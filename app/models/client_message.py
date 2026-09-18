"""Client–team messaging models for the communication hub."""

from datetime import datetime

from sqlalchemy import Index

from app import db


class ClientMessage(db.Model):
    """A message between the internal team and a client portal user."""

    __tablename__ = "client_messages"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)

    # 'team' | 'client'
    sender_type = db.Column(db.String(20), nullable=False)
    # User.id when sender_type=team; Contact.id or Client.id when client
    sender_id = db.Column(db.Integer, nullable=True)
    sender_name = db.Column(db.String(200), nullable=True)

    body = db.Column(db.Text, nullable=False)
    # Optional JSON list of attachment metadata: [{name, url, size}]
    attachments = db.Column(db.JSON, nullable=True)

    read_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    client = db.relationship("Client", backref=db.backref("messages", lazy="dynamic", cascade="all, delete-orphan"))

    __table_args__ = (Index("ix_client_messages_client_created", "client_id", "created_at"),)

    def mark_read(self):
        if self.read_at is None:
            self.read_at = datetime.utcnow()

    def to_dict(self):
        return {
            "id": self.id,
            "client_id": self.client_id,
            "sender_type": self.sender_type,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "body": self.body,
            "attachments": self.attachments or [],
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
