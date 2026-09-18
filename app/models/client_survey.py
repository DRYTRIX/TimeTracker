"""Client satisfaction / NPS survey models."""

import secrets
from datetime import datetime, timedelta

from app import db


class ClientSurvey(db.Model):
    """Token-based NPS / satisfaction survey sent to clients."""

    __tablename__ = "client_surveys"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True, index=True)

    trigger = db.Column(db.String(40), nullable=False, index=True)  # project_close | invoice_paid
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)

    nps_score = db.Column(db.Integer, nullable=True)  # 0–10
    comment = db.Column(db.Text, nullable=True)

    sent_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    responded_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    client = db.relationship("Client", backref=db.backref("surveys", lazy="dynamic"))
    project = db.relationship("Project", backref=db.backref("surveys", lazy="dynamic"))
    invoice = db.relationship("Invoice", backref=db.backref("surveys", lazy="dynamic"))

    def __init__(self, client_id, trigger, project_id=None, invoice_id=None, expires_days=30):
        self.client_id = client_id
        self.trigger = trigger
        self.project_id = project_id
        self.invoice_id = invoice_id
        self.token = secrets.token_urlsafe(32)
        self.sent_at = datetime.utcnow()
        self.expires_at = datetime.utcnow() + timedelta(days=expires_days)

    @property
    def is_expired(self):
        return bool(self.expires_at and self.expires_at < datetime.utcnow())

    @property
    def is_completed(self):
        return self.responded_at is not None

    def submit(self, nps_score, comment=None):
        score = int(nps_score)
        if score < 0 or score > 10:
            raise ValueError("NPS score must be between 0 and 10")
        self.nps_score = score
        self.comment = (comment or "").strip() or None
        self.responded_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def to_dict(self):
        return {
            "id": self.id,
            "client_id": self.client_id,
            "project_id": self.project_id,
            "invoice_id": self.invoice_id,
            "trigger": self.trigger,
            "nps_score": self.nps_score,
            "comment": self.comment,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "responded_at": self.responded_at.isoformat() if self.responded_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_completed": self.is_completed,
        }
