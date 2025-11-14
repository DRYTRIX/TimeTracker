"""Webhook models for enabling integrations"""
import secrets
import hashlib
import hmac
import json
from datetime import datetime
from app import db
from app.utils.timezone import now_in_app_timezone


class Webhook(db.Model):
    """Webhook configuration for sending events to external systems"""
    
    __tablename__ = 'webhooks'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Basic information
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Webhook URL and configuration
    url = db.Column(db.String(500), nullable=False)
    secret = db.Column(db.String(128), nullable=True)  # Secret for HMAC signature
    
    # Event subscriptions (JSON array of event types)
    # Examples: ['project.created', 'time_entry.started', 'invoice.paid']
    events = db.Column(db.JSON, nullable=False, default=list)
    
    # HTTP configuration
    http_method = db.Column(db.String(10), default='POST', nullable=False)  # POST, PUT, PATCH
    content_type = db.Column(db.String(50), default='application/json', nullable=False)
    headers = db.Column(db.JSON, nullable=True)  # Custom headers as JSON object
    
    # Status and ownership
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    user = db.relationship('User', backref='webhooks')
    
    # Retry configuration
    max_retries = db.Column(db.Integer, default=3, nullable=False)
    retry_delay_seconds = db.Column(db.Integer, default=60, nullable=False)  # Delay between retries
    
    # Timeout configuration
    timeout_seconds = db.Column(db.Integer, default=30, nullable=False)
    
    # Statistics
    total_deliveries = db.Column(db.Integer, default=0, nullable=False)
    successful_deliveries = db.Column(db.Integer, default=0, nullable=False)
    failed_deliveries = db.Column(db.Integer, default=0, nullable=False)
    last_delivery_at = db.Column(db.DateTime, nullable=True)
    last_success_at = db.Column(db.DateTime, nullable=True)
    last_failure_at = db.Column(db.DateTime, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=now_in_app_timezone, nullable=False)
    updated_at = db.Column(db.DateTime, default=now_in_app_timezone, onupdate=now_in_app_timezone, nullable=False)
    
    # Indexes
    __table_args__ = (
        db.Index('ix_webhooks_user_id', 'user_id'),
        db.Index('ix_webhooks_is_active', 'is_active'),
        db.Index('ix_webhooks_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f'<Webhook {self.name} ({self.url})>'
    
    @staticmethod
    def generate_secret():
        """Generate a secure random secret for webhook signing"""
        return secrets.token_urlsafe(32)
    
    def set_secret(self, secret=None):
        """Set or generate a webhook secret"""
        if secret is None:
            secret = self.generate_secret()
        self.secret = secret
    
    def verify_signature(self, payload, signature):
        """Verify HMAC signature of webhook payload
        
        Args:
            payload: The webhook payload (string or bytes)
            signature: The signature header value
            
        Returns:
            bool: True if signature is valid
        """
        if not self.secret:
            return False
        
        if isinstance(payload, str):
            payload = payload.encode('utf-8')
        
        expected_signature = hmac.new(
            self.secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Support both 'sha256=...' and plain hex formats
        if signature.startswith('sha256='):
            signature = signature[7:]
        
        return hmac.compare_digest(expected_signature, signature)
    
    def generate_signature(self, payload):
        """Generate HMAC signature for webhook payload
        
        Args:
            payload: The webhook payload (string or bytes)
            
        Returns:
            str: HMAC signature in format 'sha256=...'
        """
        if not self.secret:
            return None
        
        if isinstance(payload, str):
            payload = payload.encode('utf-8')
        
        signature = hmac.new(
            self.secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return f'sha256={signature}'
    
    def subscribes_to(self, event_type):
        """Check if webhook subscribes to a specific event type
        
        Args:
            event_type: Event type string (e.g., 'project.created')
            
        Returns:
            bool: True if webhook subscribes to this event
        """
        if not self.events:
            return False
        return event_type in self.events or '*' in self.events
    
    def to_dict(self, include_secret=False):
        """Convert to dictionary for API responses"""
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'url': self.url,
            'events': self.events or [],
            'http_method': self.http_method,
            'content_type': self.content_type,
            'headers': self.headers or {},
            'is_active': self.is_active,
            'user_id': self.user_id,
            'max_retries': self.max_retries,
            'retry_delay_seconds': self.retry_delay_seconds,
            'timeout_seconds': self.timeout_seconds,
            'total_deliveries': self.total_deliveries,
            'successful_deliveries': self.successful_deliveries,
            'failed_deliveries': self.failed_deliveries,
            'last_delivery_at': self.last_delivery_at.isoformat() if self.last_delivery_at else None,
            'last_success_at': self.last_success_at.isoformat() if self.last_success_at else None,
            'last_failure_at': self.last_failure_at.isoformat() if self.last_failure_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_secret:
            data['secret'] = self.secret
        
        return data


class WebhookDelivery(db.Model):
    """Track individual webhook delivery attempts"""
    
    __tablename__ = 'webhook_deliveries'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Webhook reference
    webhook_id = db.Column(db.Integer, db.ForeignKey('webhooks.id', ondelete='CASCADE'), nullable=False, index=True)
    webhook = db.relationship('Webhook', backref='deliveries')
    
    # Event information
    event_type = db.Column(db.String(100), nullable=False, index=True)
    event_id = db.Column(db.String(100), nullable=True)  # Unique ID for this event instance
    
    # Payload
    payload = db.Column(db.Text, nullable=False)  # JSON-encoded payload
    payload_hash = db.Column(db.String(64), nullable=True)  # SHA256 hash for deduplication
    
    # Delivery status
    status = db.Column(db.String(20), nullable=False, default='pending', index=True)  # pending, success, failed, retrying
    attempt_number = db.Column(db.Integer, default=1, nullable=False)
    
    # HTTP response
    response_status_code = db.Column(db.Integer, nullable=True)
    response_body = db.Column(db.Text, nullable=True)
    response_headers = db.Column(db.JSON, nullable=True)
    
    # Error information
    error_message = db.Column(db.Text, nullable=True)
    error_type = db.Column(db.String(100), nullable=True)  # timeout, connection_error, http_error, etc.
    
    # Timing
    started_at = db.Column(db.DateTime, default=now_in_app_timezone, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    duration_ms = db.Column(db.Integer, nullable=True)  # Duration in milliseconds
    
    # Retry information
    next_retry_at = db.Column(db.DateTime, nullable=True, index=True)
    retry_count = db.Column(db.Integer, default=0, nullable=False)
    
    # Indexes
    __table_args__ = (
        db.Index('ix_webhook_deliveries_webhook_id', 'webhook_id'),
        db.Index('ix_webhook_deliveries_status', 'status'),
        db.Index('ix_webhook_deliveries_event_type', 'event_type'),
        db.Index('ix_webhook_deliveries_next_retry_at', 'next_retry_at'),
        db.Index('ix_webhook_deliveries_started_at', 'started_at'),
    )
    
    def __repr__(self):
        return f'<WebhookDelivery {self.webhook_id} {self.event_type} {self.status}>'
    
    @staticmethod
    def hash_payload(payload):
        """Generate hash of payload for deduplication"""
        if isinstance(payload, str):
            payload = payload.encode('utf-8')
        return hashlib.sha256(payload).hexdigest()
    
    def mark_success(self, status_code, response_body=None, response_headers=None, duration_ms=None):
        """Mark delivery as successful"""
        self.status = 'success'
        self.response_status_code = status_code
        self.response_body = response_body
        self.response_headers = response_headers
        self.completed_at = now_in_app_timezone()
        if duration_ms is not None:
            self.duration_ms = duration_ms
        
        # Update webhook statistics
        if self.webhook:
            self.webhook.total_deliveries += 1
            self.webhook.successful_deliveries += 1
            self.webhook.last_delivery_at = self.completed_at
            self.webhook.last_success_at = self.completed_at
    
    def mark_failed(self, error_message, error_type=None, response_status_code=None, response_body=None, duration_ms=None):
        """Mark delivery as failed"""
        self.status = 'failed'
        self.error_message = error_message
        self.error_type = error_type
        self.response_status_code = response_status_code
        self.response_body = response_body
        self.completed_at = now_in_app_timezone()
        if duration_ms is not None:
            self.duration_ms = duration_ms
        
        # Update webhook statistics
        if self.webhook:
            self.webhook.total_deliveries += 1
            self.webhook.failed_deliveries += 1
            self.webhook.last_delivery_at = self.completed_at
            self.webhook.last_failure_at = self.completed_at
    
    def mark_retrying(self, next_retry_at):
        """Mark delivery as retrying and schedule next attempt"""
        self.status = 'retrying'
        self.next_retry_at = next_retry_at
        self.retry_count += 1
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'webhook_id': self.webhook_id,
            'event_type': self.event_type,
            'event_id': self.event_id,
            'status': self.status,
            'attempt_number': self.attempt_number,
            'response_status_code': self.response_status_code,
            'error_message': self.error_message,
            'error_type': self.error_type,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration_ms': self.duration_ms,
            'retry_count': self.retry_count,
            'next_retry_at': self.next_retry_at.isoformat() if self.next_retry_at else None,
        }

