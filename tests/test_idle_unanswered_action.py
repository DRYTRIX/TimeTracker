"""Tests for Settings.idle_unanswered_action (Issue #722).

When the "Still working?" grace window expires unanswered:
- review (default): flag for review, timer keeps running
- auto_stop: stop credited to last_active + idle_timeout
"""

from datetime import timedelta

from app import db
from app.models import Settings
from app.models.time_entry import TimeEntry, local_now
from app.utils.scheduled_tasks import check_idle_timers


def _make_stale_notified_timer(user, project, *, paused=False):
    """Open timer past idle window with grace already expired."""
    now = local_now()
    timer = TimeEntry(
        user_id=user.id,
        project_id=project.id,
        start_time=now - timedelta(hours=3),
        source="auto",
        billable=True,
    )
    timer.last_heartbeat_at = now - timedelta(hours=2)
    timer.idle_notified_at = now - timedelta(minutes=10)
    if paused:
        timer.paused_at = now - timedelta(minutes=90)
    db.session.add(timer)
    db.session.commit()
    db.session.refresh(timer)
    return timer


def test_idle_credited_stop_time_helper(app, user, project):
    now = local_now()
    timer = TimeEntry(
        user_id=user.id,
        project_id=project.id,
        start_time=now - timedelta(hours=2),
        source="auto",
        billable=True,
    )
    timer.last_heartbeat_at = now - timedelta(hours=1)
    db.session.add(timer)
    db.session.commit()

    stop_at = timer.idle_credited_stop_time(30, now=now)
    expected = timer.last_heartbeat_at + timedelta(minutes=30)
    assert abs((stop_at - expected).total_seconds()) < 1

    # Cap at now when last_active + window is in the future
    timer.last_heartbeat_at = now - timedelta(minutes=5)
    db.session.commit()
    stop_at = timer.idle_credited_stop_time(30, now=now)
    assert abs((stop_at - now).total_seconds()) < 1


def test_auto_stop_mode_stops_after_grace(app, user, project):
    settings = Settings.get_settings()
    settings.idle_timeout_minutes = 30
    settings.idle_unanswered_action = "auto_stop"
    settings.idle_auto_stop_hours = 0
    db.session.commit()

    timer = _make_stale_notified_timer(user, project)
    last_hb = timer.last_heartbeat_at

    check_idle_timers()
    db.session.refresh(timer)

    assert timer.end_time is not None
    assert timer.idle_flagged_at is None
    assert timer.idle_notified_at is None
    expected = last_hb + timedelta(minutes=30)
    end = timer.end_time
    if getattr(end, "tzinfo", None) is not None:
        end = end.replace(tzinfo=None)
    if getattr(expected, "tzinfo", None) is not None:
        expected = expected.replace(tzinfo=None)
    assert abs((end - expected).total_seconds()) < 5


def test_review_mode_flags_without_stopping(app, user, project):
    settings = Settings.get_settings()
    settings.idle_timeout_minutes = 30
    settings.idle_unanswered_action = "review"
    settings.idle_auto_stop_hours = 0
    db.session.commit()

    timer = _make_stale_notified_timer(user, project)

    check_idle_timers()
    db.session.refresh(timer)

    assert timer.end_time is None
    assert timer.idle_flagged_at is not None


def test_auto_stop_skips_paused_timer(app, user, project):
    settings = Settings.get_settings()
    settings.idle_unanswered_action = "auto_stop"
    db.session.commit()

    paused = _make_stale_notified_timer(user, project, paused=True)
    check_idle_timers()
    db.session.refresh(paused)

    assert paused.end_time is None
    assert paused.idle_flagged_at is None


def test_timer_status_returns_idle_unanswered_action(client_with_token, app):
    with app.app_context():
        settings = Settings.get_settings()
        settings.idle_unanswered_action = "auto_stop"
        db.session.commit()

    response = client_with_token.get("/api/v1/timer/status")
    assert response.status_code == 200
    data = response.get_json()
    assert data["idle_unanswered_action"] == "auto_stop"
    assert "idle_timeout_minutes" in data


def test_admin_rejects_invalid_idle_unanswered_action(admin_authenticated_client, app):
    with app.app_context():
        settings = Settings.get_settings()
        settings.idle_unanswered_action = "review"
        db.session.commit()
        data = {
            "timezone": settings.timezone or "UTC",
            "date_format": settings.date_format or "YYYY-MM-DD",
            "time_format": settings.time_format or "24h",
            "currency": settings.currency or "EUR",
            "rounding_minutes": str(settings.rounding_minutes or 1),
            "idle_timeout_minutes": str(settings.idle_timeout_minutes or 30),
            "idle_unanswered_action": "delete_everything",
            "idle_auto_stop_hours": "0",
            "backup_retention_days": str(settings.backup_retention_days or 30),
            "backup_time": settings.backup_time or "02:00",
            "export_delimiter": settings.export_delimiter or ",",
            "company_name": settings.company_name or "Test Co",
            "invoice_prefix": settings.invoice_prefix or "INV",
            "invoice_number_pattern": settings.invoice_number_pattern or "{PREFIX}-{SEQ}",
            "invoice_start_number": str(settings.invoice_start_number or 1000),
            "quote_prefix": getattr(settings, "quote_prefix", None) or "QUO",
            "quote_number_pattern": getattr(settings, "quote_number_pattern", None) or "{PREFIX}-{SEQ}",
            "quote_start_number": str(getattr(settings, "quote_start_number", None) or 1),
        }

    response = admin_authenticated_client.post("/admin/settings", data=data, follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        settings = Settings.get_settings()
        assert settings.idle_unanswered_action == "review"


def test_admin_accepts_auto_stop_action(admin_authenticated_client, app):
    with app.app_context():
        settings = Settings.get_settings()
        settings.idle_unanswered_action = "review"
        db.session.commit()
        data = {
            "timezone": settings.timezone or "UTC",
            "date_format": settings.date_format or "YYYY-MM-DD",
            "time_format": settings.time_format or "24h",
            "currency": settings.currency or "EUR",
            "rounding_minutes": str(settings.rounding_minutes or 1),
            "idle_timeout_minutes": str(settings.idle_timeout_minutes or 30),
            "idle_unanswered_action": "auto_stop",
            "idle_auto_stop_hours": "0",
            "backup_retention_days": str(settings.backup_retention_days or 30),
            "backup_time": settings.backup_time or "02:00",
            "export_delimiter": settings.export_delimiter or ",",
            "company_name": settings.company_name or "Test Co",
            "invoice_prefix": settings.invoice_prefix or "INV",
            "invoice_number_pattern": settings.invoice_number_pattern or "{PREFIX}-{SEQ}",
            "invoice_start_number": str(settings.invoice_start_number or 1000),
            "quote_prefix": getattr(settings, "quote_prefix", None) or "QUO",
            "quote_number_pattern": getattr(settings, "quote_number_pattern", None) or "{PREFIX}-{SEQ}",
            "quote_start_number": str(getattr(settings, "quote_start_number", None) or 1),
        }

    response = admin_authenticated_client.post("/admin/settings", data=data, follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        settings = Settings.get_settings()
        assert settings.idle_unanswered_action == "auto_stop"
