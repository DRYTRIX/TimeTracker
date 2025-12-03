from datetime import datetime
from app import db


class SavedReportView(db.Model):
    """Saved configurations for the custom report builder."""

    __tablename__ = "saved_report_views"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    scope = db.Column(db.String(20), default="private", nullable=False)  # private, team, public
    config_json = db.Column(db.Text, nullable=False)  # JSON for filters, columns, groupings
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<SavedReportView {self.name} ({self.scope})>"


class ReportEmailSchedule(db.Model):
    """Schedules to email saved reports on a cadence."""

    __tablename__ = "report_email_schedules"

    id = db.Column(db.Integer, primary_key=True)
    saved_view_id = db.Column(db.Integer, db.ForeignKey("saved_report_views.id"), nullable=False, index=True)
    recipients = db.Column(db.Text, nullable=False)  # comma-separated
    cadence = db.Column(db.String(20), nullable=False)  # daily, weekly, monthly, custom-cron
    cron = db.Column(db.String(120), nullable=True)
    timezone = db.Column(db.String(50), nullable=True)
    next_run_at = db.Column(db.DateTime, nullable=True)
    last_run_at = db.Column(db.DateTime, nullable=True)
    active = db.Column(db.Boolean, default=True, nullable=False)
    split_by_salesman = db.Column(db.Boolean, default=False, nullable=False)  # Split report by salesman
    salesman_field_name = db.Column(db.String(50), nullable=True)  # Custom field name for salesman (default: 'salesman')
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    saved_view = db.relationship("SavedReportView", backref="schedules")
    creator = db.relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<ReportEmailSchedule view={self.saved_view_id} cadence={self.cadence}>"
