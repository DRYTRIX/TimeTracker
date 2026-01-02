"""
Client Notification models for client portal notifications
"""

from datetime import datetime
from app import db
from app.utils.timezone import now_in_app_timezone
import enum


class NotificationType(enum.Enum):
    """Client notification types"""
    INVOICE_CREATED = "invoice_created"
    INVOICE_PAID = "invoice_paid"
    INVOICE_OVERDUE = "invoice_overdue"
    PROJECT_MILESTONE = "project_milestone"
    BUDGET_ALERT = "budget_alert"
    TIME_ENTRY_APPROVAL = "time_entry_approval"
    PROJECT_STATUS_CHANGE = "project_status_change"
    QUOTE_AVAILABLE = "quote_available"
    COMMENT_ADDED = "comment_added"
    FILE_UPLOADED = "file_uploaded"
    GENERAL = "general"


class ClientNotification(db.Model):
    """In-app notifications for client portal users"""

    __tablename__ = "client_notifications"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False, index=True)
    
    # Notification details
    type = db.Column(db.String(50), nullable=False, index=True)  # NotificationType enum value
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    
    # Link/action
    link_url = db.Column(db.String(500), nullable=True)  # URL to related resource
    link_text = db.Column(db.String(100), nullable=True)  # Text for the link
    
    # Status
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    read_at = db.Column(db.DateTime, nullable=True)
    
    # Metadata (renamed from 'metadata' to avoid SQLAlchemy reserved word conflict)
    extra_data = db.Column(db.JSON, nullable=True)  # Additional data (invoice_id, project_id, etc.)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=now_in_app_timezone, nullable=False, index=True)
    
    # Relationships
    client = db.relationship("Client", backref=db.backref("notifications", lazy="dynamic", order_by="desc(ClientNotification.created_at)"))

    def __repr__(self):
        return f"<ClientNotification {self.id} for client {self.client_id} - {self.type}>"

    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = True
        self.read_at = now_in_app_timezone()
        db.session.commit()

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "client_id": self.client_id,
            "type": self.type,
            "title": self.title,
            "message": self.message,
            "link_url": self.link_url,
            "link_text": self.link_text,
            "is_read": self.is_read,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "metadata": self.extra_data,  # API compatibility: return as 'metadata'
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def get_unread_count(cls, client_id):
        """Get count of unread notifications for a client"""
        return cls.query.filter_by(client_id=client_id, is_read=False).count()

    @classmethod
    def get_recent_notifications(cls, client_id, limit=20):
        """Get recent notifications for a client"""
        return cls.query.filter_by(client_id=client_id).order_by(cls.created_at.desc()).limit(limit).all()


class ClientNotificationPreferences(db.Model):
    """Notification preferences for clients"""

    __tablename__ = "client_notification_preferences"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False, unique=True, index=True)
    
    # Email preferences
    email_enabled = db.Column(db.Boolean, default=True, nullable=False)
    email_invoice_created = db.Column(db.Boolean, default=True, nullable=False)
    email_invoice_paid = db.Column(db.Boolean, default=True, nullable=False)
    email_invoice_overdue = db.Column(db.Boolean, default=True, nullable=False)
    email_project_milestone = db.Column(db.Boolean, default=True, nullable=False)
    email_budget_alert = db.Column(db.Boolean, default=True, nullable=False)
    email_time_entry_approval = db.Column(db.Boolean, default=True, nullable=False)
    email_project_status_change = db.Column(db.Boolean, default=False, nullable=False)
    email_quote_available = db.Column(db.Boolean, default=True, nullable=False)
    
    # In-app preferences
    in_app_enabled = db.Column(db.Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=now_in_app_timezone, nullable=False)
    updated_at = db.Column(db.DateTime, default=now_in_app_timezone, onupdate=now_in_app_timezone, nullable=False)
    
    # Relationships
    client = db.relationship("Client", backref=db.backref("notification_preferences", uselist=False))

    def __repr__(self):
        return f"<ClientNotificationPreferences client={self.client_id}>"

    def should_send_email(self, notification_type):
        """Check if email should be sent for this notification type"""
        if not self.email_enabled:
            return False
        
        type_map = {
            NotificationType.INVOICE_CREATED: self.email_invoice_created,
            NotificationType.INVOICE_PAID: self.email_invoice_paid,
            NotificationType.INVOICE_OVERDUE: self.email_invoice_overdue,
            NotificationType.PROJECT_MILESTONE: self.email_project_milestone,
            NotificationType.BUDGET_ALERT: self.email_budget_alert,
            NotificationType.TIME_ENTRY_APPROVAL: self.email_time_entry_approval,
            NotificationType.PROJECT_STATUS_CHANGE: self.email_project_status_change,
            NotificationType.QUOTE_AVAILABLE: self.email_quote_available,
        }
        
        return type_map.get(notification_type, True)

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "client_id": self.client_id,
            "email_enabled": self.email_enabled,
            "email_invoice_created": self.email_invoice_created,
            "email_invoice_paid": self.email_invoice_paid,
            "email_invoice_overdue": self.email_invoice_overdue,
            "email_project_milestone": self.email_project_milestone,
            "email_budget_alert": self.email_budget_alert,
            "email_time_entry_approval": self.email_time_entry_approval,
            "email_project_status_change": self.email_project_status_change,
            "email_quote_available": self.email_quote_available,
            "in_app_enabled": self.in_app_enabled,
        }
