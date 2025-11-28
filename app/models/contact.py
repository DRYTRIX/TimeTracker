from datetime import datetime
from app import db
from app.utils.timezone import now_in_app_timezone


def local_now():
    """Get current time in local timezone as naive datetime (for database storage)"""
    return now_in_app_timezone().replace(tzinfo=None)


class Contact(db.Model):
    """Contact model for managing multiple contacts per client"""

    __tablename__ = "contacts"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False, index=True)

    # Contact information
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(200), nullable=True, index=True)
    phone = db.Column(db.String(50), nullable=True)
    mobile = db.Column(db.String(50), nullable=True)

    # Contact details
    title = db.Column(db.String(100), nullable=True)  # Job title
    department = db.Column(db.String(100), nullable=True)
    role = db.Column(db.String(50), nullable=True, default="contact")  # 'primary', 'billing', 'technical', 'contact'
    is_primary = db.Column(db.Boolean, default=False, nullable=False)  # Primary contact for client

    # Additional information
    address = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    tags = db.Column(db.String(500), nullable=True)  # Comma-separated tags

    # Status
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=local_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=local_now, onupdate=local_now, nullable=False)

    # Relationships
    client = db.relationship("Client", backref="contacts")
    creator = db.relationship("User", foreign_keys=[created_by], backref="created_contacts")
    communications = db.relationship(
        "ContactCommunication",
        foreign_keys="ContactCommunication.contact_id",
        backref="contact",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def __init__(self, client_id, first_name, last_name, created_by, **kwargs):
        self.client_id = client_id
        self.first_name = first_name.strip()
        self.last_name = last_name.strip()
        self.created_by = created_by

        # Set optional fields
        self.email = kwargs.get("email", "").strip() if kwargs.get("email") else None
        self.phone = kwargs.get("phone", "").strip() if kwargs.get("phone") else None
        self.mobile = kwargs.get("mobile", "").strip() if kwargs.get("mobile") else None
        self.title = kwargs.get("title", "").strip() if kwargs.get("title") else None
        self.department = kwargs.get("department", "").strip() if kwargs.get("department") else None
        self.role = kwargs.get("role", "contact").strip() if kwargs.get("role") else "contact"
        self.is_primary = kwargs.get("is_primary", False)
        self.address = kwargs.get("address", "").strip() if kwargs.get("address") else None
        self.notes = kwargs.get("notes", "").strip() if kwargs.get("notes") else None
        self.tags = kwargs.get("tags", "").strip() if kwargs.get("tags") else None
        self.is_active = kwargs.get("is_active", True)

    def __repr__(self):
        return f"<Contact {self.first_name} {self.last_name} ({self.client.name})>"

    @property
    def full_name(self):
        """Get full name of contact"""
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def display_name(self):
        """Get display name with title if available"""
        if self.title:
            return f"{self.full_name} - {self.title}"
        return self.full_name

    def to_dict(self):
        """Convert contact to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "client_id": self.client_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "display_name": self.display_name,
            "email": self.email,
            "phone": self.phone,
            "mobile": self.mobile,
            "title": self.title,
            "department": self.department,
            "role": self.role,
            "is_primary": self.is_primary,
            "address": self.address,
            "notes": self.notes,
            "tags": self.tags.split(",") if self.tags else [],
            "is_active": self.is_active,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def get_active_contacts(cls, client_id=None):
        """Get active contacts, optionally filtered by client"""
        query = cls.query.filter_by(is_active=True)
        if client_id:
            query = query.filter_by(client_id=client_id)
        return query.order_by(cls.last_name, cls.first_name).all()

    @classmethod
    def get_primary_contact(cls, client_id):
        """Get primary contact for a client"""
        return cls.query.filter_by(client_id=client_id, is_primary=True, is_active=True).first()

    def set_as_primary(self):
        """Set this contact as primary and unset others for the same client"""
        # Unset other primary contacts for this client
        Contact.query.filter_by(client_id=self.client_id, is_primary=True).update({"is_primary": False})
        self.is_primary = True
        db.session.commit()
