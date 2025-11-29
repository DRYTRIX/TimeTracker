"""
Team Chat models for real-time messaging
"""

from datetime import datetime
from app import db
from sqlalchemy import Index


class ChatChannel(db.Model):
    """Chat channel/room for team communication"""

    __tablename__ = "chat_channels"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    channel_type = db.Column(db.String(20), default="public", nullable=False)  # 'public', 'private', 'direct'

    # Channel settings
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id"), nullable=True, index=True
    )  # Project-specific channel

    # Metadata
    is_archived = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    creator = db.relationship("User", foreign_keys=[created_by])
    project = db.relationship("Project", backref=db.backref("chat_channels", lazy="dynamic"))
    messages = db.relationship("ChatMessage", backref="channel", lazy="dynamic", cascade="all, delete-orphan")
    members = db.relationship("ChatChannelMember", backref="channel", lazy="dynamic", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_chat_channels_type", "channel_type"),)

    def __repr__(self):
        return f"<ChatChannel {self.name} ({self.channel_type})>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "channel_type": self.channel_type,
            "created_by": self.created_by,
            "project_id": self.project_id,
            "is_archived": self.is_archived,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "message_count": self.messages.count(),
            "member_count": self.members.count(),
        }


class ChatChannelMember(db.Model):
    """Channel membership for users"""

    __tablename__ = "chat_channel_members"

    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.Integer, db.ForeignKey("chat_channels.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    # Permissions
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    # Notification settings
    notifications_enabled = db.Column(db.Boolean, default=True, nullable=False)
    muted_until = db.Column(db.DateTime, nullable=True)  # Mute until this time

    # Metadata
    joined_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_read_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    user = db.relationship("User", backref=db.backref("chat_channel_memberships", lazy="dynamic"))

    __table_args__ = (
        db.UniqueConstraint("channel_id", "user_id", name="uq_channel_member"),
        Index("ix_chat_channel_members_channel_user", "channel_id", "user_id"),
    )

    def __repr__(self):
        return f"<ChatChannelMember channel={self.channel_id} user={self.user_id}>"


class ChatMessage(db.Model):
    """Individual chat message"""

    __tablename__ = "chat_messages"

    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.Integer, db.ForeignKey("chat_channels.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    # Message content
    message = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), default="text", nullable=False)  # 'text', 'file', 'system'

    # File attachment
    attachment_url = db.Column(db.String(500), nullable=True)
    attachment_filename = db.Column(db.String(255), nullable=True)
    attachment_size = db.Column(db.Integer, nullable=True)

    # Reply/thread
    reply_to_id = db.Column(db.Integer, db.ForeignKey("chat_messages.id"), nullable=True)

    # Mentions
    mentions = db.Column(db.JSON, nullable=True)  # List of mentioned user IDs

    # Reactions
    reactions = db.Column(db.JSON, nullable=True)  # {emoji: [user_ids]}

    # Status
    is_edited = db.Column(db.Boolean, default=False, nullable=False)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    edited_at = db.Column(db.DateTime, nullable=True)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = db.relationship("User", backref=db.backref("chat_messages", lazy="dynamic"))
    reply_to = db.relationship("ChatMessage", remote_side=[id], backref=db.backref("replies", lazy="dynamic"))

    __table_args__ = (Index("ix_chat_messages_channel_created", "channel_id", "created_at"),)

    def __repr__(self):
        return f"<ChatMessage {self.id} in channel {self.channel_id}>"

    def to_dict(self):
        return {
            "id": self.id,
            "channel_id": self.channel_id,
            "user_id": self.user_id,
            "username": self.user.username if self.user else None,
            "display_name": self.user.display_name if self.user else None,
            "message": self.message,
            "message_type": self.message_type,
            "attachment_url": self.attachment_url,
            "attachment_filename": self.attachment_filename,
            "reply_to_id": self.reply_to_id,
            "mentions": self.mentions or [],
            "reactions": self.reactions or {},
            "is_edited": self.is_edited,
            "is_deleted": self.is_deleted,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "edited_at": self.edited_at.isoformat() if self.edited_at else None,
        }

    def parse_mentions(self):
        """Parse @mentions from message and extract user IDs"""
        import re

        mentions = []
        pattern = r"@(\w+)"
        matches = re.findall(pattern, self.message)

        from app.models import User

        for username in matches:
            user = User.query.filter_by(username=username).first()
            if user:
                mentions.append(user.id)

        self.mentions = mentions if mentions else None
        return mentions


class ChatReadReceipt(db.Model):
    """Track read receipts for messages"""

    __tablename__ = "chat_read_receipts"

    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey("chat_messages.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    read_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    message = db.relationship("ChatMessage", backref=db.backref("read_receipts", lazy="dynamic"))
    user = db.relationship("User", backref=db.backref("chat_read_receipts", lazy="dynamic"))

    __table_args__ = (db.UniqueConstraint("message_id", "user_id", name="uq_read_receipt"),)

    def __repr__(self):
        return f"<ChatReadReceipt message={self.message_id} user={self.user_id}>"
