"""Payroll sync log for Gusto / ADP connectors."""

from datetime import datetime

from app import db


class PayrollSyncLog(db.Model):
    """Track payroll batch pushes to external providers."""

    __tablename__ = "payroll_sync_logs"

    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(40), nullable=False)  # gusto | adp
    integration_id = db.Column(db.Integer, db.ForeignKey("integrations.id", ondelete="SET NULL"), nullable=True)
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(40), nullable=False, default="pending")  # pending|success|failed|partial
    employee_count = db.Column(db.Integer, default=0, nullable=False)
    hours_total = db.Column(db.Float, default=0.0, nullable=False)
    external_batch_id = db.Column(db.String(255), nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    payload_summary = db.Column(db.JSON, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "provider": self.provider,
            "integration_id": self.integration_id,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "status": self.status,
            "employee_count": self.employee_count,
            "hours_total": self.hours_total,
            "external_batch_id": self.external_batch_id,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
