from datetime import datetime

from app import db
from app.models.time_entry import local_now


class WorkingTimeViolation(db.Model):
    """Record when a user exceeds daily or weekly working time limits."""

    __tablename__ = "working_time_violations"
    __table_args__ = (
        db.UniqueConstraint("user_id", "period_type", "period_start", name="uq_working_time_violation_period"),
    )

    STATUS_PENDING = "pending"
    STATUS_SUBMITTED = "submitted"
    STATUS_ACKNOWLEDGED = "acknowledged"

    PERIOD_DAILY = "daily"
    PERIOD_WEEKLY = "weekly"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    period_type = db.Column(db.String(10), nullable=False)  # daily | weekly
    period_start = db.Column(db.Date, nullable=False, index=True)
    period_end = db.Column(db.Date, nullable=False)
    limit_hours = db.Column(db.Float, nullable=False)
    actual_hours = db.Column(db.Float, nullable=False)
    hours_over = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default=STATUS_PENDING, nullable=False)
    justification = db.Column(db.Text, nullable=True)
    justification_submitted_at = db.Column(db.DateTime, nullable=True)
    acknowledged_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    acknowledged_at = db.Column(db.DateTime, nullable=True)
    notified_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=local_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=local_now, onupdate=local_now, nullable=False)

    user = db.relationship("User", foreign_keys=[user_id], backref=db.backref("working_time_violations", lazy="dynamic"))
    acknowledged_by = db.relationship("User", foreign_keys=[acknowledged_by_user_id])

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "period_type": self.period_type,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "limit_hours": self.limit_hours,
            "actual_hours": self.actual_hours,
            "hours_over": self.hours_over,
            "status": self.status,
            "justification": self.justification,
            "justification_submitted_at": (
                self.justification_submitted_at.isoformat() if self.justification_submitted_at else None
            ),
            "acknowledged_by_user_id": self.acknowledged_by_user_id,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "notified_at": self.notified_at.isoformat() if self.notified_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
