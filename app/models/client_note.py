from datetime import datetime
from app import db
from app.utils.timezone import now_in_app_timezone


class ClientNote(db.Model):
    """ClientNote model for internal notes about clients"""

    __tablename__ = "client_notes"

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)

    # Reference to client
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False, index=True)

    # Author of the note
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    # Internal flag - these notes are always internal and not visible to clients
    is_important = db.Column(db.Boolean, default=False, nullable=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=now_in_app_timezone, nullable=False)
    updated_at = db.Column(db.DateTime, default=now_in_app_timezone, onupdate=now_in_app_timezone, nullable=False)

    # Relationships
    author = db.relationship("User", backref="client_notes")
    client = db.relationship("Client", backref=db.backref("notes", cascade="all, delete-orphan"))

    def __init__(self, content, user_id, client_id, is_important=False):
        """Create a client note.

        Args:
            content: The note text
            user_id: ID of the user creating the note
            client_id: ID of the client
            is_important: Whether this note is marked as important
        """
        if not client_id:
            raise ValueError("Note must be associated with a client")

        if not content or not content.strip():
            raise ValueError("Note content cannot be empty")

        self.content = content.strip()
        self.user_id = user_id
        self.client_id = client_id
        self.is_important = is_important

    def __repr__(self):
        return f'<ClientNote by {self.author.username if self.author else "Unknown"} for Client {self.client_id}>'

    @property
    def author_name(self):
        """Get the author's display name"""
        if self.author:
            return self.author.full_name if self.author.full_name else self.author.username
        return "Unknown"

    @property
    def client_name(self):
        """Get the client name"""
        return self.client.name if self.client else "Unknown"

    def can_edit(self, user):
        """Check if a user can edit this note"""
        return user.id == self.user_id or user.is_admin

    def can_delete(self, user):
        """Check if a user can delete this note"""
        return user.id == self.user_id or user.is_admin

    def edit_content(self, new_content, user, is_important=None):
        """Edit the note content

        Args:
            new_content: New content for the note
            user: User making the edit
            is_important: Optional new importance flag
        """
        if not self.can_edit(user):
            raise PermissionError("User does not have permission to edit this note")

        if not new_content or not new_content.strip():
            raise ValueError("Note content cannot be empty")

        self.content = new_content.strip()
        if is_important is not None:
            self.is_important = is_important
        self.updated_at = now_in_app_timezone()

    def to_dict(self):
        """Convert note to dictionary for API responses"""
        return {
            "id": self.id,
            "content": self.content,
            "client_id": self.client_id,
            "client_name": self.client_name,
            "user_id": self.user_id,
            "author": self.author.username if self.author else None,
            "author_full_name": self.author.full_name if self.author and self.author.full_name else None,
            "author_name": self.author_name,
            "is_important": self.is_important,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def get_client_notes(cls, client_id, order_by_important=False):
        """Get all notes for a client

        Args:
            client_id: ID of the client
            order_by_important: If True, important notes appear first
        """
        query = cls.query.filter_by(client_id=client_id)

        if order_by_important:
            query = query.order_by(cls.is_important.desc(), cls.created_at.desc())
        else:
            query = query.order_by(cls.created_at.desc())

        return query.all()

    @classmethod
    def get_important_notes(cls, client_id=None):
        """Get all important notes, optionally filtered by client"""
        query = cls.query.filter_by(is_important=True)

        if client_id:
            query = query.filter_by(client_id=client_id)

        return query.order_by(cls.created_at.desc()).all()

    @classmethod
    def get_user_notes(cls, user_id, limit=None):
        """Get recent notes by a user"""
        query = cls.query.filter_by(user_id=user_id).order_by(cls.created_at.desc())

        if limit:
            query = query.limit(limit)

        return query.all()

    @classmethod
    def get_recent_notes(cls, limit=10):
        """Get recent notes across all clients"""
        return cls.query.order_by(cls.created_at.desc()).limit(limit).all()
