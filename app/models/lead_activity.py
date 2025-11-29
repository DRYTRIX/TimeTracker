from datetime import datetime
from app import db
from app.utils.timezone import now_in_app_timezone


def local_now():
    """Get current time in local timezone as naive datetime (for database storage)"""
    return now_in_app_timezone().replace(tzinfo=None)


class LeadActivity(db.Model):
    """Model for tracking activities on leads"""

    __tablename__ = "lead_activities"

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey("leads.id"), nullable=False, index=True)

    # Activity details
    type = db.Column(
        db.String(50), nullable=False
    )  # 'call', 'email', 'meeting', 'note', 'status_change', 'score_change'
    subject = db.Column(db.String(500), nullable=True)
    description = db.Column(db.Text, nullable=True)

    # Activity date
    activity_date = db.Column(db.DateTime, nullable=False, default=local_now, index=True)
    due_date = db.Column(db.DateTime, nullable=True)  # For scheduled activities

    # Status
    status = db.Column(db.String(50), nullable=True, default="completed")  # 'completed', 'pending', 'cancelled'

    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=local_now, nullable=False)

    # Relationships
    # Note: 'lead' backref is created by Lead.activities relationship
    creator = db.relationship("User", foreign_keys=[created_by], backref="created_lead_activities")

    def __init__(self, lead_id, type, created_by, **kwargs):
        self.lead_id = lead_id
        self.type = type.strip()
        self.created_by = created_by

        # Set optional fields
        self.subject = kwargs.get("subject", "").strip() if kwargs.get("subject") else None
        self.description = kwargs.get("description", "").strip() if kwargs.get("description") else None
        self.activity_date = kwargs.get("activity_date") or local_now()
        self.due_date = kwargs.get("due_date")
        self.status = kwargs.get("status", "completed").strip() if kwargs.get("status") else "completed"

    def __repr__(self):
        return f"<LeadActivity {self.type} for Lead {self.lead_id}>"

    def to_dict(self):
        """Convert activity to dictionary"""
        return {
            "id": self.id,
            "lead_id": self.lead_id,
            "type": self.type,
            "subject": self.subject,
            "description": self.description,
            "activity_date": self.activity_date.isoformat() if self.activity_date else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "status": self.status,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
