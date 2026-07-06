"""Tests for Slack attendance slash-command integration."""

import hashlib
import hmac
import time
from unittest.mock import patch
from urllib.parse import urlencode

import pytest

from app import db
from app.integrations.slack_attendance_connector import (
    PROVIDER_KEY,
    SlackAttendanceConnector,
)
from app.models import Integration, User
from app.models.attendance_compliance import AttendanceBreak, AttendanceWorkPeriod, DailyAttendanceRecord
from app.models.workday_session import WorkdaySession
from app.services.attendance_compliance_service import AttendanceComplianceService


SIGNING_SECRET = "test-signing-secret"
BOT_TOKEN = "xoxb-test-token"


def _make_signature(secret: str, body: bytes, timestamp: str | None = None) -> tuple[str, str]:
    ts = timestamp or str(int(time.time()))
    base = f"v0:{ts}:".encode("utf-8") + body
    sig = "v0=" + hmac.new(secret.encode("utf-8"), base, hashlib.sha256).hexdigest()
    return sig, ts


def _slash_form(command: str, slack_user_id: str = "U_SLACK_1", channel_id: str = "C_ATTEND") -> dict:
    return {
        "command": command,
        "user_id": slack_user_id,
        "channel_id": channel_id,
        "team_id": "T_TEST",
        "text": "",
    }


@pytest.fixture
def slack_attendance_integration(app):
    with app.app_context():
        integration = Integration(
            name="Slack Attendance",
            provider=PROVIDER_KEY,
            user_id=None,
            is_global=True,
            is_active=True,
            config={
                "bot_token": BOT_TOKEN,
                "signing_secret": SIGNING_SECRET,
                "attendance_channel_id": "C_ATTEND",
            },
        )
        db.session.add(integration)
        db.session.commit()
        yield integration
        Integration.query.filter_by(provider=PROVIDER_KEY).delete()
        db.session.commit()


@pytest.fixture
def linked_user(app):
    with app.app_context():
        user = User(
            username="slack_att_user",
            email="slack.user@example.com",
            role="user",
        )
        user.slack_user_id = "U_SLACK_1"
        user.set_password("test")
        db.session.add(user)
        db.session.commit()
        yield user
        AttendanceBreak.query.filter_by(user_id=user.id).delete()
        AttendanceWorkPeriod.query.filter_by(user_id=user.id).delete()
        DailyAttendanceRecord.query.filter_by(user_id=user.id).delete()
        WorkdaySession.query.filter_by(user_id=user.id).delete()
        db.session.delete(user)
        db.session.commit()


