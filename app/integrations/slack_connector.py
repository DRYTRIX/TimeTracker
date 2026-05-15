"""
Slack connector — timer notifications, slash commands, daily summaries.

Per-user, opt-in. Sits alongside the OAuth-based
:class:`app.integrations.slack.SlackConnector` and uses the provider key
``"slack_connector"``. Tokens, signing secret, channel and feature flags
live in ``Integration.config`` (encrypted at rest where possible).

All public methods degrade gracefully when the integration row is missing
or ``is_active`` is False, and notify helpers never raise — they log a
warning and return.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from app.integrations.base import BaseConnector
from app.utils.secret_crypto import decrypt_if_needed, encrypt_if_possible
from app.utils.secret_crypto import is_configured as secrets_encryption_configured

logger = logging.getLogger(__name__)

PROVIDER_KEY = "slack_connector"
HTTP_TIMEOUT = 10
SLACK_POST_MESSAGE = "https://slack.com/api/chat.postMessage"
SLACK_SIGNATURE_VERSION = "v0"
SLACK_REQUEST_MAX_AGE = 60 * 5  # 5 minutes


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
            logger.warning("Slack secret encryption failed; storing plaintext: %s", exc)
    return value


def _dec(value: Optional[str]) -> str:
    if not value:
        return ""
    try:
        return decrypt_if_needed(value)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Slack secret decryption failed: %s", exc)
        return ""


def _mask(token: Optional[str]) -> str:
    if not token:
        return "(empty)"
    return f"{token[:4]}..."


class SlackConnector(BaseConnector):
    """Per-user Slack notifier + slash command handler."""

    display_name = "Slack"
    description = "Notify a Slack channel on timer events and run /tt slash commands"
    icon = "slack"

    def __init__(self, integration=None, credentials=None):
        super().__init__(integration, credentials)

    # ------------------------------------------------------------------
    # BaseConnector abstract surface
    # ------------------------------------------------------------------
    @property
    def provider_name(self) -> str:
        return PROVIDER_KEY

    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        raise NotImplementedError("SlackConnector uses a bot token (no OAuth flow here)")

    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        raise NotImplementedError("SlackConnector uses a bot token (no OAuth flow here)")

    def refresh_access_token(self) -> Dict[str, Any]:
        return {"access_token": self._bot_token() or None}

    def test_connection(self) -> Dict[str, Any]:
        if not self._is_ready():
            return {"success": False, "message": "Integration not configured"}
        try:
            resp = requests.post(
                "https://slack.com/api/auth.test",
                headers={"Authorization": f"Bearer {self._bot_token()}"},
                timeout=HTTP_TIMEOUT,
            )
        except requests.RequestException as exc:
            return {"success": False, "message": f"Connection error: {exc}"}
        data = resp.json() or {}
        if data.get("ok"):
            return {"success": True, "message": f"Connected as {data.get('user') or 'Unknown'}"}
        return {"success": False, "message": data.get("error") or "auth.test failed"}

    # ------------------------------------------------------------------
    # Config helpers
    # ------------------------------------------------------------------
    def _cfg(self) -> Dict[str, Any]:
        return dict(self.integration.config or {}) if self.integration else {}

    def _bot_token(self) -> str:
        return _dec(self._cfg().get("bot_token"))

    def _signing_secret(self) -> str:
        return _dec(self._cfg().get("signing_secret"))

    def _is_ready(self) -> bool:
        return bool(self.integration and self.integration.is_active and self._bot_token())

    @classmethod
    def save_config(cls, integration, payload: Dict[str, Any]) -> Dict[str, Any]:
        from app.utils.db import safe_commit

        if not integration:
            return {"ok": False, "error": "Integration not configured"}
        cfg: Dict[str, Any] = dict(integration.config or {})

        bot_token = (payload.get("bot_token") or "").strip()
        if bot_token:
            cfg["bot_token"] = _enc(bot_token)
        signing = (payload.get("signing_secret") or "").strip()
        if signing:
            cfg["signing_secret"] = _enc(signing)

        for key in ("channel_id", "daily_summary_time", "linked_slack_user_id"):
            if key in payload:
                cfg[key] = (payload.get(key) or "").strip() or None

        for flag in ("notify_on_start", "notify_on_stop", "daily_summary"):
            if flag in payload:
                cfg[flag] = bool(payload[flag])

        # Validate daily_summary_time HH:MM
        if cfg.get("daily_summary_time"):
            try:
                hh, mm = cfg["daily_summary_time"].split(":")
                if not (0 <= int(hh) <= 23 and 0 <= int(mm) <= 59):
                    raise ValueError
            except (ValueError, AttributeError):
                cfg["daily_summary_time"] = "18:00"
        else:
            cfg.setdefault("daily_summary_time", "18:00")

        integration.config = cfg
        integration.is_active = bool(cfg.get("bot_token"))
        integration.updated_at = datetime.utcnow()

        if not safe_commit("slack_connector_save_config", {"integration_id": integration.id}):
            return {"ok": False, "error": "Database error while saving configuration"}
        return {"ok": True, "is_active": bool(integration.is_active)}

    # ------------------------------------------------------------------
    # Slack signature verification (used by the webhook route)
    # ------------------------------------------------------------------
    def verify_signature(
        self,
        signature: Optional[str],
        timestamp: Optional[str],
        raw_body: Optional[bytes],
    ) -> bool:
        secret = self._signing_secret()
        if not secret or not signature or not timestamp or raw_body is None:
            return False
        try:
            ts_int = int(timestamp)
        except (TypeError, ValueError):
            return False
        if abs(time.time() - ts_int) > SLACK_REQUEST_MAX_AGE:
            return False
        base = f"{SLACK_SIGNATURE_VERSION}:{timestamp}:".encode("utf-8") + raw_body
        expected = (
            SLACK_SIGNATURE_VERSION
            + "="
            + hmac.new(secret.encode("utf-8"), base, hashlib.sha256).hexdigest()
        )
        return hmac.compare_digest(expected, signature)

    # ------------------------------------------------------------------
    # Webhook / Events / Slash commands
    # ------------------------------------------------------------------
    def handle_webhook(
        self,
        payload: Dict[str, Any],
        headers: Dict[str, str],
        raw_body: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        # URL verification challenge
        if isinstance(payload, dict) and payload.get("type") == "url_verification" and payload.get("challenge"):
            return {"status": 200, "body": {"challenge": payload["challenge"]}}
        return {"status": 200, "body": {"ok": True}}

    def handle_slash_command(self, form: Dict[str, str]) -> Dict[str, Any]:
        """Dispatch ``/tt ...`` slash commands.

        Returns ``{"status": int, "body": dict-or-text}`` for the route to
        serialise. All replies are ``response_type=ephemeral`` JSON.
        """
        if not self.integration:
            return self._ephemeral("Integration not configured.")

        slack_user_id = (form.get("user_id") or "").strip()
        linked = (self._cfg().get("linked_slack_user_id") or "").strip()
        if linked and slack_user_id and slack_user_id != linked:
            return self._ephemeral("This Slack user is not linked to your TimeTracker account.")

        owner = self._owner()
        if not owner:
            return self._ephemeral("No TimeTracker user is linked to this integration.")

        raw_text = (form.get("text") or "").strip()
        parts = raw_text.split(None, 1)
        subcommand = (parts[0] or "").lower() if parts else ""
        argument = parts[1] if len(parts) > 1 else ""

        if subcommand == "start":
            return self._cmd_start(owner, argument)
        if subcommand == "stop":
            return self._cmd_stop(owner)
        if subcommand == "status":
            return self._cmd_status(owner)
        if subcommand == "today":
            return self._cmd_today(owner)
        return self._ephemeral(
            "Available commands:\n"
            "• `/tt start <project>` — start a timer\n"
            "• `/tt stop` — stop the active timer\n"
            "• `/tt status` — show the current timer\n"
            "• `/tt today` — today's hours summary"
        )

    def _cmd_start(self, owner, argument: str) -> Dict[str, Any]:
        from app.models import Project
        from app.services.time_tracking_service import TimeTrackingService

        argument = (argument or "").strip()
        if not argument:
            return self._ephemeral("Usage: `/tt start <project name or ID>`")

        project = None
        try:
            project = Project.query.get(int(argument))
        except (TypeError, ValueError):
            project = None
        if not project:
            project = Project.query.filter(Project.name.ilike(f"%{argument}%")).first()
        if not project:
            return self._ephemeral(f"Project not found: `{argument}`")

        result = TimeTrackingService().start_timer(user_id=owner.id, project_id=project.id)
        if result.get("success"):
            return self._ephemeral(f":stopwatch: Timer started for *{project.name}*.")
        return self._ephemeral(f"Could not start timer: {result.get('message') or 'unknown error'}")

    def _cmd_stop(self, owner) -> Dict[str, Any]:
        from app.services.time_tracking_service import TimeTrackingService

        result = TimeTrackingService().stop_timer(user_id=owner.id)
        if result.get("success"):
            entry = result.get("entry")
            duration = getattr(entry, "duration_formatted", "")
            return self._ephemeral(f":white_check_mark: Timer stopped (duration {duration}).")
        return self._ephemeral(f"Could not stop timer: {result.get('message') or 'no active timer'}")

    def _cmd_status(self, owner) -> Dict[str, Any]:
        active = getattr(owner, "active_timer", None)
        if not active:
            return self._ephemeral("No active timer.")
        project_name = active.project.name if getattr(active, "project", None) else "—"
        return self._ephemeral(
            f":hourglass_flowing_sand: Active timer on *{project_name}* "
            f"(running {active.duration_formatted})."
        )

    def _cmd_today(self, owner) -> Dict[str, Any]:
        try:
            from app.services.notification_service import get_today_summary_for_user

            summary = get_today_summary_for_user(owner)
        except Exception as exc:
            return self._ephemeral(f"Could not fetch today's summary: {exc}")
        hours = summary.get("hours", 0)
        projects = summary.get("projects", 0)
        return self._ephemeral(
            f":bar_chart: Today: *{hours}h* across *{projects}* project(s)."
        )

    @staticmethod
    def _ephemeral(text: str) -> Dict[str, Any]:
        return {"status": 200, "body": {"response_type": "ephemeral", "text": text}}

    # ------------------------------------------------------------------
    # Notify helpers (timer start / stop / daily summary)
    # ------------------------------------------------------------------
    def notify_timer_started(self, user, timer) -> None:
        cfg = self._cfg()
        if not (self._is_ready() and cfg.get("notify_on_start")):
            return
        try:
            project_name = timer.project.name if getattr(timer, "project", None) else "—"
            task_name = timer.task.name if getattr(timer, "task", None) else None
            start_dt = getattr(timer, "start_time", None)
            start_hhmm = start_dt.strftime("%H:%M") if hasattr(start_dt, "strftime") else "—"
            text = (
                f":stopwatch: *{getattr(user, 'display_name', None) or user.username}* started a timer\n"
                f"*Project:* {project_name}"
                f"{(' — ' + task_name) if task_name else ''}\n"
                f"*Started at:* {start_hhmm}"
            )
            self._post(cfg.get("channel_id"), text)
        except Exception as exc:
            logger.warning("Slack notify_timer_started failed: %s", exc)

    def notify_timer_stopped(self, user, entry) -> None:
        cfg = self._cfg()
        if not (self._is_ready() and cfg.get("notify_on_stop")):
            return
        try:
            project_name = entry.project.name if getattr(entry, "project", None) else "—"
            duration = getattr(entry, "duration_formatted", "—")
            billable = "Yes" if getattr(entry, "billable", False) else "No"
            text = (
                f":white_check_mark: *{getattr(user, 'display_name', None) or user.username}* stopped a timer\n"
                f"*Project:* {project_name}\n"
                f"*Duration:* {duration}\n"
                f"*Billable:* {billable}"
            )
            self._post(cfg.get("channel_id"), text)
        except Exception as exc:
            logger.warning("Slack notify_timer_stopped failed: %s", exc)

    def post_daily_summary(self, user) -> None:
        cfg = self._cfg()
        if not (self._is_ready() and cfg.get("daily_summary")):
            return
        try:
            from app.services.notification_service import get_today_summary_for_user

            summary = get_today_summary_for_user(user)
            hours = summary.get("hours", 0)
            projects = summary.get("projects", 0)
            text = (
                f":bar_chart: *Daily summary for "
                f"{getattr(user, 'display_name', None) or user.username}*\n"
                f"*Hours logged:* {hours}h across {projects} projects\n"
                f"Have a great evening!"
            )
            self._post(cfg.get("channel_id"), text)
        except Exception as exc:
            logger.warning("Slack post_daily_summary failed: %s", exc)

    def send_test_message(self) -> Dict[str, Any]:
        if not self._is_ready():
            return {"ok": False, "error": "Integration not configured"}
        ok = self._post(self._cfg().get("channel_id"), ":wave: TimeTracker test message.")
        return {"ok": bool(ok)}

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------
    def _post(self, channel: Optional[str], text: str) -> bool:
        token = self._bot_token()
        if not (token and channel and text):
            return False
        try:
            resp = requests.post(
                SLACK_POST_MESSAGE,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                json={"channel": channel, "text": text},
                timeout=HTTP_TIMEOUT,
            )
        except requests.RequestException as exc:
            logger.warning("Slack chat.postMessage failed (token=%s): %s", _mask(token), exc)
            return False
        if resp.status_code != 200:
            logger.warning("Slack chat.postMessage HTTP %s", resp.status_code)
            return False
        data = resp.json() or {}
        if not data.get("ok"):
            logger.warning("Slack chat.postMessage error: %s", data.get("error"))
            return False
        return True

    def _owner(self):
        from app.models import User

        if not self.integration or not self.integration.user_id:
            return None
        return User.query.get(self.integration.user_id)

    # ------------------------------------------------------------------
    # Class-level convenience used by routes and timer wiring
    # ------------------------------------------------------------------
    @classmethod
    def notify_for_user(cls, user, timer, event: str) -> None:
        """Fire-and-forget notify helper used by timer routes.

        Always returns None; exceptions are logged at debug level.
        """
        try:
            connector = cls.for_user(user)
            if not connector:
                return
            if event == "start":
                connector.notify_timer_started(user, timer)
            elif event == "stop":
                connector.notify_timer_stopped(user, timer)
        except Exception as exc:
            logger.debug("SlackConnector.notify_for_user failed: %s", exc)

    @classmethod
    def for_user(cls, user) -> Optional["SlackConnector"]:
        from app.models import Integration

        if not user:
            return None
        integration = Integration.query.filter_by(provider=PROVIDER_KEY, user_id=user.id).first()
        if not integration:
            return None
        return cls(integration=integration, credentials=None)

    @classmethod
    def for_any_active(cls) -> List["SlackConnector"]:
        from app.models import Integration

        rows = Integration.query.filter_by(provider=PROVIDER_KEY, is_active=True).all()
        return [cls(integration=row, credentials=None) for row in rows]

    @classmethod
    def find_by_signing_secret_match(
        cls,
        signature: Optional[str],
        timestamp: Optional[str],
        raw_body: Optional[bytes],
    ) -> Optional["SlackConnector"]:
        """Locate the Slack integration whose signing secret matches the request.

        Slack webhooks are M2M and don't carry our user id, so we walk active
        integrations and stop at the first signature match.
        """
        if not (signature and timestamp and raw_body is not None):
            return None
        for connector in cls.for_any_active():
            try:
                if connector.verify_signature(signature, timestamp, raw_body):
                    return connector
            except Exception:
                continue
        return None
