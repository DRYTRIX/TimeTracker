"""Tests for WorkdaySessionService and working time limits."""

from datetime import timedelta

import pytest

from app import db
from app.models import Settings, User, WorkdaySession, WorkingTimeViolation
from app.models.time_entry import local_now
from app.services.workday_session_service import WorkdaySessionService
from app.services.working_time_limit_service import WorkingTimeLimitService


@pytest.fixture
def workday_user(app):
    with app.app_context():
        user = User(username="workday_test_user", role="user")
        user.set_password("testpass123")
        db.session.add(user)
        db.session.commit()
        yield user
        WorkdaySession.query.filter_by(user_id=user.id).delete()
        WorkingTimeViolation.query.filter_by(user_id=user.id).delete()
        db.session.delete(user)
        db.session.commit()


class TestWorkdaySessionService:
    def test_start_and_end_workday(self, app, workday_user):
        with app.app_context():
            svc = WorkdaySessionService()
            start = svc.start_workday(workday_user.id)
            assert start["success"] is True
            assert start["session"].is_active

            again = svc.start_workday(workday_user.id)
            assert again["success"] is False

            end = svc.end_workday(workday_user.id)
            assert end["success"] is True
            assert end["session"].end_time is not None
            assert end["session"].duration_seconds is not None

    def test_auto_close_stale_sessions(self, app, workday_user):
        with app.app_context():
            old_start = local_now() - timedelta(hours=20)
            session = WorkdaySession(user_id=workday_user.id, start_time=old_start, source="manual")
            db.session.add(session)
            db.session.commit()

            closed = WorkdaySessionService().auto_close_stale_sessions(max_hours=18)
            assert closed == 1
            db.session.refresh(session)
            assert session.end_time is not None
            assert session.auto_closed is True


class TestWorkingTimeLimitService:
    def test_daily_violation_created(self, app, workday_user):
        with app.app_context():
            settings = Settings.get_settings()
            settings.hour_limits_enabled = True
            settings.daily_hour_limit = 1.0
            settings.hour_limit_email_enabled = True
            db.session.commit()

            start = local_now() - timedelta(hours=2)
            session = WorkdaySession(
                user_id=workday_user.id,
                start_time=start,
                end_time=local_now(),
                source="manual",
            )
            session.calculate_duration()
            db.session.add(session)
            db.session.commit()

            svc = WorkingTimeLimitService()
            hours = svc.get_worked_hours_for_day(workday_user.id, local_now().date())
            assert hours >= 1.9

            violations = svc.check_user_limits(workday_user)
            assert len(violations) >= 1
            assert any(v.period_type == WorkingTimeViolation.PERIOD_DAILY for v in violations)

    def test_submit_justification(self, app, workday_user):
        with app.app_context():
            v = WorkingTimeViolation(
                user_id=workday_user.id,
                period_type=WorkingTimeViolation.PERIOD_DAILY,
                period_start=local_now().date(),
                period_end=local_now().date(),
                limit_hours=8.0,
                actual_hours=10.0,
                hours_over=2.0,
            )
            db.session.add(v)
            db.session.commit()

            result = WorkingTimeLimitService().submit_justification(
                v.id, workday_user.id, "Client deadline required extra hours."
            )
            assert result["success"] is True
            assert result["violation"].status == WorkingTimeViolation.STATUS_SUBMITTED
