"""
Push Subscription model for storing browser push and mobile FCM device tokens.
"""

import json
from datetime import datetime

from app import db
from app.utils.timezone import now_in_app_timezone


class PushSubscription(db.Model):
    """Model for storing browser Web Push and mobile FCM subscriptions."""

    __tablename__ = "push_subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Push subscription data (JSON format from browser Push API).
    # For FCM device rows, endpoint is a sentinel ``fcm://<device_token>`` and keys is {}.
    endpoint = db.Column(db.Text, nullable=False)  # Push service endpoint URL
    keys = db.Column(db.JSON, nullable=False)  # p256dh and auth keys

    # Mobile FCM (Issue #722 idle wake-up)
    device_token = db.Column(db.String(512), nullable=True, index=True)
    platform = db.Column(db.String(20), nullable=True)  # 'android', 'ios', 'web'

    # Metadata
    user_agent = db.Column(db.String(500), nullable=True)  # Browser user agent
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_used_at = db.Column(db.DateTime, nullable=True)  # Last time subscription was used

    # Relationships
    user = db.relationship("User", backref="push_subscriptions", lazy="joined")

    def __init__(self, user_id, endpoint, keys, user_agent=None, device_token=None, platform=None):
        """Create a push subscription"""
        self.user_id = user_id
        self.endpoint = endpoint
        self.keys = keys if isinstance(keys, dict) else json.loads(keys) if isinstance(keys, str) else {}
        self.user_agent = user_agent
        self.device_token = device_token
        self.platform = platform

    def __repr__(self):
        return f"<PushSubscription {self.id} for user {self.user_id}>"

    def to_dict(self):
        """Convert subscription to dictionary for API responses"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "endpoint": self.endpoint,
            "keys": self.keys,
            "device_token": self.device_token,
            "platform": self.platform,
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

    @classmethod
    def find_by_device_token(cls, user_id, device_token):
        """Find a mobile FCM subscription by user and device token."""
        if not device_token:
            return None
        return cls.query.filter_by(user_id=user_id, device_token=device_token).first()

    @classmethod
    def upsert_device_token(cls, user_id, device_token, platform, user_agent=None):
        """Create or update an FCM device-token subscription for a user."""
        platform_norm = (platform or "").strip().lower() or None
        if platform_norm not in ("android", "ios"):
            platform_norm = platform_norm if platform_norm else "android"

        existing = cls.find_by_device_token(user_id, device_token)
        if existing:
            existing.platform = platform_norm
            existing.user_agent = user_agent
            existing.updated_at = now_in_app_timezone()
            existing.last_used_at = now_in_app_timezone()
            return existing

        # Sentinel endpoint keeps the non-null unique-ish endpoint column valid for FCM rows.
        endpoint = f"fcm://{device_token}"
        collision = cls.find_by_endpoint(user_id, endpoint)
        if collision:
            collision.device_token = device_token
            collision.platform = platform_norm
            collision.keys = collision.keys or {}
            collision.user_agent = user_agent
            collision.updated_at = now_in_app_timezone()
            collision.last_used_at = now_in_app_timezone()
            return collision

        sub = cls(
            user_id=user_id,
            endpoint=endpoint,
            keys={},
            user_agent=user_agent,
            device_token=device_token,
            platform=platform_norm,
        )
        db.session.add(sub)
        return sub
