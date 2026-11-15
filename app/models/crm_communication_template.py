"""Reusable templates for CRM contact communications."""

from app import db
from app.utils.timezone import now_in_app_timezone


def local_now():
    return now_in_app_timezone().replace(tzinfo=None)


class CrmCommunicationTemplate(db.Model):
    """Saved subject/body templates for logging contact communications."""

    __tablename__ = "crm_communication_templates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    type = db.Column(db.String(50), nullable=False, default="email")  # email, call, meeting, note, message
    subject = db.Column(db.String(500), nullable=True)
    content = db.Column(db.Text, nullable=True)
    direction = db.Column(db.String(20), nullable=False, default="outbound")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=local_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=local_now, onupdate=local_now, nullable=False)

    creator = db.relationship("User", foreign_keys=[created_by], backref="crm_communication_templates")

    def __init__(self, name, created_by, **kwargs):
        self.name = name.strip()
        self.created_by = created_by
        self.type = (kwargs.get("type") or "email").strip()
        self.subject = (kwargs.get("subject") or "").strip() or None
        self.content = (kwargs.get("content") or "").strip() or None
        self.direction = (kwargs.get("direction") or "outbound").strip()
        self.is_active = kwargs.get("is_active", True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "subject": self.subject,
            "content": self.content,
            "direction": self.direction,
            "is_active": self.is_active,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
