"""Tests for NotificationService smart notification eligibility."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import insert, update
from zoneinfo import ZoneInfo

from app import db
from app.models import TimeEntry, User, UserSmartNotificationDismissal
from app.services.notification_service import (
    KIND_LONG_TIMER,
    KIND_MISSED_CLOCK_IN,
    KIND_NO_TRACKING,
    NotificationService,
    get_today_summary_for_user,
    parse_hhmm,
    user_local_today_bounds_utc,
)


def _commit_user_prefs(user_id: int, **values):
    db.session.execute(update(User).where(User.id == user_id).values(**values))
    db.session.commit()


def _insert_time_entry(**kwargs):
    """Insert via Core to avoid ORM audit hooks on TimeEntry."""
    defaults = {
        "notes": "notif_test",
        "source": "manual",
        "billable": True,
        "paid": False,
        "break_seconds": 0,
        "tags": None,
        "client_id": None,
        "task_id": None,
        "invoice_number": None,
        "paused_at": None,
    }
    row = {**defaults, **kwargs}
    if "created_at" not in row:
        row["created_at"] = row["start_time"]
    if "updated_at" not in row:
        row["updated_at"] = row["start_time"]
    db.session.execute(insert(TimeEntry.__table__).values(**row))
    db.session.commit()


@pytest.mark.unit
def test_parse_hhmm():
    assert parse_hhmm("16:00") == (16, 0)
    assert parse_hhmm("09:30") == (9, 30)
    assert parse_hhmm("") is None
    assert parse_hhmm("25:00") is None


@pytest.mark.unit
def test_build_disabled_returns_empty(app, user):
    with app.app_context():
        _commit_user_prefs(user.id, smart_notifications_enabled=False)
        user = db.session.get(User, user.id)
        out = NotificationService.build_for_user(user)
        assert out["notifications"] == []
        assert out["meta"]["enabled"] is False


@pytest.mark.unit
def test_long_timer_notification(app, user, project):
    with app.app_context():
        _commit_user_prefs(
            user.id,
            smart_notifications_enabled=True,
            smart_notify_long_timer=True,
            smart_notify_no_tracking=False,
            smart_notify_daily_summary=False,
            timezone="UTC",
        )
        user = db.session.get(User, user.id)
        now_utc = datetime(2026, 6, 10, 18, 0, 0, tzinfo=timezone.utc)
        started = datetime(2026, 6, 10, 12, 0, 0)
        _insert_time_entry(
            user_id=user.id,
            project_id=project.id,
            start_time=started,
            end_time=None,
            duration_seconds=None,
        )

        out = NotificationService.build_for_user(user, now_utc=now_utc)
        kinds = [n["kind"] for n in out["notifications"]]
        assert KIND_LONG_TIMER in kinds


@pytest.mark.unit
def test_no_tracking_in_slot(app, user, project):
    with app.app_context():
        _commit_user_prefs(
            user.id,
            smart_notifications_enabled=True,
            smart_notify_no_tracking=True,
            smart_notify_long_timer=False,
            smart_notify_daily_summary=False,
            timezone="Europe/Rome",
        )
        user = db.session.get(User, user.id)
        now_utc = datetime(2026, 6, 10, 14, 5, 0, tzinfo=timezone.utc)

        with patch("app.utils.timezone.now_in_user_timezone") as m_now:
            m_now.return_value = datetime(2026, 6, 10, 16, 5, tzinfo=ZoneInfo("Europe/Rome"))
            out = NotificationService.build_for_user(user, now_utc=now_utc)

        kinds = [n["kind"] for n in out["notifications"]]
        assert KIND_NO_TRACKING in kinds


@pytest.mark.unit
def test_no_tracking_suppressed_when_timer_active(app, user, project):
    with app.app_context():
        _commit_user_prefs(
            user.id,
            smart_notifications_enabled=True,
            smart_notify_no_tracking=True,
            smart_notify_long_timer=False,
            smart_notify_daily_summary=False,
            timezone="Europe/Rome",
        )
        user = db.session.get(User, user.id)
        now_utc = datetime(2026, 6, 10, 14, 5, 0, tzinfo=timezone.utc)
        _insert_time_entry(
            user_id=user.id,
            project_id=project.id,
            start_time=datetime(2026, 6, 10, 15, 0, 0),
            end_time=None,
            duration_seconds=None,
        )

        with patch("app.utils.timezone.now_in_user_timezone") as m_now:
            m_now.return_value = datetime(2026, 6, 10, 16, 5, tzinfo=ZoneInfo("Europe/Rome"))
            out = NotificationService.build_for_user(user, now_utc=now_utc)

        kinds = [n["kind"] for n in out["notifications"]]
        assert KIND_NO_TRACKING not in kinds


@pytest.mark.unit
def test_dismissal_hides_kind(app, user, project):
    with app.app_context():
        _commit_user_prefs(
            user.id,
            smart_notifications_enabled=True,
            smart_notify_long_timer=True,
            smart_notify_no_tracking=False,
            smart_notify_daily_summary=False,
            timezone="UTC",
        )
        user = db.session.get(User, user.id)
        now_utc = datetime(2026, 6, 10, 18, 0, 0, tzinfo=timezone.utc)
        _, _, local_date = user_local_today_bounds_utc(user)
        db.session.execute(
            insert(UserSmartNotificationDismissal.__table__).values(
                user_id=user.id,
                local_date=local_date,
                kind=KIND_LONG_TIMER,
                dismissed_at=datetime.utcnow(),
            )
        )
        db.session.commit()
        _insert_time_entry(
            user_id=user.id,
            project_id=project.id,
            start_time=datetime(2026, 6, 10, 12, 0, 0),
            end_time=None,
            duration_seconds=None,
        )

        out = NotificationService.build_for_user(user, now_utc=now_utc)
        assert all(n["kind"] != KIND_LONG_TIMER for n in out["notifications"])


@pytest.mark.unit
def test_max_per_day_truncates(app, user, project):
    with app.app_context():
        app.config["SMART_NOTIFY_MAX_PER_DAY"] = 1
        _commit_user_prefs(
            user.id,
            smart_notifications_enabled=True,
            smart_notify_long_timer=True,
            smart_notify_no_tracking=True,
            smart_notify_daily_summary=True,
            timezone="Europe/Rome",
        )
        user = db.session.get(User, user.id)
        now_utc = datetime(2026, 6, 10, 14, 5, 0, tzinfo=timezone.utc)
        _insert_time_entry(
            user_id=user.id,
            project_id=project.id,
            start_time=datetime(2026, 6, 10, 12, 0, 0),
            end_time=None,
            duration_seconds=None,
        )

        with patch("app.utils.timezone.now_in_user_timezone") as m_now:
            m_now.return_value = datetime(2026, 6, 10, 16, 5, tzinfo=ZoneInfo("Europe/Rome"))
            out = NotificationService.build_for_user(user, now_utc=now_utc)

        assert len(out["notifications"]) <= 1
        if out["notifications"]:
            assert out["notifications"][0]["kind"] == KIND_LONG_TIMER


@pytest.mark.unit
def test_get_today_summary_for_user(app, user, project):
    with app.app_context():
        _commit_user_prefs(user.id, timezone="UTC")
        user = db.session.get(User, user.id)
        start = datetime(2026, 6, 10, 10, 0, 0)
        end = datetime(2026, 6, 10, 11, 0, 0)
        _insert_time_entry(
            user_id=user.id,
            project_id=project.id,
            start_time=start,
            end_time=end,
            duration_seconds=3600,
        )
        frozen_local = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)
        with patch("app.utils.timezone.now_in_user_timezone", return_value=frozen_local):
            s = get_today_summary_for_user(user)
        assert s["hours"] == 1.0
        assert s["projects"] == 1


@pytest.mark.unit
def test_missed_clock_in_notification_on_workday(app, user):
    with app.app_context():
        _commit_user_prefs(
            user.id,
            smart_notifications_enabled=True,
            smart_notify_missed_clock_in=True,
            smart_notify_missed_clock_in_at="09:30",
            smart_notify_no_tracking=False,
            smart_notify_long_timer=False,
            smart_notify_daily_summary=False,
            timezone="Europe/Brussels",
        )
        user = db.session.get(User, user.id)
        now_utc = datetime(2026, 6, 10, 7, 35, 0, tzinfo=timezone.utc)  # 09:35 Brussels (CEST)
        with patch("app.utils.timezone.now_in_user_timezone") as m_now:
            m_now.return_value = datetime(2026, 6, 10, 9, 35, tzinfo=ZoneInfo("Europe/Brussels"))
            out = NotificationService.build_for_user(user, now_utc=now_utc)
        kinds = [n["kind"] for n in out["notifications"]]
        assert KIND_MISSED_CLOCK_IN in kinds
