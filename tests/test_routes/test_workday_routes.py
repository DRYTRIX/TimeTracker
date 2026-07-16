"""Route tests for workday attendance pages."""

import pytest

from app import db
from app.models.attendance_compliance import AttendanceWorkPeriod, DailyAttendanceRecord
from app.services.attendance_compliance_service import AttendanceComplianceService


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
