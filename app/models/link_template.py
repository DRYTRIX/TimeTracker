"""Link Template model for storing URL templates with field placeholders"""

from datetime import datetime
from app import db
from sqlalchemy.exc import ProgrammingError


class LinkTemplate(db.Model):
    """Model for storing URL templates that can use custom field values from clients"""

    __tablename__ = "link_templates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    url_template = db.Column(db.String(1000), nullable=False)  # URL with {value} or %value% placeholder
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
        """Render the URL template with the given field value
        
        Supports both {value} and %value% placeholder formats
        """
        if not field_value:
            return None
        try:
            # First try Python format string with {value}
            if "{value}" in self.url_template:
                return self.url_template.format(value=field_value)
            # Then try %value% placeholder
            elif "%value%" in self.url_template:
                return self.url_template.replace("%value%", str(field_value))
            else:
                # If neither placeholder is found, return None
                return None
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
        """Get active link templates, optionally filtered by field_key.
        
        Returns empty list if table doesn't exist (migration not run yet).
        """
        try:
            query = cls.query.filter_by(is_active=True)
            if field_key:
                query = query.filter_by(field_key=field_key)
            return query.order_by(cls.order, cls.name).all()
        except ProgrammingError as e:
            # Handle case where link_templates table doesn't exist (migration not run)
            if "does not exist" in str(e.orig) or "relation" in str(e.orig).lower():
                try:
                    from flask import current_app
                    if current_app:
                        current_app.logger.warning(
                            "link_templates table does not exist. Run migration: flask db upgrade"
                        )
                except RuntimeError:
                    pass  # No application context
                # Rollback the failed transaction and clear session state
                try:
                    db.session.rollback()
                    db.session.expunge_all()  # Clear all objects from session
                except Exception:
                    pass
                return []
            raise
        except Exception:
            # For other database errors, return empty list to prevent breaking the app
            try:
                from flask import current_app
                if current_app:
                    current_app.logger.warning(
                        "Could not query link_templates. Returning empty list."
                    )
            except RuntimeError:
                pass  # No application context
            # Rollback the failed transaction
            try:
                db.session.rollback()
            except Exception:
                pass
            return []
