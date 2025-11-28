"""
Integration models for third-party service connections.
"""

from datetime import datetime
from app import db
from sqlalchemy import JSON


class Integration(db.Model):
    """Integration model for third-party service connections."""

    __tablename__ = "integrations"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # e.g., 'Jira', 'Slack', 'GitHub'
    provider = db.Column(db.String(50), nullable=False, index=True)  # e.g., 'jira', 'slack', 'github'
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=False, nullable=False)  # Only True when credentials are set up
    config = db.Column(JSON, nullable=True)  # Provider-specific configuration
    last_sync_at = db.Column(db.DateTime, nullable=True)
    last_sync_status = db.Column(db.String(20), nullable=True)  # 'success', 'error', 'pending'
    last_error = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = db.relationship("User", backref="integrations")

    def __repr__(self):
        return f"<Integration {self.provider} for User {self.user_id}>"


class IntegrationCredential(db.Model):
    """Stores OAuth tokens and credentials for integrations."""

    __tablename__ = "integration_credentials"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    integration_id = db.Column(
        db.Integer, db.ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    access_token = db.Column(db.Text, nullable=True)  # Encrypted in production
    refresh_token = db.Column(db.Text, nullable=True)  # Encrypted in production
    token_type = db.Column(db.String(20), default="Bearer", nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)
    scope = db.Column(db.String(500), nullable=True)  # OAuth scopes
    extra_data = db.Column(JSON, nullable=True)  # Additional provider-specific data
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    integration = db.relationship("Integration", backref=db.backref("credentials", cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<IntegrationCredential for Integration {self.integration_id}>"

    @property
    def is_expired(self):
        """Check if the access token is expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() >= self.expires_at

    def needs_refresh(self):
        """Check if token needs refresh (within 5 minutes of expiry)."""
        if not self.expires_at or not self.refresh_token:
            return False
        from datetime import timedelta

        return datetime.utcnow() >= (self.expires_at - timedelta(minutes=5))


class IntegrationEvent(db.Model):
    """Tracks integration events and sync history."""

    __tablename__ = "integration_events"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    integration_id = db.Column(
        db.Integer, db.ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type = db.Column(db.String(50), nullable=False)  # 'sync', 'webhook', 'error', etc.
    status = db.Column(db.String(20), nullable=False)  # 'success', 'error', 'pending'
    message = db.Column(db.Text, nullable=True)
    event_metadata = db.Column(
        JSON, nullable=True
    )  # Event-specific data (renamed from 'metadata' to avoid SQLAlchemy conflict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    integration = db.relationship("Integration", backref="events")

    def __repr__(self):
        return f"<IntegrationEvent {self.event_type} for Integration {self.integration_id}>"
