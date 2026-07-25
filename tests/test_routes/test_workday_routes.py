"""Route tests for workday attendance pages."""

from datetime import timedelta

import pytest

from app import db
from app.models.attendance_compliance import AttendanceWorkPeriod, DailyAttendanceRecord
from app.models.time_entry import local_now
from app.services.attendance_compliance_service import AttendanceComplianceService
from app.services.workday_session_service import WorkdaySessionService


@pytest.mark.routes
def test_workday_history_renders_attendance_dates(authenticated_client, app, user):
    """Regression: work_date is a plain date and must not crash user_date formatting."""
    with app.app_context():
        user = db.session.merge(user)
        svc = AttendanceComplianceService()
        clock_in = svc.clock_in(user.id, source="manual")
        assert clock_in["success"] is True
        clock_out = svc.clock_out(user.id)
        assert clock_out["success"] is True

        record = DailyAttendanceRecord.query.filter_by(user_id=user.id).first()
        assert record is not None
        work_date = record.work_date

    try:
        response = authenticated_client.get("/workday/history")
        assert response.status_code == 200
        body = response.data.decode("utf-8", errors="replace")
        assert work_date.isoformat() in body or work_date.strftime("%d.%m.%Y") in body
    finally:
        with app.app_context():
            user = db.session.merge(user)
            AttendanceWorkPeriod.query.filter_by(user_id=user.id).delete()
            DailyAttendanceRecord.query.filter_by(user_id=user.id).delete()
            db.session.commit()


@pytest.mark.routes
def test_end_workday_with_leave_time_for_overnight_session(authenticated_client, app, user):
    """POST /workday/end accepts end_time to correct a forgotten overnight clock-out."""
    from app.models import WorkdaySession

    leave_iso = None
    session_id = None
    with app.app_context():
        user = db.session.merge(user)
        svc = WorkdaySessionService()
        start = svc.start_workday(user.id, source="manual")
        assert start["success"] is True
        session = start["session"]
        yesterday_start = (local_now() - timedelta(days=1)).replace(
            hour=9, minute=0, second=0, microsecond=0
        )
        session.start_time = yesterday_start
        period = AttendanceWorkPeriod.query.filter_by(workday_session_id=session.id).first()
        period.start_time = yesterday_start
        db.session.commit()
        leave = yesterday_start.replace(hour=17, minute=30)
        leave_iso = leave.strftime("%Y-%m-%dT%H:%M")
        session_id = session.id

    response = authenticated_client.post(
        "/workday/end",
        data={"end_time": leave_iso},
        follow_redirects=False,
    )
    assert response.status_code in (302, 303)

    with app.app_context():
        session = db.session.get(WorkdaySession, session_id)
        assert session is not None
        assert session.end_time is not None
        assert session.end_time.hour == 17
        assert session.end_time.minute == 30
        assert session.duration_seconds == int(8.5 * 3600)


@pytest.mark.routes
def test_dashboard_shows_overnight_clock_out_modal(authenticated_client, app, user):
    with app.app_context():
        user = db.session.merge(user)
        svc = WorkdaySessionService()
        start = svc.start_workday(user.id, source="manual")
        assert start["success"] is True
        session = start["session"]
        yesterday_start = (local_now() - timedelta(days=1)).replace(
            hour=9, minute=0, second=0, microsecond=0
        )
        session.start_time = yesterday_start
        period = AttendanceWorkPeriod.query.filter_by(workday_session_id=session.id).first()
        period.start_time = yesterday_start
        db.session.commit()

    response = authenticated_client.get("/dashboard")
    assert response.status_code == 200
    body = response.data.decode("utf-8", errors="replace")
    assert "overnightClockOutModal" in body
    assert "overnightLeaveTime" in body
