from datetime import datetime
from app import db
from app.utils.timezone import now_in_app_timezone
import json


class AuditLog(db.Model):
    """Audit log model for tracking detailed changes to entities
    
    Provides comprehensive audit trail tracking:
    - Who made the change (user_id)
    - What entity was changed (entity_type, entity_id)
    - When the change occurred (created_at)
    - What changed (field_name, old_value, new_value)
    - Action type (created, updated, deleted)
    - Additional context (ip_address, user_agent, request_path)
    """
    
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # User who made the change
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Entity being changed
    entity_type = db.Column(db.String(50), nullable=False, index=True)  # 'project', 'task', 'time_entry', 'invoice', 'client', 'user', etc.
    entity_id = db.Column(db.Integer, nullable=False, index=True)
    entity_name = db.Column(db.String(500), nullable=True)  # Cached name for display
    
    # Action details
    action = db.Column(db.String(20), nullable=False)  # 'created', 'updated', 'deleted' - index defined in __table_args__
    field_name = db.Column(db.String(100), nullable=True, index=True)  # Name of the field that changed (None for create/delete)
    
    # Change values (stored as JSON for flexibility)
    old_value = db.Column(db.Text, nullable=True)  # JSON-encoded old value
    new_value = db.Column(db.Text, nullable=True)  # JSON-encoded new value
    
    # Human-readable change description
    change_description = db.Column(db.Text, nullable=True)
    
    # Additional context
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    request_path = db.Column(db.String(500), nullable=True)
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=now_in_app_timezone, nullable=False)  # index defined in __table_args__
    
    # Relationships
    user = db.relationship('User', backref='audit_logs')
    
    # Indexes for common queries
    __table_args__ = (
        db.Index('ix_audit_logs_entity', 'entity_type', 'entity_id'),
        db.Index('ix_audit_logs_user_created', 'user_id', 'created_at'),
        db.Index('ix_audit_logs_created_at', 'created_at'),
        db.Index('ix_audit_logs_action', 'action'),
    )
    
    def __repr__(self):
        return f'<AuditLog {self.action} {self.entity_type}#{self.entity_id} by user#{self.user_id}>'
    
    @classmethod
    def log_change(cls, user_id, action, entity_type, entity_id, field_name=None, 
                   old_value=None, new_value=None, entity_name=None, 
                   change_description=None, ip_address=None, user_agent=None, 
                   request_path=None):
        """Log a change to the audit trail
        
        Args:
            user_id: ID of the user making the change (None for system actions)
            action: 'created', 'updated', or 'deleted'
            entity_type: Type of entity (e.g., 'project', 'task', 'time_entry')
            entity_id: ID of the entity being changed
            field_name: Name of the field that changed (None for create/delete actions)
            old_value: Previous value (will be JSON-encoded)
            new_value: New value (will be JSON-encoded)
            entity_name: Cached name of the entity for display
            change_description: Human-readable description of the change
            ip_address: IP address of the request
            user_agent: User agent string
            request_path: Path of the request that triggered the change
        """
        # Encode values as JSON if they're not already strings
        old_val_str = cls._encode_value(old_value)
        new_val_str = cls._encode_value(new_value)
        
        audit_log = cls(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            field_name=field_name,
            old_value=old_val_str,
            new_value=new_val_str,
            entity_name=entity_name,
            change_description=change_description,
            ip_address=ip_address,
            user_agent=user_agent,
            request_path=request_path
        )
        
        try:
            # Add to session - don't commit here as we're likely in the middle of a transaction
            # The main transaction will commit everything together
            db.session.add(audit_log)
            # Flush to ensure the audit log is part of the current transaction
            # but don't commit - let the main transaction handle that
            db.session.flush()
        except Exception as e:
            # Don't rollback - that would rollback the entire transaction including the main operation!
            # Just remove the audit log from the session and continue
            try:
                db.session.expunge(audit_log)
            except Exception:
                pass
            # Don't let audit logging break the main flow
            # Use debug level to avoid cluttering logs with expected errors
            # (e.g., when audit_logs table doesn't exist yet)
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Failed to log audit change (non-critical): {e}")
    
    @staticmethod
    def _encode_value(value):
        """Encode a value as JSON string, handling None and special types"""
        if value is None:
            return None
        
        # Handle datetime objects
        if isinstance(value, datetime):
            return value.isoformat()
        
        # Handle Decimal and other types that aren't JSON serializable
        try:
            return json.dumps(value, default=str)
        except (TypeError, ValueError):
            return str(value)
    
    @staticmethod
    def _decode_value(value_str):
        """Decode a JSON string back to a Python value"""
        if value_str is None:
            return None
        
        try:
            return json.loads(value_str)
        except (json.JSONDecodeError, TypeError):
            # If it's not valid JSON, return as string
            return value_str
    
    def get_old_value(self):
        """Get the decoded old value"""
        return self._decode_value(self.old_value)
    
    def get_new_value(self):
        """Get the decoded new value"""
        return self._decode_value(self.new_value)
    
    @classmethod
    def get_for_entity(cls, entity_type, entity_id, limit=100):
        """Get audit logs for a specific entity"""
        return cls.query.filter_by(
            entity_type=entity_type,
            entity_id=entity_id
        ).order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def get_for_user(cls, user_id, limit=100):
        """Get audit logs for actions by a specific user"""
        return cls.query.filter_by(user_id=user_id).order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def get_recent(cls, limit=100, entity_type=None, user_id=None, action=None):
        """Get recent audit logs with optional filters"""
        query = cls.query
        
        if entity_type:
            query = query.filter_by(entity_type=entity_type)
        
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        if action:
            query = query.filter_by(action=action)
        
        return query.order_by(cls.created_at.desc()).limit(limit).all()
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'display_name': self.user.display_name if self.user else None,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'entity_name': self.entity_name,
            'action': self.action,
            'field_name': self.field_name,
            'old_value': self.get_old_value(),
            'new_value': self.get_new_value(),
            'change_description': self.change_description,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'request_path': self.request_path,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def get_icon(self):
        """Get icon class for this audit log action"""
        icons = {
            'created': 'fas fa-plus-circle text-green-500',
            'updated': 'fas fa-edit text-blue-500',
            'deleted': 'fas fa-trash text-red-500',
        }
        return icons.get(self.action, 'fas fa-circle text-gray-500')
    
    def get_color(self):
        """Get color class for this audit log action"""
        colors = {
            'created': 'green',
            'updated': 'blue',
            'deleted': 'red',
        }
        return colors.get(self.action, 'gray')

