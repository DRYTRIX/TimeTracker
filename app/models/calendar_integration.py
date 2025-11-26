"""Calendar integration models"""
from datetime import datetime
from app import db


class CalendarIntegration(db.Model):
    """User calendar integration configuration"""
    
    __tablename__ = 'calendar_integrations'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Provider
    provider = db.Column(db.String(50), nullable=False, index=True)
    # Provider: 'google', 'outlook', 'ical'
    
    # OAuth tokens (encrypted)
    access_token = db.Column(db.Text, nullable=False)  # Encrypted
    refresh_token = db.Column(db.Text, nullable=True)  # Encrypted
    token_expires_at = db.Column(db.DateTime, nullable=True)
    
    # Calendar ID
    calendar_id = db.Column(db.String(200), nullable=True)
    calendar_name = db.Column(db.String(200), nullable=True)
    
    # Sync settings (JSON)
    # Contains: sync_direction (bidirectional, time_to_calendar, calendar_to_time),
    # sync_frequency, auto_create_events, etc.
    sync_settings = db.Column(db.JSON, nullable=False, default=dict)
    
    # Status
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    last_sync_at = db.Column(db.DateTime, nullable=True)
    last_sync_status = db.Column(db.String(20), nullable=True)
    # Status: 'success', 'error', 'partial'
    last_sync_error = db.Column(db.Text, nullable=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = db.relationship('User', backref='calendar_integrations')
    
    def __repr__(self):
        return f'<CalendarIntegration user_id={self.user_id} provider={self.provider}>'


class CalendarSyncEvent(db.Model):
    """Calendar sync event tracking"""
    
    __tablename__ = 'calendar_sync_events'
    
    id = db.Column(db.Integer, primary_key=True)
    integration_id = db.Column(db.Integer, db.ForeignKey('calendar_integrations.id'), nullable=False, index=True)
    
    # Event type
    event_type = db.Column(db.String(50), nullable=False, index=True)
    # Type: 'time_entry_created', 'time_entry_updated', 'calendar_event_created', etc.
    
    # Related entities
    time_entry_id = db.Column(db.Integer, db.ForeignKey('time_entries.id'), nullable=True, index=True)
    calendar_event_id = db.Column(db.String(200), nullable=True, index=True)
    # External calendar event ID
    
    # Sync direction
    direction = db.Column(db.String(20), nullable=False)
    # Direction: 'to_calendar', 'from_calendar'
    
    # Status
    status = db.Column(db.String(20), nullable=False, index=True)
    # Status: 'pending', 'synced', 'failed', 'skipped'
    
    # Error information
    error_message = db.Column(db.Text, nullable=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    synced_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    integration = db.relationship('CalendarIntegration', backref='sync_events')
    time_entry = db.relationship('TimeEntry', backref='calendar_sync_events')
    
    def __repr__(self):
        return f'<CalendarSyncEvent {self.event_type} ({self.status})>'

