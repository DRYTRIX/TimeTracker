"""
Workspace-level Slack attendance connector.

Employees run /in, /brb, /back, and /out in a dedicated Slack channel to
record clock-in/out and breaks via AttendanceComplianceService.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional

import requests

from app.integrations.base import BaseConnector
from app.utils.db import safe_commit
from app.utils.secret_crypto import decrypt_if_needed, encrypt_if_possible
from app.utils.secret_crypto import is_configured as secrets_encryption_configured

logger = logging.getLogger(__name__)

PROVIDER_KEY = "slack_attendance"
HTTP_TIMEOUT = 10
SLACK_POST_MESSAGE = "https://slack.com/api/chat.postMessage"
SLACK_USERS_INFO = "https://slack.com/api/users.info"
SLACK_SIGNATURE_VERSION = "v0"
SLACK_REQUEST_MAX_AGE = 60 * 5

ATTENDANCE_COMMANDS = {
    "/in": "clock_in",
    "/brb": "start_break",
    "/back": "end_break",
    "/out": "clock_out",
}


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
            logger.warning("Slack attendance secret encryption failed: %s", exc)
    return value


def _dec(value: Optional[str]) -> str:
    if not value:
        return ""
    try:
        return decrypt_if_needed(value)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Slack attendance secret decryption failed: %s", exc)
        return ""


class SlackAttendanceConnector(BaseConnector):
    """Global Slack integration for workspace attendance slash commands."""

    display_name = "Slack Attendance"
    description = "Clock in/out and breaks from Slack with /in, /brb, /back, /out"
    icon = "slack"

    def __init__(self, integration=None, credentials=None):
        super().__init__(integration, credentials)

    @property
    def provider_name(self) -> str:
        return PROVIDER_KEY

    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        raise NotImplementedError("SlackAttendanceConnector uses a bot token (no OAuth flow here)")

    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        raise NotImplementedError("SlackAttendanceConnector uses a bot token (no OAuth flow here)")

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
        if not integration:
            return {"ok": False, "error": "Integration not configured"}
        cfg: Dict[str, Any] = dict(integration.config or {})

        bot_token = (payload.get("bot_token") or "").strip()
        if bot_token:
            cfg["bot_token"] = _enc(bot_token)
        signing = (payload.get("signing_secret") or "").strip()
        if signing:
            cfg["signing_secret"] = _enc(signing)

        if "attendance_channel_id" in payload:
            cfg["attendance_channel_id"] = (payload.get("attendance_channel_id") or "").strip() or None

        integration.config = cfg
        integration.is_active = bool(cfg.get("bot_token") and cfg.get("signing_secret"))
        integration.updated_at = datetime.utcnow()

        if not safe_commit("slack_attendance_save_config", {"integration_id": integration.id}):
            return {"ok": False, "error": "Database error while saving configuration"}
        return {"ok": True, "is_active": bool(integration.is_active)}

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
        expected = SLACK_SIGNATURE_VERSION + "=" + hmac.new(secret.encode("utf-8"), base, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def handle_slash_command(self, form: Dict[str, str]) -> Dict[str, Any]:
        if not self._is_ready():
            return self._ephemeral("Slack attendance integration is not configured.")

        channel_id = (form.get("channel_id") or "").strip()
        allowed_channel = (self._cfg().get("attendance_channel_id") or "").strip()
        if allowed_channel and channel_id and channel_id != allowed_channel:
            return self._ephemeral(
                "This command can only be used in the configured attendance channel."
            )

        command = (form.get("command") or "").strip().lower()
        action = ATTENDANCE_COMMANDS.get(command)
        if not action:
            return self._ephemeral(
                "Unknown command. Available: `/in`, `/brb`, `/back`, `/out`."
            )

        slack_user_id = (form.get("user_id") or "").strip()
        if not slack_user_id:
            return self._ephemeral("Missing Slack user ID.")

        user = self.resolve_user(slack_user_id)
        if not user:
            return self._ephemeral(
                "Your Slack account is not linked to TimeTracker. "
                "Add your Slack user ID in User Settings, or ensure your Slack "
                "profile email matches your TimeTracker email."
            )

        return self._dispatch_action(action, user)

    def resolve_user(self, slack_user_id: str):
        from app import db
        from app.models import User

        user = User.query.filter_by(slack_user_id=slack_user_id).first()
        if user:
            return user

        email = self._fetch_slack_user_email(slack_user_id)
        if not email:
            return None

        user = User.query.filter(db.func.lower(User.email) == email.lower()).first()
        if not user:
            return None

        existing = User.query.filter_by(slack_user_id=slack_user_id).first()
        if existing and existing.id != user.id:
            return None

        user.slack_user_id = slack_user_id
        if not safe_commit("slack_attendance_link_user", {"user_id": user.id, "slack_user_id": slack_user_id}):
            db.session.rollback()
            return None
        return user

    def _fetch_slack_user_email(self, slack_user_id: str) -> Optional[str]:
        token = self._bot_token()
        if not token:
            return None
        try:
            resp = requests.get(
                SLACK_USERS_INFO,
                headers={"Authorization": f"Bearer {token}"},
                params={"user": slack_user_id},
                timeout=HTTP_TIMEOUT,
            )
        except requests.RequestException as exc:
            logger.warning("Slack users.info failed for %s: %s", slack_user_id, exc)
            return None
        data = resp.json() or {}
        if not data.get("ok"):
            logger.warning("Slack users.info error for %s: %s", slack_user_id, data.get("error"))
            return None
        profile = (data.get("user") or {}).get("profile") or {}
        email = (profile.get("email") or "").strip()
        return email or None

    def _dispatch_action(self, action: str, user) -> Dict[str, Any]:
        from app.services.attendance_compliance_service import AttendanceComplianceService
        from app.services.workday_session_service import WorkdaySessionService

        display = getattr(user, "display_name", None) or user.username or "User"
        now = datetime.now()

        if action == "clock_in":
            result = WorkdaySessionService().start_workday(user.id, source="slack")
            if result.get("success"):
                session = result.get("session")
                at = getattr(session, "start_time", now)
                return self._in_channel(f":white_check_mark: *{display}* clocked in at {self._format_time(at)}")
            return self._ephemeral(result.get("message") or "Could not clock in.")

        if action == "clock_out":
            result = WorkdaySessionService().end_workday(user.id)
            if result.get("success"):
                session = result.get("session")
                at = getattr(session, "end_time", now)
                return self._in_channel(f":door: *{display}* clocked out at {self._format_time(at)}")
            return self._ephemeral(result.get("message") or "Could not clock out.")

        compliance = AttendanceComplianceService()
        if action == "start_break":
            result = compliance.start_break(user.id)
            if result.get("success"):
                brk = result.get("break")
                at = getattr(brk, "start_time", now)
                return self._in_channel(f":coffee: *{display}* started a break at {self._format_time(at)}")
            return self._ephemeral(result.get("message") or "Could not start break.")

        if action == "end_break":
            result = compliance.end_break(user.id)
            if result.get("success"):
                brk = result.get("break")
                at = getattr(brk, "end_time", now)
                return self._in_channel(f":arrow_forward: *{display}* is back at {self._format_time(at)}")
            return self._ephemeral(result.get("message") or "Could not end break.")

        return self._ephemeral("Unknown action.")

    @staticmethod
    def _format_time(value) -> str:
        if hasattr(value, "strftime"):
            return value.strftime("%H:%M")
        return "—"

    @staticmethod
    def _ephemeral(text: str) -> Dict[str, Any]:
        return {"status": 200, "body": {"response_type": "ephemeral", "text": text}}

    @staticmethod
    def _in_channel(text: str) -> Dict[str, Any]:
        return {"status": 200, "body": {"response_type": "in_channel", "text": text}}

    def send_test_message(self) -> Dict[str, Any]:
        if not self._is_ready():
            return {"ok": False, "error": "Integration not configured"}
        channel = self._cfg().get("attendance_channel_id")
        if not channel:
            return {"ok": False, "error": "Attendance channel ID is required for test messages"}
        ok = self._post(channel, ":wave: TimeTracker Slack attendance test message.")
        return {"ok": bool(ok)}

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
            logger.warning("Slack attendance chat.postMessage failed: %s", exc)
            return False
        if resp.status_code != 200:
            return False
        data = resp.json() or {}
        return bool(data.get("ok"))

    @classmethod
    def for_global(cls) -> Optional["SlackAttendanceConnector"]:
        from app.models import Integration

        integration = Integration.query.filter_by(provider=PROVIDER_KEY, is_global=True).first()
        if not integration:
            return None
        return cls(integration=integration, credentials=None)

    @classmethod
    def get_or_create_global(cls) -> "SlackAttendanceConnector":
        from app import db
        from app.models import Integration

        integration = Integration.query.filter_by(provider=PROVIDER_KEY, is_global=True).first()
        if not integration:
            integration = Integration(
                name="Slack Attendance",
                provider=PROVIDER_KEY,
                user_id=None,
                is_global=True,
                is_active=False,
                config={},
            )
            db.session.add(integration)
            safe_commit("slack_attendance_create_global", {"provider": PROVIDER_KEY})
        return cls(integration=integration, credentials=None)
