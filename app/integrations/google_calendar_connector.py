"""
Google Calendar connector — minimal OAuth2 + bidirectional sync.

Sits alongside the fully-featured :class:`app.integrations.google_calendar.
GoogleCalendarConnector` (Google API client library based). This one talks
directly to the Google REST API via ``requests`` and persists *everything*
in ``Integration.config`` so it owns no extra tables.

Provider key: ``"google_calendar_connector"`` (per-user). All public
methods return JSON-serialisable dicts and degrade gracefully when the
integration row is missing or ``is_active`` is False.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests

from app.integrations.base import BaseConnector
from app.utils.secret_crypto import decrypt_if_needed, encrypt_if_possible
from app.utils.secret_crypto import is_configured as secrets_encryption_configured

logger = logging.getLogger(__name__)

PROVIDER_KEY = "google_calendar_connector"
HTTP_TIMEOUT = 10
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
GOOGLE_CALENDAR_API = "https://www.googleapis.com/calendar/v3"
GOOGLE_SCOPES = " ".join(
    [
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/calendar.events",
        "openid",
        "email",
    ]
)

MAX_DAYS_BACK = 30
DEFAULT_DAYS_BACK = 7
TT_MARKER = "[TT]"


def _enc(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = (value or "").strip()
    if not value:
        return ""
    if secrets_encryption_configured():
        try:
            return encrypt_if_possible(value)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Google secret encryption failed; storing plaintext: %s", exc)
    return value


def _dec(value: Optional[str]) -> str:
    if not value:
        return ""
    try:
        return decrypt_if_needed(value)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Google secret decryption failed: %s", exc)
        return ""


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


class GoogleCalendarConnector(BaseConnector):
    """Per-user Google Calendar import/export connector."""

    display_name = "Google Calendar"
    description = "Import calendar events as time entries and (optionally) export back"
    icon = "google"

    def __init__(self, integration=None, credentials=None):
        super().__init__(integration, credentials)

    # ------------------------------------------------------------------
    # BaseConnector abstract surface
    # ------------------------------------------------------------------
    @property
    def provider_name(self) -> str:
        return PROVIDER_KEY

    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        from flask import current_app

        client_id = current_app.config.get("GOOGLE_CLIENT_ID")
        if not client_id:
            raise ValueError("GOOGLE_CLIENT_ID is not configured")
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": GOOGLE_SCOPES,
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "consent",
        }
        if state:
            params["state"] = state
        from urllib.parse import urlencode

        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        from flask import current_app

        client_id = current_app.config.get("GOOGLE_CLIENT_ID")
        client_secret = current_app.config.get("GOOGLE_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise ValueError("GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET are not configured")
        try:
            resp = requests.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
                timeout=HTTP_TIMEOUT,
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"Token exchange failed: {exc}") from exc

        if resp.status_code != 200:
            raise RuntimeError(f"Google token endpoint returned HTTP {resp.status_code}")

        data = resp.json() or {}
        access = data.get("access_token")
        refresh = data.get("refresh_token")
        if not access:
            raise RuntimeError("Google token response missing access_token")
        expires_in = int(data.get("expires_in") or 3600)
        expires_at = (datetime.now(timezone.utc) + timedelta(seconds=expires_in - 60)).isoformat()

        email = self._fetch_userinfo_email(access)
        return {
            "access_token": access,
            "refresh_token": refresh,
            "expires_at": expires_at,
            "email": email,
        }

    def refresh_access_token(self) -> Dict[str, Any]:
        return {"access_token": self._refresh_token_if_needed() or None}

    def test_connection(self) -> Dict[str, Any]:
        if not self.integration or not self.integration.is_active:
            return {"success": False, "message": "Integration not configured"}
        try:
            token = self._refresh_token_if_needed()
        except Exception as exc:
            return {"success": False, "message": str(exc)}
        try:
            resp = requests.get(
                f"{GOOGLE_CALENDAR_API}/users/me/calendarList",
                headers={"Authorization": f"Bearer {token}"},
                timeout=HTTP_TIMEOUT,
            )
        except requests.RequestException as exc:
            return {"success": False, "message": f"Connection error: {exc}"}
        if resp.status_code != 200:
            return {"success": False, "message": f"Google returned HTTP {resp.status_code}"}
        return {"success": True, "message": f"Connected ({len(resp.json().get('items') or [])} calendars)"}

    # ------------------------------------------------------------------
    # Config / persistence
    # ------------------------------------------------------------------
    def _cfg(self) -> Dict[str, Any]:
        return dict(self.integration.config or {}) if self.integration else {}

    def get_status(self) -> Dict[str, Any]:
        """Return UI-safe status (used by /api/integrations/google/status)."""
        if not self.integration:
            return {"ok": False, "connected": False}
        cfg = self._cfg()
        return {
            "ok": True,
            "connected": bool(cfg.get("access_token")),
            "email": cfg.get("email"),
            "calendar_id": cfg.get("calendar_id", "primary"),
            "sync_direction": cfg.get("sync_direction", "import"),
            "default_project_id": cfg.get("default_project_id"),
            "sync_days_back": int(cfg.get("sync_days_back") or DEFAULT_DAYS_BACK),
            "last_sync_at": cfg.get("last_sync_at"),
            "is_active": bool(self.integration.is_active),
        }

    @classmethod
    def save_tokens(cls, integration, tokens: Dict[str, Any]) -> Dict[str, Any]:
        """Store encrypted tokens after a successful OAuth callback."""
        from app.utils.db import safe_commit

        if not integration:
            return {"ok": False, "error": "Integration not configured"}

        cfg: Dict[str, Any] = dict(integration.config or {})
        cfg["access_token"] = _enc(tokens.get("access_token"))
        if tokens.get("refresh_token"):
            cfg["refresh_token"] = _enc(tokens["refresh_token"])
        if tokens.get("expires_at"):
            cfg["token_expiry"] = tokens["expires_at"]
        if tokens.get("email"):
            cfg["email"] = tokens["email"]
        cfg.setdefault("calendar_id", "primary")
        cfg.setdefault("sync_direction", "import")
        cfg.setdefault("sync_days_back", DEFAULT_DAYS_BACK)
        integration.config = cfg
        integration.is_active = True
        integration.updated_at = datetime.utcnow()
        if not safe_commit("google_connector_save_tokens", {"integration_id": integration.id}):
            return {"ok": False, "error": "Database error while saving tokens"}
        return {"ok": True}

    @classmethod
    def save_settings(cls, integration, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Update user-facing settings (calendar id, direction, etc.)."""
        from app.utils.db import safe_commit

        if not integration:
            return {"ok": False, "error": "Integration not configured"}

        cfg: Dict[str, Any] = dict(integration.config or {})
        if "calendar_id" in payload:
            cfg["calendar_id"] = (payload.get("calendar_id") or "primary").strip() or "primary"
        if "sync_direction" in payload:
            direction = (payload.get("sync_direction") or "import").strip()
            if direction not in ("import", "export", "both"):
                direction = "import"
            cfg["sync_direction"] = direction
        if "default_project_id" in payload:
            try:
                cfg["default_project_id"] = int(payload["default_project_id"])
            except (TypeError, ValueError):
                cfg["default_project_id"] = None
        if "sync_days_back" in payload:
            try:
                cfg["sync_days_back"] = max(1, min(MAX_DAYS_BACK, int(payload["sync_days_back"])))
            except (TypeError, ValueError):
                cfg["sync_days_back"] = DEFAULT_DAYS_BACK

        integration.config = cfg
        integration.updated_at = datetime.utcnow()
        if not safe_commit("google_connector_save_settings", {"integration_id": integration.id}):
            return {"ok": False, "error": "Database error while saving settings"}
        return {"ok": True}

    @classmethod
    def clear_tokens(cls, integration) -> Dict[str, Any]:
        from app.utils.db import safe_commit

        if not integration:
            return {"ok": False, "error": "Integration not configured"}
        cfg = dict(integration.config or {})
        for key in ("access_token", "refresh_token", "token_expiry", "email"):
            cfg.pop(key, None)
        integration.config = cfg
        integration.is_active = False
        integration.updated_at = datetime.utcnow()
        safe_commit("google_connector_clear_tokens", {"integration_id": integration.id})
        return {"ok": True}

    # ------------------------------------------------------------------
    # Token refresh
    # ------------------------------------------------------------------
    def _refresh_token_if_needed(self) -> str:
        from flask import current_app

        if not self.integration:
            raise RuntimeError("Integration not configured")
        cfg = self._cfg()
        access = _dec(cfg.get("access_token"))
        refresh = _dec(cfg.get("refresh_token"))
        if not access and not refresh:
            raise RuntimeError("No Google credentials stored")

        expiry = _parse_iso(cfg.get("token_expiry"))
        now = datetime.now(timezone.utc)
        if expiry and expiry > now + timedelta(minutes=5):
            return access

        if not refresh:
            return access  # access still works until Google says otherwise

        client_id = current_app.config.get("GOOGLE_CLIENT_ID")
        client_secret = current_app.config.get("GOOGLE_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise RuntimeError("GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET are not configured")

        try:
            resp = requests.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh,
                },
                timeout=HTTP_TIMEOUT,
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"Token refresh failed: {exc}") from exc

        if resp.status_code != 200:
            raise RuntimeError(f"Token refresh returned HTTP {resp.status_code}")
        data = resp.json() or {}
        new_access = data.get("access_token")
        if not new_access:
            raise RuntimeError("Google refresh response missing access_token")
        expires_in = int(data.get("expires_in") or 3600)
        cfg["access_token"] = _enc(new_access)
        cfg["token_expiry"] = (datetime.now(timezone.utc) + timedelta(seconds=expires_in - 60)).isoformat()
        self.integration.config = cfg
        try:
            from app.utils.db import safe_commit

            safe_commit("google_connector_refresh_token", {"integration_id": self.integration.id})
        except Exception:
            pass
        return new_access

    @staticmethod
    def _fetch_userinfo_email(access_token: str) -> Optional[str]:
        try:
            resp = requests.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=HTTP_TIMEOUT,
            )
        except requests.RequestException:
            return None
        if resp.status_code != 200:
            return None
        return (resp.json() or {}).get("email")

    # ------------------------------------------------------------------
    # Sync (import + export)
    # ------------------------------------------------------------------
    def sync(self) -> Dict[str, Any]:
        if not self.integration or not self.integration.is_active:
            return {"ok": False, "error": "Integration not configured"}
        cfg = self._cfg()
        direction = cfg.get("sync_direction", "import")
        result = {"ok": True, "imported": 0, "skipped": 0, "exported": 0, "errors": []}
        try:
            token = self._refresh_token_if_needed()
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

        try:
            if direction in ("import", "both"):
                imp = self._sync_import(token, cfg)
                result["imported"] += imp.get("imported", 0)
                result["skipped"] += imp.get("skipped", 0)
                result["errors"].extend(imp.get("errors", []))
            if direction in ("export", "both"):
                exp = self._sync_export(token, cfg)
                result["exported"] += exp.get("exported", 0)
                result["errors"].extend(exp.get("errors", []))
        except Exception as exc:
            logger.warning("Google sync failed: %s", exc)
            result["ok"] = False
            result["error"] = str(exc)

        try:
            cfg["last_sync_at"] = datetime.now(timezone.utc).isoformat()
            self.integration.config = cfg
            self.integration.last_sync_at = datetime.utcnow()
            self.integration.last_sync_status = "success" if result.get("ok") and not result.get("errors") else "partial"
            from app.utils.db import safe_commit

            safe_commit("google_connector_sync_status", {"integration_id": self.integration.id})
        except Exception:
            pass
        return result

    def _sync_import(self, token: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
        from app import db
        from app.models import TimeEntry
        from app.utils.db import safe_commit

        days_back = int(cfg.get("sync_days_back") or DEFAULT_DAYS_BACK)
        days_back = max(1, min(MAX_DAYS_BACK, days_back))
        calendar_id = cfg.get("calendar_id") or "primary"
        project_id = cfg.get("default_project_id")
        if not project_id:
            return {"imported": 0, "skipped": 0, "errors": ["default_project_id not configured"]}

        now = datetime.now(timezone.utc)
        time_min = (now - timedelta(days=days_back)).isoformat()
        time_max = now.isoformat()

        try:
            resp = requests.get(
                f"{GOOGLE_CALENDAR_API}/calendars/{calendar_id}/events",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "timeMin": time_min,
                    "timeMax": time_max,
                    "singleEvents": "true",
                    "orderBy": "startTime",
                    "maxResults": 100,
                },
                timeout=HTTP_TIMEOUT,
            )
        except requests.RequestException as exc:
            return {"imported": 0, "skipped": 0, "errors": [f"Calendar fetch failed: {exc}"]}

        if resp.status_code != 200:
            return {"imported": 0, "skipped": 0, "errors": [f"Google returned HTTP {resp.status_code}"]}

        items = (resp.json() or {}).get("items") or []
        imported = 0
        skipped = 0
        errors: List[str] = []
        user_id = self.integration.user_id

        for event in items:
            summary = (event.get("summary") or "").strip()
            if TT_MARKER in summary:
                skipped += 1
                continue
            start = (event.get("start") or {}).get("dateTime")
            end = (event.get("end") or {}).get("dateTime")
            if not start or not end:
                skipped += 1
                continue
            event_id = event.get("id")
            if not event_id:
                skipped += 1
                continue
            marker = f"gcal:{event_id}"

            existing = TimeEntry.query.filter(
                TimeEntry.user_id == user_id,
                TimeEntry.notes.ilike(f"%{marker}%"),
            ).first()
            if existing:
                skipped += 1
                continue

            start_dt = _parse_iso(start)
            end_dt = _parse_iso(end)
            if not start_dt or not end_dt or end_dt <= start_dt:
                skipped += 1
                continue

            try:
                from app.utils.timezone import utc_to_local

                start_local = utc_to_local(start_dt.astimezone(timezone.utc)).replace(tzinfo=None)
                end_local = utc_to_local(end_dt.astimezone(timezone.utc)).replace(tzinfo=None)
            except Exception:
                start_local = start_dt.replace(tzinfo=None)
                end_local = end_dt.replace(tzinfo=None)

            try:
                entry = TimeEntry(
                    user_id=user_id,
                    project_id=int(project_id),
                    start_time=start_local,
                    end_time=end_local,
                    notes=f"{summary or 'Calendar event'} [{marker}]",
                    source="auto",
                    billable=False,
                )
                entry.calculate_duration()
                db.session.add(entry)
                imported += 1
            except Exception as exc:
                errors.append(f"{event_id}: {exc}")

        if imported:
            if not safe_commit("google_connector_import", {"integration_id": self.integration.id}):
                errors.append("Database error while saving imported entries")
        return {"imported": imported, "skipped": skipped, "errors": errors}

    def _sync_export(self, token: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
        from app.models import Project, Task, TimeEntry

        calendar_id = cfg.get("calendar_id") or "primary"
        last_sync = _parse_iso(cfg.get("last_sync_at"))
        if not last_sync:
            last_sync = datetime.now(timezone.utc) - timedelta(days=int(cfg.get("sync_days_back") or DEFAULT_DAYS_BACK))

        last_sync_naive = last_sync.replace(tzinfo=None) if last_sync.tzinfo else last_sync

        entries = (
            TimeEntry.query.filter(
                TimeEntry.user_id == self.integration.user_id,
                TimeEntry.end_time.isnot(None),
                TimeEntry.created_at >= last_sync_naive,
            )
            .order_by(TimeEntry.created_at.asc())
            .limit(200)
            .all()
        )

        exported = 0
        errors: List[str] = []
        for entry in entries:
            if entry.notes and "[gcal:" in entry.notes:
                continue
            project = Project.query.get(entry.project_id) if entry.project_id else None
            task = Task.query.get(entry.task_id) if entry.task_id else None
            project_name = project.name if project else "TimeTracker"
            task_name = task.name if task else ((entry.notes or "")[:50])
            summary = f"{TT_MARKER} {project_name} — {task_name}".strip()
            try:
                from app.utils.timezone import local_to_utc

                start_iso = local_to_utc(entry.start_time).isoformat()
                end_iso = local_to_utc(entry.end_time).isoformat()
            except Exception:
                start_iso = entry.start_time.isoformat()
                end_iso = entry.end_time.isoformat()

            body = {
                "summary": summary[:200],
                "description": f"Logged via TimeTracker. Duration: {entry.duration_formatted}",
                "start": {"dateTime": start_iso, "timeZone": "UTC"},
                "end": {"dateTime": end_iso, "timeZone": "UTC"},
            }
            try:
                resp = requests.post(
                    f"{GOOGLE_CALENDAR_API}/calendars/{calendar_id}/events",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json=body,
                    timeout=HTTP_TIMEOUT,
                )
            except requests.RequestException as exc:
                errors.append(f"entry {entry.id}: {exc}")
                continue
            if resp.status_code in (200, 201):
                exported += 1
            else:
                errors.append(f"entry {entry.id}: HTTP {resp.status_code}")
        return {"exported": exported, "errors": errors}

    # ------------------------------------------------------------------
    # Revoke / disconnect
    # ------------------------------------------------------------------
    def revoke(self) -> Dict[str, Any]:
        if not self.integration:
            return {"ok": False, "error": "Integration not configured"}
        cfg = self._cfg()
        token = _dec(cfg.get("refresh_token")) or _dec(cfg.get("access_token"))
        if token:
            try:
                requests.post(
                    GOOGLE_REVOKE_URL,
                    params={"token": token},
                    timeout=HTTP_TIMEOUT,
                )
            except requests.RequestException as exc:
                logger.debug("Google revoke best-effort failed: %s", exc)
        return self.clear_tokens(self.integration)

    def handle_webhook(
        self,
        payload: Dict[str, Any],
        headers: Dict[str, str],
        raw_body: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        # Google Calendar push notifications are not used by this connector,
        # but we still implement the abstract method.
        return {"status": 200, "body": {"ok": False, "error": "Webhooks not supported"}}

    # ------------------------------------------------------------------
    # Convenience class methods
    # ------------------------------------------------------------------
    @classmethod
    def for_user(cls, user) -> Optional["GoogleCalendarConnector"]:
        from app.models import Integration

        if not user:
            return None
        integration = Integration.query.filter_by(provider=PROVIDER_KEY, user_id=user.id).first()
        if not integration:
            return None
        return cls(integration=integration, credentials=None)

    @classmethod
    def for_any_active(cls) -> List["GoogleCalendarConnector"]:
        from app.models import Integration

        rows = Integration.query.filter_by(provider=PROVIDER_KEY, is_active=True).all()
        return [cls(integration=row, credentials=None) for row in rows]

    @classmethod
    def get_or_create_for_user(cls, user) -> Optional["Integration"]:  # type: ignore[override]
        """Return the (possibly fresh) Integration row for ``user`` — used by OAuth callback."""
        from app import db
        from app.models import Integration
        from app.utils.db import safe_commit

        if not user:
            return None
        integration = Integration.query.filter_by(provider=PROVIDER_KEY, user_id=user.id).first()
        if integration:
            return integration
        integration = Integration(
            name="Google Calendar",
            provider=PROVIDER_KEY,
            user_id=user.id,
            is_global=False,
            is_active=False,
            config={},
        )
        db.session.add(integration)
        safe_commit("google_connector_create", {"user_id": user.id})
        return integration
