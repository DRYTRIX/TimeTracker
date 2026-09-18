"""Email thread models for Gmail / Outlook CRM sync."""

from datetime import datetime

from app import db


class EmailThread(db.Model):
    """A synced email conversation linked to CRM entities."""

    __tablename__ = "email_threads"

    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(40), nullable=False)  # gmail | outlook
    external_thread_id = db.Column(db.String(255), nullable=False, index=True)
    subject = db.Column(db.String(500), nullable=True)
    snippet = db.Column(db.Text, nullable=True)
    participants = db.Column(db.JSON, nullable=True)  # list of email addresses

    client_id = db.Column(db.Integer, db.ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True)
    lead_id = db.Column(db.Integer, db.ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True)
    deal_id = db.Column(db.Integer, db.ForeignKey("deals.id", ondelete="SET NULL"), nullable=True, index=True)

    last_message_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    messages = db.relationship("EmailMessage", backref="thread", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "provider": self.provider,
            "external_thread_id": self.external_thread_id,
            "subject": self.subject,
            "snippet": self.snippet,
            "participants": self.participants or [],
            "client_id": self.client_id,
            "lead_id": self.lead_id,
            "deal_id": self.deal_id,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
            "message_count": self.messages.count(),
        }


class EmailMessage(db.Model):
    """Individual email within a synced thread."""

    __tablename__ = "email_messages"

    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey("email_threads.id", ondelete="CASCADE"), nullable=False, index=True)
    external_message_id = db.Column(db.String(255), nullable=False, index=True)
    from_address = db.Column(db.String(320), nullable=True)
    to_addresses = db.Column(db.JSON, nullable=True)
    subject = db.Column(db.String(500), nullable=True)
    body_text = db.Column(db.Text, nullable=True)
    body_html = db.Column(db.Text, nullable=True)
    sent_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "thread_id": self.thread_id,
            "external_message_id": self.external_message_id,
            "from_address": self.from_address,
            "to_addresses": self.to_addresses or [],
            "subject": self.subject,
            "body_text": self.body_text,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
        }
