"""Belgium/EU attendance compliance models — unified daily work + break + absence records."""

import enum
from datetime import date, datetime

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Index, UniqueConstraint

from app import db
from app.models.time_entry import local_now


class AttendanceDayStatus(enum.Enum):
    PRESENT = "present"
    ABSENT = "absent"
    PARTIAL = "partial"
    HOLIDAY = "holiday"


class AttendanceCorrectionStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"


class AttendanceBreakType(enum.Enum):
    REST = "rest"
    MEAL = "meal"
    OTHER = "other"


class DailyAttendanceRecord(db.Model):
    """One compliance record per user per calendar work day."""

    __tablename__ = "daily_attendance_records"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    work_date = db.Column(db.Date, nullable=False, index=True)

    status = db.Column(
        SQLEnum(AttendanceDayStatus, values_callable=lambda x: [e.value for e in x]),
        default=AttendanceDayStatus.PRESENT,
        nullable=False,
        index=True,
    )

    time_off_request_id = db.Column(db.Integer, db.ForeignKey("time_off_requests.id"), nullable=True, index=True)
    leave_type_id = db.Column(db.Integer, db.ForeignKey("leave_types.id"), nullable=True, index=True)

    total_work_seconds = db.Column(db.Integer, nullable=False, default=0)
    total_break_seconds = db.Column(db.Integer, nullable=False, default=0)

    locked_at = db.Column(db.DateTime, nullable=True)
    locked_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    timesheet_period_id = db.Column(db.Integer, db.ForeignKey("timesheet_periods.id"), nullable=True, index=True)

    compliance_notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=local_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=local_now, onupdate=local_now, nullable=False)

    user = db.relationship(
        "User", foreign_keys=[user_id], backref=db.backref("daily_attendance_records", lazy="dynamic")
    )
    locker = db.relationship("User", foreign_keys=[locked_by])
    time_off_request = db.relationship("TimeOffRequest", backref=db.backref("attendance_days", lazy="dynamic"))
    leave_type = db.relationship("LeaveType")
    timesheet_period = db.relationship("TimesheetPeriod")
    work_periods = db.relationship(
        "AttendanceWorkPeriod",
        back_populates="attendance_day",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    breaks = db.relationship(
        "AttendanceBreak",
        back_populates="attendance_day",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("user_id", "work_date", name="uq_daily_attendance_user_date"),
        Index("ix_daily_attendance_user_date", "user_id", "work_date"),
    )

    @property
    def is_locked(self) -> bool:
        return self.locked_at is not None

    def recalculate_totals(self):
        work_secs = 0
        break_secs = 0
        for period in self.work_periods:
            period.calculate_duration()
            work_secs += period.duration_seconds or 0
        for brk in self.breaks:
            brk.calculate_duration()
            break_secs += brk.duration_seconds or 0
        self.total_work_seconds = work_secs
        self.total_break_seconds = break_secs
        if self.status == AttendanceDayStatus.ABSENT:
            return
        if work_secs > 0 and self.status == AttendanceDayStatus.ABSENT:
            self.status = AttendanceDayStatus.PRESENT
        elif work_secs > 0 and self.status not in (AttendanceDayStatus.HOLIDAY, AttendanceDayStatus.ABSENT):
            self.status = AttendanceDayStatus.PRESENT

    def to_dict(self, include_periods: bool = False):
        status = self.status.value if isinstance(self.status, AttendanceDayStatus) else str(self.status)
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "work_date": self.work_date.isoformat() if self.work_date else None,
            "status": status,
            "time_off_request_id": self.time_off_request_id,
            "leave_type_id": self.leave_type_id,
            "leave_type_name": self.leave_type.name if self.leave_type else None,
            "total_work_seconds": self.total_work_seconds,
            "total_break_seconds": self.total_break_seconds,
            "total_work_hours": round((self.total_work_seconds or 0) / 3600, 2),
            "total_break_hours": round((self.total_break_seconds or 0) / 3600, 2),
            "locked_at": self.locked_at.isoformat() if self.locked_at else None,
            "locked_by": self.locked_by,
            "is_locked": self.is_locked,
            "timesheet_period_id": self.timesheet_period_id,
            "compliance_notes": self.compliance_notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_periods:
            data["work_periods"] = [
                p.to_dict() for p in self.work_periods.order_by(AttendanceWorkPeriod.start_time.asc())
            ]
            data["breaks"] = [b.to_dict() for b in self.breaks.order_by(AttendanceBreak.start_time.asc())]
        return data


class AttendanceWorkPeriod(db.Model):
    """A contiguous work period within a day (clock-in to clock-out)."""

    __tablename__ = "attendance_work_periods"

    id = db.Column(db.Integer, primary_key=True)
    attendance_day_id = db.Column(db.Integer, db.ForeignKey("daily_attendance_records.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, nullable=True, index=True)
    duration_seconds = db.Column(db.Integer, nullable=True)
    source = db.Column(db.String(20), default="manual", nullable=False)
    auto_closed = db.Column(db.Boolean, default=False, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    workday_session_id = db.Column(db.Integer, db.ForeignKey("workday_sessions.id"), nullable=True, index=True)

    created_at = db.Column(db.DateTime, default=local_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=local_now, onupdate=local_now, nullable=False)

    attendance_day = db.relationship("DailyAttendanceRecord", back_populates="work_periods")
    user = db.relationship("User", backref=db.backref("attendance_work_periods", lazy="dynamic"))
    breaks = db.relationship(
        "AttendanceBreak",
        back_populates="work_period",
        lazy="dynamic",
        foreign_keys="AttendanceBreak.work_period_id",
    )

    @property
    def is_active(self) -> bool:
        return self.end_time is None

    def calculate_duration(self):
        if not self.start_time:
            self.duration_seconds = None
            return
        end = self.end_time or local_now()
        self.duration_seconds = max(0, int((end - self.start_time).total_seconds()))

    def to_dict(self):
        return {
            "id": self.id,
            "attendance_day_id": self.attendance_day_id,
            "user_id": self.user_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "source": self.source,
            "auto_closed": self.auto_closed,
            "notes": self.notes,
            "is_active": self.is_active,
            "workday_session_id": self.workday_session_id,
        }


class AttendanceBreak(db.Model):
    """Break period during a work day."""

    __tablename__ = "attendance_breaks"

    id = db.Column(db.Integer, primary_key=True)
    attendance_day_id = db.Column(db.Integer, db.ForeignKey("daily_attendance_records.id"), nullable=False, index=True)
    work_period_id = db.Column(db.Integer, db.ForeignKey("attendance_work_periods.id"), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, nullable=True, index=True)
    duration_seconds = db.Column(db.Integer, nullable=True)
    break_type = db.Column(
        SQLEnum(AttendanceBreakType, values_callable=lambda x: [e.value for e in x]),
        default=AttendanceBreakType.REST,
        nullable=False,
    )

    created_at = db.Column(db.DateTime, default=local_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=local_now, onupdate=local_now, nullable=False)

    attendance_day = db.relationship("DailyAttendanceRecord", back_populates="breaks")
    work_period = db.relationship("AttendanceWorkPeriod", back_populates="breaks", foreign_keys=[work_period_id])
    user = db.relationship("User", backref=db.backref("attendance_breaks", lazy="dynamic"))

    @property
    def is_active(self) -> bool:
        return self.end_time is None

    def calculate_duration(self):
        if not self.start_time:
            self.duration_seconds = None
            return
        end = self.end_time or local_now()
        self.duration_seconds = max(0, int((end - self.start_time).total_seconds()))

    def to_dict(self):
        break_type = self.break_type.value if isinstance(self.break_type, AttendanceBreakType) else str(self.break_type)
        return {
            "id": self.id,
            "attendance_day_id": self.attendance_day_id,
            "work_period_id": self.work_period_id,
            "user_id": self.user_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "break_type": break_type,
            "is_active": self.is_active,
        }


class AttendanceCorrection(db.Model):
    """Reason-required correction request for attendance records."""

    __tablename__ = "attendance_corrections"

    id = db.Column(db.Integer, primary_key=True)
    attendance_day_id = db.Column(db.Integer, db.ForeignKey("daily_attendance_records.id"), nullable=False, index=True)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.Integer, nullable=False)

    original_values = db.Column(db.JSON, nullable=True)
    corrected_values = db.Column(db.JSON, nullable=False)
    reason = db.Column(db.Text, nullable=False)

    status = db.Column(
        SQLEnum(AttendanceCorrectionStatus, values_callable=lambda x: [e.value for e in x]),
        default=AttendanceCorrectionStatus.PENDING,
        nullable=False,
        index=True,
    )

    requested_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    review_comment = db.Column(db.Text, nullable=True)
    applied_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=local_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=local_now, onupdate=local_now, nullable=False)

    attendance_day = db.relationship("DailyAttendanceRecord", backref=db.backref("corrections", lazy="dynamic"))
    requester = db.relationship("User", foreign_keys=[requested_by])
    reviewer = db.relationship("User", foreign_keys=[reviewed_by])

    def to_dict(self):
        status = self.status.value if isinstance(self.status, AttendanceCorrectionStatus) else str(self.status)
        return {
            "id": self.id,
            "attendance_day_id": self.attendance_day_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "original_values": self.original_values,
            "corrected_values": self.corrected_values,
            "reason": self.reason,
            "status": status,
            "requested_by": self.requested_by,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "review_comment": self.review_comment,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
