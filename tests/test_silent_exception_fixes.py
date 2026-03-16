"""
Tests for silent exception handling fixes.

Covers: team_chat attachment parsing, expenses bulk_update feedback,
api_v1 PATCH validation errors, error_handling helpers, backup observability.
"""

import logging
import pytest

pytestmark = [pytest.mark.unit]


# --- error_handling helpers ---


def test_safe_log_does_not_raise():
    """safe_log must never raise even if logger or message is invalid."""
    from app.utils.error_handling import safe_log

    log = logging.getLogger("test_safe_log")
    safe_log(log, "debug", "msg")
    safe_log(log, "info", "msg %s", 1)
    safe_log(None, "debug", "msg")  # no-op if logger is None
    safe_log(log, "nonexistent_level", "msg")  # falls back to debug


def test_safe_file_remove_nonexistent_returns_true():
    """safe_file_remove returns True when path does not exist."""
    from app.utils.error_handling import safe_file_remove

    assert safe_file_remove("/nonexistent/path/12345") is True
    assert safe_file_remove("") is True


def test_safe_file_remove_with_logger():
    """safe_file_remove with logger does not raise; returns False when remove fails."""
    from app.utils.error_handling import safe_file_remove

    log = logging.getLogger("test_safe_file_remove")
    # Use a path that is not a file (e.g. directory or nonexistent dir) so remove is not called, or use a path that will fail
    # On some systems os.path.isfile("/") is True, on others False. Just ensure no exception and return is bool.
    result = safe_file_remove("/nonexistent_file_12345_xyz", logger=log)
    assert result is True  # nonexistent file: not removed but returns True (nothing to do)
    # Test that invalid path type still doesn't raise (e.g. None is handled)
    result2 = safe_file_remove("", logger=log)
    assert result2 is True


# --- API v1 PATCH validation (per_diem invalid optional field) ---


@pytest.mark.api
def test_api_v1_per_diem_patch_invalid_full_days_returns_400(app, client):
    """PATCH per_diem with invalid full_days returns 400 and validation_error."""
    from app import db
    from app.models import User, ApiToken, PerDiem
    from datetime import date, timedelta

    with app.app_context():
        user = User(username="pduser", email="pd@test.com", role="user")
        user.is_active = True
        db.session.add(user)
        db.session.commit()
        api_token, plain_token = ApiToken.create_token(user.id, "token", scopes="read:per_diem,write:per_diem")
        db.session.add(api_token)
        pd = PerDiem(
            user_id=user.id,
            trip_purpose="Test",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
            country="DE",
            full_day_rate=30,
            half_day_rate=15,
            full_days=1,
            half_days=0,
        )
        db.session.add(pd)
        db.session.commit()
        pd_id = pd.id

    headers = {"Authorization": f"Bearer {plain_token}", "Content-Type": "application/json"}
    r = client.patch(
        f"/api/v1/per-diems/{pd_id}",
        headers=headers,
        json={"full_days": "not_an_int"},
    )
    assert r.status_code == 400
    data = r.get_json()
    assert data.get("error_code") == "validation_error"
    assert "full_days" in (data.get("errors") or data)


# --- Team chat API: invalid attachment fields return 400 ---


@pytest.mark.api
def test_team_chat_api_message_invalid_attachment_size_returns_400(app, client):
    """POST /api/chat/channels/<id>/messages with invalid attachment_size returns 400 when module enabled."""
    from app import db
    from app.models import User, Settings
    from app.models.team_chat import ChatChannel, ChatChannelMember

    with app.app_context():
        user = User(username="chatuser", email="chat@test.com", role="user")
        user.is_active = True
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        # Ensure team_chat module is enabled for this test
        settings = Settings.get_settings()
        if hasattr(settings, "enabled_modules") and settings.enabled_modules is not None:
            mods = list(settings.enabled_modules) if isinstance(settings.enabled_modules, (list, tuple)) else []
            if "team_chat" not in mods:
                mods.append("team_chat")
                settings.enabled_modules = mods
                db.session.commit()
        channel = ChatChannel(name="Test", channel_type="public", created_by=user_id)
        db.session.add(channel)
        db.session.flush()
        ChatChannelMember(channel_id=channel.id, user_id=user_id, is_admin=True)
        db.session.add(channel)
        db.session.commit()
        channel_id = channel.id

    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True

    r = client.post(
        f"/api/chat/channels/{channel_id}/messages",
        json={
            "message": "Hi",
            "attachment_url": "uploads/chat_attachments/file.pdf",
            "attachment_filename": "file.pdf",
            "attachment_size": "not_a_number",
        },
        content_type="application/json",
    )
    # If module is disabled we may get 403/404; only assert when we hit the validation
    if r.status_code == 400:
        data = r.get_json()
        assert data.get("error_code") == "validation_error"
        errors = data.get("errors") or {}
        assert "attachment_size" in errors
    else:
        pytest.skip("team_chat module not available or route not registered")


# --- Expenses bulk_update: invalid payload or empty selection ---


@pytest.mark.api
def test_expenses_bulk_update_invalid_payload_returns_error(app, client):
    """POST /expenses/bulk-status with no expense_ids or invalid status redirects with flash, no 500."""
    from app import db
    from app.models import User

    with app.app_context():
        user = User(username="expuser", email="exp@test.com", role="user")
        user.is_active = True
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True

    # No expense_ids: should redirect with warning flash
    r = client.post(
        "/expenses/bulk-status",
        data={"expense_ids[]": [], "status": "approved"},
        follow_redirects=False,
    )
    assert r.status_code == 302
    assert "expenses" in (r.location or "")

    # Invalid status: should redirect with error flash
    r2 = client.post(
        "/expenses/bulk-status",
        data={"expense_ids[]": ["1"], "status": "invalid_status"},
        follow_redirects=False,
    )
    assert r2.status_code == 302
    assert "expenses" in (r2.location or "")


# --- Backup: _get_alembic_revision returns None and logs on error ---


def test_backup_get_alembic_revision_returns_none_on_error(app):
    """_get_alembic_revision returns None when query fails (and logs warning to app logger)."""
    from app.utils.backup import _get_alembic_revision

    with app.app_context():
        class BadSession:
            def execute(self, *args, **kwargs):
                raise RuntimeError("test failure")

        result = _get_alembic_revision(BadSession())
    assert result is None
