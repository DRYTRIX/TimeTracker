"""
ActivityWatch integration connector.

Imports window and web activity events from a local ActivityWatch aw-server
(https://activitywatch.net/) as automatic time entries (source='auto').

This connector is **not OAuth-based**. No credentials. Configuration only:
- Integration.config: server_url, default_project_id, lookback_days, bucket_ids, etc.

aw-server REST API: GET /api/0/buckets/, GET /api/0/buckets/<id>/events?start=&end=&limit=
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests

from app.integrations.base import BaseConnector
from app.utils.timezone import get_timezone_obj, utc_to_local

logger = logging.getLogger(__name__)


def _to_local_naive(dt: datetime) -> datetime:
    """Convert a datetime to app-local timezone and drop tzinfo (DB stores local naive)."""
    tz = get_timezone_obj()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz).replace(tzinfo=None)


def _normalize_server_url(url: str) -> str:
    """Strip trailing slash from server URL."""
    if not url:
        return url
    return url.rstrip("/")


class ActivityWatchConnector(BaseConnector):
    """ActivityWatch integration: import aw-server events as time entries."""

    display_name = "ActivityWatch"
    description = "Import window and web activity from ActivityWatch (aw-server) as automatic time entries"
    icon = "desktop"

    @property
    def provider_name(self) -> str:
        return "activitywatch"

    # --- OAuth (not used) ---
    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        raise NotImplementedError("ActivityWatch does not use OAuth.")

    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        raise NotImplementedError("ActivityWatch does not use OAuth.")

    def refresh_access_token(self) -> Dict[str, Any]:
        raise NotImplementedError("ActivityWatch does not use OAuth.")

    # --- Helpers ---
    def _get_server_url(self) -> str:
        cfg = self.integration.config or {}
        url = (cfg.get("server_url") or "").strip()
        if not url:
            raise ValueError("ActivityWatch server_url is required in integration config.")
        return _normalize_server_url(url)

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        base = self._get_server_url()
        url = f"{base}/api/0/{path.lstrip('/')}"
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.ConnectionError as e:
            raise ValueError(f"Cannot reach ActivityWatch at {base}: {e}") from e
        except requests.exceptions.Timeout as e:
            raise ValueError(f"ActivityWatch request timed out: {e}") from e
        except requests.exceptions.HTTPError as e:
            raise ValueError(f"ActivityWatch API error: {e}") from e
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from ActivityWatch: {e}") from e

    def test_connection(self) -> Dict[str, Any]:
        """Test connectivity to aw-server: GET /api/0/buckets/."""
        try:
            self._get("buckets/")
            return {"success": True, "message": "Connected to ActivityWatch."}
        except ValueError as e:
            return {"success": False, "message": str(e)}
        except Exception as e:
            return {"success": False, "message": f"Connection test failed: {e}"}

    def sync_data(self, sync_type: str = "full") -> Dict[str, Any]:
        """
        Fetch events from selected buckets and create TimeEntry records (source='auto').
        Uses IntegrationExternalEventLink for idempotency.
        """
        from app import db
        from app.models import TimeEntry
        from app.models.integration_external_event_link import IntegrationExternalEventLink

        if not self.integration or not self.integration.user_id:
            return {"success": False, "message": "ActivityWatch integration must be per-user."}

        cfg = self.integration.config or {}
        server_url = _normalize_server_url((cfg.get("server_url") or "").strip())
        if not server_url:
            return {"success": False, "message": "server_url is required."}

        lookback_days = int(cfg.get("lookback_days", 7))
        lookback_days = max(1, min(90, lookback_days))
        default_project_id = cfg.get("default_project_id")
        if default_project_id is not None:
            default_project_id = int(default_project_id)

        # Parse bucket_ids: optional list; if empty, use aw-watcher-window_* and aw-watcher-web_*
        bucket_ids_cfg = cfg.get("bucket_ids")
        bucket_ids: Optional[List[str]] = None
        if bucket_ids_cfg is not None and bucket_ids_cfg != "":
            if isinstance(bucket_ids_cfg, list):
                bucket_ids = [str(b).strip() for b in bucket_ids_cfg if b]
            elif isinstance(bucket_ids_cfg, str):
                raw = bucket_ids_cfg.strip()
                if raw:
                    try:
                        parsed = json.loads(raw)
                        bucket_ids = [str(b).strip() for b in (parsed if isinstance(parsed, list) else [parsed]) if b]
                    except json.JSONDecodeError:
                        bucket_ids = [b.strip() for b in raw.split(",") if b.strip()]

        now_utc = datetime.now(timezone.utc)
        if sync_type == "incremental" and self.integration.last_sync_at:
            time_min_utc = self.integration.last_sync_at
            if time_min_utc.tzinfo is None:
                time_min_utc = time_min_utc.replace(tzinfo=timezone.utc)
        else:
            time_min_utc = now_utc - timedelta(days=lookback_days)
        time_max_utc = now_utc

        time_min_iso = time_min_utc.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        time_max_iso = time_max_utc.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        # Resolve bucket list
        try:
            buckets_data = self._get("buckets/")
        except Exception as e:
            if self.integration:
                self.integration.last_sync_status = "error"
                self.integration.last_error = str(e)
                try:
                    db.session.commit()
                except Exception:
                    pass
            return {"success": False, "message": f"Failed to list buckets: {e}"}

        if isinstance(buckets_data, dict):
            # /buckets/ returns { "id": { metadata } }
            all_bucket_ids = list(buckets_data.keys())
        elif isinstance(buckets_data, list):
            all_bucket_ids = [b.get("id") if isinstance(b, dict) else str(b) for b in buckets_data if b]
        else:
            all_bucket_ids = []

        if bucket_ids is not None and len(bucket_ids) > 0:
            selected = [b for b in bucket_ids if b in all_bucket_ids]
            if not selected:
                return {
                    "success": False,
                    "message": f"None of the configured bucket_ids exist. Available: {all_bucket_ids[:5]}{'...' if len(all_bucket_ids) > 5 else ''}.",
                }
        else:
            selected = [
                b
                for b in all_bucket_ids
                if b.startswith("aw-watcher-window_") or b.startswith("aw-watcher-web_")
            ]

        if not selected:
            self.integration.last_sync_at = datetime.utcnow()
            self.integration.last_sync_status = "success"
            self.integration.last_error = None
            db.session.commit()
            return {
                "success": True,
                "imported": 0,
                "skipped": 0,
                "synced_items": 0,
                "errors": [],
                "message": "No aw-watcher-window or aw-watcher-web buckets found. Install and run ActivityWatch watchers.",
            }

        imported = 0
        skipped = 0
        errors: List[str] = []

        for bucket_id in selected:
            try:
                events_data = self._get(
                    f"buckets/{bucket_id}/events",
                    params={"start": time_min_iso, "end": time_max_iso, "limit": 5000},
                )
            except Exception as e:
                errors.append(f"Bucket {bucket_id}: {e}")
                continue

            events = events_data if isinstance(events_data, list) else []
            for ev in events:
                try:
                    ts = ev.get("timestamp")
                    duration = ev.get("duration")
                    data = ev.get("data") or {}

                    if not ts:
                        skipped += 1
                        continue

                    # Parse timestamp (ISO UTC)
                    if isinstance(ts, str):
                        if ts.endswith("Z"):
                            ts = ts[:-1] + "+00:00"
                        start_dt = datetime.fromisoformat(ts)
                    else:
                        skipped += 1
                        continue

                    if start_dt.tzinfo is None:
                        start_dt = start_dt.replace(tzinfo=timezone.utc)
                    else:
                        start_dt = start_dt.astimezone(timezone.utc)

                    dur_sec = 1
                    if duration is not None:
                        try:
                            dur_sec = int(float(duration))
                            if dur_sec <= 0:
                                dur_sec = 1
                        except (TypeError, ValueError):
                            pass

                    end_dt = start_dt + timedelta(seconds=dur_sec)

                    # Notes: app+title or url+title
                    app = (data.get("app") or "").strip()
                    title = (data.get("title") or "").strip()
                    url = (data.get("url") or "").strip()
                    if app and title:
                        notes = f"ActivityWatch: {app} - {title}"
                    elif url and title:
                        notes = f"{url} - {title}"
                    elif url:
                        notes = url
                    elif app:
                        notes = f"ActivityWatch: {app}"
                    else:
                        notes = "ActivityWatch: (no app/title)"

                    # external_uid for idempotency (max 255)
                    data_str = (app or "") + "|" + (title or "") + (url or "")
                    h = hashlib.md5(data_str.encode("utf-8")).hexdigest()[:16]
                    external_uid = f"{bucket_id}|{ts}|{dur_sec}|{h}"[:255]

                    existing = IntegrationExternalEventLink.query.filter_by(
                        integration_id=self.integration.id,
                        external_uid=external_uid,
                    ).first()
                    if existing:
                        skipped += 1
                        continue

                    start_local = _to_local_naive(start_dt)
                    end_local = _to_local_naive(end_dt)
                    if end_local <= start_local:
                        skipped += 1
                        continue

                    entry = TimeEntry(
                        user_id=self.integration.user_id,
                        project_id=default_project_id,
                        client_id=None,
                        task_id=None,
                        start_time=start_local,
                        end_time=end_local,
                        duration_seconds=dur_sec,
                        notes=notes[:5000] if notes else None,
                        tags=None,
                        source="auto",
                        billable=True,
                        paid=False,
                    )
                    db.session.add(entry)
                    db.session.flush()

                    link = IntegrationExternalEventLink(
                        integration_id=self.integration.id,
                        time_entry_id=entry.id,
                        external_uid=external_uid,
                        external_href=None,
                    )
                    db.session.add(link)
                    imported += 1

                except Exception as e:
                    errors.append(f"Event {ev.get('timestamp', '?')}: {e}")

        self.integration.last_sync_at = datetime.utcnow()
        self.integration.last_sync_status = "success" if not errors else "partial"
        self.integration.last_error = "; ".join(errors[:3]) if errors else None
        db.session.commit()

        msg = f"Imported {imported} events, skipped {skipped}."
        if errors:
            msg += f" Errors: {len(errors)}."
        return {
            "success": True,
            "imported": imported,
            "skipped": skipped,
            "synced_items": imported,
            "errors": errors,
            "message": msg,
        }

    def get_config_schema(self) -> Dict[str, Any]:
        return {
            "fields": [
                {
                    "name": "server_url",
                    "type": "url",
                    "label": "ActivityWatch Server URL",
                    "required": True,
                    "placeholder": "http://localhost:5600",
                    "description": "Base URL of aw-server (no trailing slash). Must be reachable from this server.",
                    "help": "aw-server must be running. Use http://localhost:5600 if on the same machine.",
                },
                {
                    "name": "default_project_id",
                    "type": "number",
                    "label": "Default Project",
                    "required": False,
                    "description": "Project to assign imported events to (optional)",
                    "help": "Leave empty to import without a project.",
                },
                {
                    "name": "lookback_days",
                    "type": "number",
                    "label": "Lookback Days",
                    "default": 7,
                    "validation": {"min": 1, "max": 90},
                    "description": "Days in the past to import (1–90)",
                    "help": "How far back to fetch on full sync.",
                },
                {
                    "name": "bucket_ids",
                    "type": "text",
                    "label": "Bucket IDs",
                    "required": False,
                    "description": "Comma-separated or JSON array; leave empty for all window and web buckets",
                    "help": "e.g. aw-watcher-window_hostname. Empty = use all aw-watcher-window_* and aw-watcher-web_*.",
                },
                {
                    "name": "auto_sync",
                    "type": "boolean",
                    "label": "Auto Sync",
                    "default": False,
                    "description": "Automatically sync on a schedule",
                },
                {
                    "name": "sync_interval",
                    "type": "select",
                    "label": "Sync Schedule",
                    "options": [
                        {"value": "manual", "label": "Manual only"},
                        {"value": "hourly", "label": "Every hour"},
                        {"value": "daily", "label": "Daily"},
                    ],
                    "default": "manual",
                    "description": "How often to sync",
                },
            ],
            "required": ["server_url"],
            "sections": [
                {
                    "title": "Connection",
                    "description": "Connect to your ActivityWatch aw-server",
                    "fields": ["server_url"],
                },
                {
                    "title": "Import Settings",
                    "description": "What to import and where",
                    "fields": ["default_project_id", "lookback_days", "bucket_ids", "auto_sync", "sync_interval"],
                },
            ],
            "sync_settings": {
                "enabled": True,
                "auto_sync": False,
                "sync_interval": "manual",
                "sync_direction": "provider_to_timetracker",
                "sync_items": ["time_entries"],
            },
        }
