"""Tests for AttendanceComplianceService (Belgium 2027 compliance)."""

from datetime import date, datetime, timedelta

import pytest

from app.models import Settings, User
from app.models.attendance_compliance import (
    AttendanceCorrectionStatus,
    AttendanceDayStatus,
    AttendanceWorkPeriod,
    DailyAttendanceRecord,
)
from app.models.time_off import LeaveType, TimeOffRequest, TimeOffRequestStatus
from app.services.attendance_compliance_service import AttendanceComplianceService


@pytest.fixture
def compliance_user(app):
    with app.app_context():
        user = User(username="compliance_test_user", role="user")
        user.set_password("test")
        from app import db

        db.session.add(user)
        db.session.commit()
        yield user
        DailyAttendanceRecord.query.filter_by(user_id=user.id).delete()
        AttendanceWorkPeriod.query.filter_by(user_id=user.id).delete()
        db.session.delete(user)
        db.session.commit()


class TestAttendanceComplianceService:
    def test_clock_in_and_out(self, app, compliance_user):
        with app.app_context():
            svc = AttendanceComplianceService()
            start = svc.clock_in(compliance_user.id, source="manual")
            assert start["success"] is True
            assert svc.get_active_work_period(compliance_user.id) is not None

            end = svc.clock_out(compliance_user.id)
            assert end["success"] is True
            assert svc.get_active_work_period(compliance_user.id) is None

            today = date.today()
            hours = svc.get_total_hours(compliance_user.id, today, today)
            assert hours >= 0

    def test_break_during_work(self, app, compliance_user):
        with app.app_context():
            svc = AttendanceComplianceService()
            svc.clock_in(compliance_user.id)
            brk_start = svc.start_break(compliance_user.id)
            assert brk_start["success"] is True
            brk_end = svc.end_break(compliance_user.id)
            assert brk_end["success"] is True
            svc.clock_out(compliance_user.id)

            today = date.today()
            day = DailyAttendanceRecord.query.filter_by(
                user_id=compliance_user.id, work_date=today
            ).first()
            assert day is not None
            assert (day.total_break_seconds or 0) >= 0

    def test_time_off_sync_creates_absence_day(self, app, compliance_user):
        with app.app_context():
            from app import db

            lt = LeaveType(name="Vacation", code="vacation_test", is_paid=True)
            db.session.add(lt)
            db.session.commit()

            req = TimeOffRequest(
                user_id=compliance_user.id,
                leave_type_id=lt.id,
                start_date=date.today(),
                end_date=date.today(),
                status=TimeOffRequestStatus.APPROVED,
            )
            db.session.add(req)
            db.session.commit()

            svc = AttendanceComplianceService()
            count = svc.sync_time_off_request(req)
            assert count == 1

            day = DailyAttendanceRecord.query.filter_by(
                user_id=compliance_user.id, work_date=date.today()
            ).first()
            assert day is not None
            assert day.status == AttendanceDayStatus.ABSENT

    def test_correction_request_and_approve(self, app, compliance_user):
        with app.app_context():
            from app import db

            admin = User(username="compliance_admin", role="admin")
            admin.set_password("test")
            db.session.add(admin)
            db.session.commit()

            svc = AttendanceComplianceService()
            result = svc.clock_in(compliance_user.id)
            period = result["period"]
            svc.clock_out(compliance_user.id)

            corr = svc.request_correction(
                attendance_day_id=period.attendance_day_id,
                entity_type="AttendanceWorkPeriod",
                entity_id=period.id,
                corrected_values={"notes": "Corrected via test"},
                reason="Forgot to add note at clock-out",
                requested_by=compliance_user.id,
            )
            assert corr["success"] is True

            review = svc.review_correction(
                corr["correction"].id,
                admin.id,
                approve=True,
                review_comment="Approved",
            )
            assert review["success"] is True
            assert review["correction"].status == AttendanceCorrectionStatus.APPLIED

    def test_add_missing_work_period_correction(self, app, compliance_user):
        with app.app_context():
            from app import db

            admin = User(username="compliance_admin2", role="admin")
            admin.set_password("test")
            db.session.add(admin)
            db.session.commit()

            svc = AttendanceComplianceService()
            work_date = date.today() - timedelta(days=1)
            start = datetime.combine(work_date, datetime.min.time()).replace(hour=9, minute=0)
            end = datetime.combine(work_date, datetime.min.time()).replace(hour=17, minute=0)

            corr = svc.request_missing_work_period(
                user_id=compliance_user.id,
                work_date=work_date,
                start_time=start,
                end_time=end,
                reason="Forgot to clock in yesterday",
            )
            assert corr["success"] is True

            review = svc.review_correction(corr["correction"].id, admin.id, approve=True)
            assert review["success"] is True

            day = DailyAttendanceRecord.query.filter_by(
                user_id=compliance_user.id, work_date=work_date
            ).first()
            assert day is not None
            assert day.work_periods.count() == 1
            period = day.work_periods.first()
            assert period.start_time.hour == 9
            assert period.end_time.hour == 17

    def test_belgium_inspector_export_shape(self, app, compliance_user):
        with app.app_context():
            svc = AttendanceComplianceService()
            svc.clock_in(compliance_user.id)
            svc.clock_out(compliance_user.id)

            today = date.today()
            rows = svc.belgium_inspector_rows(
                start_date=today,
                end_date=today,
                user_id=compliance_user.id,
            )
            assert len(rows) >= 1
            row = rows[0]
            assert "work_date" in row
            assert "net_work_hours" in row
            assert "has_other_employers" in row
            assert "royal_decree_config_version" in row

    def test_apply_belgium_preset(self, app):
        with app.app_context():
            settings = Settings.get_settings()
            svc = AttendanceComplianceService()
            svc.apply_belgium_preset(settings)
            assert settings.compliance_enabled is True
            assert settings.compliance_jurisdiction_preset == "belgium"
            assert settings.compliance_attendance_retention_years == 10