class TestSlackAttendanceConnector:
    def test_resolve_user_by_slack_user_id(self, app, slack_attendance_integration, linked_user):
        with app.app_context():
            connector = SlackAttendanceConnector.for_global()
            user = connector.resolve_user("U_SLACK_1")
            assert user is not None
            assert user.id == linked_user.id

    def test_resolve_user_by_email_fallback(self, app, slack_attendance_integration):
        with app.app_context():
            user = User(username="email_match_user", email="match@example.com", role="user")
            user.set_password("test")
            db.session.add(user)
            db.session.commit()

            connector = SlackAttendanceConnector.for_global()
            with patch.object(
                connector,
                "_fetch_slack_user_email",
                return_value="match@example.com",
            ):
                resolved = connector.resolve_user("U_NEW_SLACK")
            assert resolved is not None
            assert resolved.id == user.id
            assert resolved.slack_user_id == "U_NEW_SLACK"

            db.session.delete(user)
            db.session.commit()

    def test_clock_in_command(self, app, slack_attendance_integration, linked_user):
        with app.app_context():
            connector = SlackAttendanceConnector.for_global()
            result = connector.handle_slash_command(_slash_form("/in"))
            body = result["body"]
            assert body["response_type"] == "in_channel"
            assert "clocked in" in body["text"].lower()
            assert AttendanceComplianceService().get_active_work_period(linked_user.id) is not None
            AttendanceComplianceService().clock_out(linked_user.id)

    def test_break_flow(self, app, slack_attendance_integration, linked_user):
        with app.app_context():
            connector = SlackAttendanceConnector.for_global()
            connector.handle_slash_command(_slash_form("/in"))
            brb = connector.handle_slash_command(_slash_form("/brb"))
            assert brb["body"]["response_type"] == "in_channel"
            assert "break" in brb["body"]["text"].lower()

            back = connector.handle_slash_command(_slash_form("/back"))
            assert back["body"]["response_type"] == "in_channel"
            assert "back" in back["body"]["text"].lower()

            connector.handle_slash_command(_slash_form("/out"))

    def test_double_clock_in_error(self, app, slack_attendance_integration, linked_user):
        with app.app_context():
            connector = SlackAttendanceConnector.for_global()
            connector.handle_slash_command(_slash_form("/in"))
            again = connector.handle_slash_command(_slash_form("/in"))
            assert again["body"]["response_type"] == "ephemeral"
            assert "active" in again["body"]["text"].lower()
            connector.handle_slash_command(_slash_form("/out"))

    def test_break_without_clock_in_error(self, app, slack_attendance_integration, linked_user):
        with app.app_context():
            connector = SlackAttendanceConnector.for_global()
            result = connector.handle_slash_command(_slash_form("/brb"))
            assert result["body"]["response_type"] == "ephemeral"
            assert "start work" in result["body"]["text"].lower()

    def test_unknown_slack_user(self, app, slack_attendance_integration):
        with app.app_context():
            connector = SlackAttendanceConnector.for_global()
            with patch.object(connector, "_fetch_slack_user_email", return_value=None):
                result = connector.handle_slash_command(_slash_form("/in", slack_user_id="U_UNKNOWN"))
            assert result["body"]["response_type"] == "ephemeral"
            assert "not linked" in result["body"]["text"].lower()

    def test_wrong_channel_rejected(self, app, slack_attendance_integration, linked_user):
        with app.app_context():
            connector = SlackAttendanceConnector.for_global()
            result = connector.handle_slash_command(
                _slash_form("/in", channel_id="C_OTHER")
            )
            assert result["body"]["response_type"] == "ephemeral"
            assert "attendance channel" in result["body"]["text"].lower()


class TestSlackAttendanceRoutes:
    def test_invalid_signature_rejected(self, client, slack_attendance_integration):
        body = urlencode(_slash_form("/in")).encode("utf-8")
        response = client.post(
            "/api/integrations/slack/attendance",
            data=body,
            content_type="application/x-www-form-urlencoded",
            headers={
                "X-Slack-Signature": "v0=invalid",
                "X-Slack-Request-Timestamp": str(int(time.time())),
            },
        )
        assert response.status_code == 401

    def test_signed_clock_in_request(self, client, app, slack_attendance_integration, linked_user):
        form = _slash_form("/in")
        body = urlencode(form).encode("utf-8")
        sig, ts = _make_signature(SIGNING_SECRET, body)

        response = client.post(
            "/api/integrations/slack/attendance",
            data=body,
            content_type="application/x-www-form-urlencoded",
            headers={
                "X-Slack-Signature": sig,
                "X-Slack-Request-Timestamp": ts,
            },
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["response_type"] == "in_channel"

        with app.app_context():
            AttendanceComplianceService().clock_out(linked_user.id)

    def test_admin_config_requires_admin(self, client, user):
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = client.get("/api/integrations/slack-attendance/status")
        assert response.status_code == 403

    def test_admin_can_save_config(self, client, admin_user):
        with client.session_transaction() as sess:
            sess["_user_id"] = str(admin_user.id)

        response = client.post(
            "/api/integrations/slack-attendance/config",
            json={
                "bot_token": BOT_TOKEN,
                "signing_secret": SIGNING_SECRET,
                "attendance_channel_id": "C_ATTEND",
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.get_json().get("ok") is True

        status = client.get("/api/integrations/slack-attendance/status")
        assert status.get_json().get("connected") is True

        Integration.query.filter_by(provider=PROVIDER_KEY).delete()
        db.session.commit()
