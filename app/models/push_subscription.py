"""
Push Subscription model for storing browser push notification subscriptions.
"""

from datetime import datetime
from app import db
from app.utils.timezone import now_in_app_timezone
import json


class PushSubscription(db.Model):
    """Model for storing browser push notification subscriptions"""

    __tablename__ = "push_subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Push subscription data (JSON format from browser Push API)
    endpoint = db.Column(db.Text, nullable=False)  # Push service endpoint URL
    keys = db.Column(db.JSON, nullable=False)  # p256dh and auth keys
    
    # Metadata
    user_agent = db.Column(db.String(500), nullable=True)  # Browser user agent
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_used_at = db.Column(db.DateTime, nullable=True)  # Last time subscription was used
    
    # Relationships
    user = db.relationship("User", backref="push_subscriptions", lazy="joined")

    def __init__(self, user_id, endpoint, keys, user_agent=None):
        """Create a push subscription"""
        self.user_id = user_id
        self.endpoint = endpoint
        self.keys = keys if isinstance(keys, dict) else json.loads(keys) if isinstance(keys, str) else {}
        self.user_agent = user_agent

    def __repr__(self):
        return f"<PushSubscription {self.id} for user {self.user_id}>"

    def to_dict(self):
        """Convert subscription to dictionary for API responses"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "endpoint": self.endpoint,
            "keys": self.keys,
            "user_agent": self.user_agent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }

    def update_last_used(self):
        """Update the last_used_at timestamp"""
        self.last_used_at = now_in_app_timezone()
        self.updated_at = now_in_app_timezone()
        db.session.commit()

    @classmethod
    def get_user_subscriptions(cls, user_id):
        """Get all active subscriptions for a user"""
        return cls.query.filter_by(user_id=user_id).order_by(cls.created_at.desc()).all()

    @classmethod
    def find_by_endpoint(cls, user_id, endpoint):
        """Find a subscription by user and endpoint"""
        return cls.query.filter_by(user_id=user_id, endpoint=endpoint).first()

