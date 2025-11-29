"""Link Template model for storing URL templates with field placeholders"""

from datetime import datetime
from app import db


class LinkTemplate(db.Model):
    """Model for storing URL templates that can use custom field values from clients"""

    __tablename__ = "link_templates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    url_template = db.Column(db.String(1000), nullable=False)  # URL with {value} placeholder
    icon = db.Column(db.String(50), nullable=True)  # Font Awesome icon class (e.g., 'fas fa-link')
    field_key = db.Column(db.String(100), nullable=False)  # Key in custom_fields to use (e.g., 'debtor_number')
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    order = db.Column(db.Integer, default=0, nullable=False)  # Display order
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    creator = db.relationship("User", backref="link_templates", foreign_keys=[created_by])

    def __repr__(self):
        return f"<LinkTemplate {self.name}>"

    def render_url(self, field_value):
        """Render the URL template with the given field value"""
        if not field_value:
            return None
        try:
            return self.url_template.format(value=field_value)
        except (KeyError, ValueError):
            return None

    def to_dict(self):
        """Convert link template to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "url_template": self.url_template,
            "icon": self.icon,
            "field_key": self.field_key,
            "is_active": self.is_active,
            "order": self.order,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def get_active_templates(cls, field_key=None):
        """Get active link templates, optionally filtered by field_key"""
        query = cls.query.filter_by(is_active=True)
        if field_key:
            query = query.filter_by(field_key=field_key)
        return query.order_by(cls.order, cls.name).all()

