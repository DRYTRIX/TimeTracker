from datetime import datetime, date
import enum

from sqlalchemy import Enum as SQLEnum, UniqueConstraint, Index

from app import db


class TimesheetPeriodStatus(enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    CLOSED = "closed"


class TimesheetPeriod(db.Model):
    """Period-level workflow for submit/approve/close and locking."""

    __tablename__ = "timesheet_periods"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    period_type = db.Column(db.String(20), nullable=False, default="weekly")
    period_start = db.Column(db.Date, nullable=False, index=True)
    period_end = db.Column(db.Date, nullable=False, index=True)

    status = db.Column(
        SQLEnum(TimesheetPeriodStatus, values_callable=lambda x: [e.value for e in x]),
        default=TimesheetPeriodStatus.DRAFT,
        nullable=False,
        index=True,
    )

    submitted_at = db.Column(db.DateTime, nullable=True)
    submitted_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)

    approved_at = db.Column(db.DateTime, nullable=True)
    approved_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)

    rejected_at = db.Column(db.DateTime, nullable=True)
    rejected_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    rejection_reason = db.Column(db.Text, nullable=True)

    closed_at = db.Column(db.DateTime, nullable=True)
    closed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    close_reason = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = db.relationship("User", foreign_keys=[user_id], backref=db.backref("timesheet_periods", lazy="dynamic"))
    submitter = db.relationship("User", foreign_keys=[submitted_by])
    approver = db.relationship("User", foreign_keys=[approved_by])
    rejector = db.relationship("User", foreign_keys=[rejected_by])
    closer = db.relationship("User", foreign_keys=[closed_by])

    __table_args__ = (
        UniqueConstraint("user_id", "period_type", "period_start", "period_end", name="uq_timesheet_period_user_range"),
        Index("ix_timesheet_period_user_status", "user_id", "status"),
    )

    @property
    def is_locked(self) -> bool:
        raw = self.status
        if isinstance(raw, TimesheetPeriodStatus):
            return raw == TimesheetPeriodStatus.CLOSED
        return str(raw).lower() == TimesheetPeriodStatus.CLOSED.value

    def contains_date(self, value: date) -> bool:
        return bool(value and self.period_start <= value <= self.period_end)

    def to_dict(self):
        status = self.status.value if isinstance(self.status, TimesheetPeriodStatus) else str(self.status)
        return {
            "id": self.id,
            "user_id": self.user_id,
            "period_type": self.period_type,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "status": status,
            "is_locked": self.is_locked,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "submitted_by": self.submitted_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "approved_by": self.approved_by,
            "rejected_at": self.rejected_at.isoformat() if self.rejected_at else None,
            "rejected_by": self.rejected_by,
            "rejection_reason": self.rejection_reason,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "closed_by": self.closed_by,
            "close_reason": self.close_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
