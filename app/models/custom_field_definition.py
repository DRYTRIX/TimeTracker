"""Custom Field Definition model for global custom field management"""

from datetime import datetime
from app import db


class CustomFieldDefinition(db.Model):
    """Model for storing global custom field definitions that can be used across all clients"""

    __tablename__ = "custom_field_definitions"

    id = db.Column(db.Integer, primary_key=True)
    field_key = db.Column(db.String(100), unique=True, nullable=False, index=True)  # Unique key (e.g., 'debtor_number')
    label = db.Column(db.String(200), nullable=False)  # Display label (e.g., 'Debtor Number')
    description = db.Column(db.Text, nullable=True)  # Help text for the field
    is_mandatory = db.Column(db.Boolean, default=False, nullable=False)  # Whether field is required
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)  # Whether field is active
    order = db.Column(db.Integer, default=0, nullable=False)  # Display order
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    creator = db.relationship("User", backref="custom_field_definitions", foreign_keys=[created_by])

    def __repr__(self):
        return f"<CustomFieldDefinition {self.field_key}>"

    def to_dict(self):
        """Convert custom field definition to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "field_key": self.field_key,
            "label": self.label,
            "description": self.description,
            "is_mandatory": self.is_mandatory,
            "is_active": self.is_active,
            "order": self.order,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def get_active_definitions(cls):
        """Get all active custom field definitions ordered by order and label"""
        return cls.query.filter_by(is_active=True).order_by(cls.order, cls.label).all()

    @classmethod
    def get_mandatory_definitions(cls):
        """Get all active mandatory custom field definitions"""
        return cls.query.filter_by(is_active=True, is_mandatory=True).order_by(cls.order, cls.label).all()

    @classmethod
    def get_by_key(cls, field_key):
        """Get a custom field definition by its key"""
        return cls.query.filter_by(field_key=field_key, is_active=True).first()

    def count_clients_with_value(self):
        """Count how many clients have a value for this custom field"""
        from app.models import Client
        from sqlalchemy import func
        
        # Query clients that have this field key in their custom_fields JSON
        # This works for both SQLite and PostgreSQL
        count = 0
        for client in Client.query.all():
            if client.custom_fields and self.field_key in client.custom_fields:
                value = client.custom_fields.get(self.field_key)
                # Count only if value is not empty
                if value and str(value).strip():
                    count += 1
        return count