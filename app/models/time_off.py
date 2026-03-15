import enum
from datetime import datetime

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Index

from app import db


class TimeOffRequestStatus(enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class LeaveType(db.Model):
    __tablename__ = "leave_types"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(40), nullable=False, unique=True, index=True)
    is_paid = db.Column(db.Boolean, nullable=False, default=True)
    annual_allowance_hours = db.Column(db.Numeric(10, 2), nullable=True)
    accrual_hours_per_month = db.Column(db.Numeric(10, 2), nullable=True)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "is_paid": self.is_paid,
            "annual_allowance_hours": (
                float(self.annual_allowance_hours) if self.annual_allowance_hours is not None else None
            ),
            "accrual_hours_per_month": (
                float(self.accrual_hours_per_month) if self.accrual_hours_per_month is not None else None
            ),
            "enabled": self.enabled,
        }


class TimeOffRequest(db.Model):
    __tablename__ = "time_off_requests"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    leave_type_id = db.Column(db.Integer, db.ForeignKey("leave_types.id"), nullable=False, index=True)

    start_date = db.Column(db.Date, nullable=False, index=True)
    end_date = db.Column(db.Date, nullable=False, index=True)

    start_half_day = db.Column(db.Boolean, nullable=False, default=False)
    end_half_day = db.Column(db.Boolean, nullable=False, default=False)
    requested_hours = db.Column(db.Numeric(10, 2), nullable=True)

    status = db.Column(
        SQLEnum(TimeOffRequestStatus, values_callable=lambda x: [e.value for e in x]),
        default=TimeOffRequestStatus.DRAFT,
        nullable=False,
        index=True,
    )

    requested_comment = db.Column(db.Text, nullable=True)
    review_comment = db.Column(db.Text, nullable=True)

    submitted_at = db.Column(db.DateTime, nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = db.relationship("User", foreign_keys=[user_id], backref=db.backref("time_off_requests", lazy="dynamic"))
    leave_type = db.relationship("LeaveType", backref=db.backref("requests", lazy="dynamic"))
    reviewer = db.relationship("User", foreign_keys=[reviewed_by])

    __table_args__ = (Index("ix_time_off_user_status_dates", "user_id", "status", "start_date", "end_date"),)

    def to_dict(self):
        status = self.status.value if isinstance(self.status, TimeOffRequestStatus) else str(self.status)
        return {
            "id": self.id,
            "user_id": self.user_id,
            "leave_type_id": self.leave_type_id,
            "leave_type": self.leave_type.name if self.leave_type else None,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "start_half_day": self.start_half_day,
            "end_half_day": self.end_half_day,
            "requested_hours": float(self.requested_hours) if self.requested_hours is not None else None,
            "status": status,
            "requested_comment": self.requested_comment,
            "review_comment": self.review_comment,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "reviewed_by": self.reviewed_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class CompanyHoliday(db.Model):
    __tablename__ = "company_holidays"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    start_date = db.Column(db.Date, nullable=False, index=True)
    end_date = db.Column(db.Date, nullable=False, index=True)
    region = db.Column(db.String(50), nullable=True)
    enabled = db.Column(db.Boolean, nullable=False, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "region": self.region,
            "enabled": self.enabled,
        }
