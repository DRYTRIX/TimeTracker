from datetime import datetime
from app import db


class Activity(db.Model):
    """Activity log for tracking user actions across the system
    
    Provides a comprehensive audit trail and activity feed showing
    what users are doing in the application.
    """
    
    __tablename__ = 'activities'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Action details
    action = db.Column(db.String(50), nullable=False, index=True)  # 'created', 'updated', 'deleted', 'started', 'stopped', etc.
    entity_type = db.Column(db.String(50), nullable=False, index=True)  # 'project', 'task', 'time_entry', 'invoice', 'client'
    entity_id = db.Column(db.Integer, nullable=False, index=True)
    entity_name = db.Column(db.String(500), nullable=True)  # Cached name for display
    
    # Description and extra data
    description = db.Column(db.Text, nullable=True)  # Human-readable description
    extra_data = db.Column(db.JSON, nullable=True)  # Additional context (changes, values, etc.)
    
    # IP and user agent for security audit
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = db.relationship('User', backref='activities')
    
    # Indexes for common queries
    __table_args__ = (
        db.Index('ix_activities_user_created', 'user_id', 'created_at'),
        db.Index('ix_activities_entity', 'entity_type', 'entity_id'),
    )
    
    def __repr__(self):
        return f'<Activity {self.user.username if self.user else "Unknown"} {self.action} {self.entity_type}#{self.entity_id}>'
    
    @classmethod
    def log(cls, user_id, action, entity_type, entity_id, entity_name=None, description=None, extra_data=None, metadata=None, ip_address=None, user_agent=None):
        """Convenience method to log an activity
        
        Usage:
            Activity.log(
                user_id=current_user.id,
                action='created',
                entity_type='project',
                entity_id=project.id,
                entity_name=project.name,
                description=f'Created project "{project.name}"'
            )
        
        Note: 'metadata' parameter is deprecated, use 'extra_data' instead.
        """
        # Support both parameter names for backward compatibility
        data = extra_data if extra_data is not None else metadata
        
        activity = cls(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            description=description,
            extra_data=data,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.session.add(activity)
        try:
            db.session.commit()
            
            # Emit WebSocket event for real-time updates
            try:
                from app import socketio
                socketio.emit('activity_created', {
                    'activity': activity.to_dict(),
                    'user_id': user_id
                })
            except Exception as socket_error:
                # Don't let WebSocket errors break activity logging
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to emit activity WebSocket event: {socket_error}")
        except Exception as e:
            db.session.rollback()
            # Don't let activity logging break the main flow
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to log activity: {e}")
    
    @classmethod
    def get_recent(cls, user_id=None, limit=50, entity_type=None):
        """Get recent activities
        
        Args:
            user_id: Filter by user (None for all users)
            limit: Maximum number of activities to return
            entity_type: Filter by entity type
        """
        query = cls.query
        
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        if entity_type:
            query = query.filter_by(entity_type=entity_type)
        
        return query.order_by(cls.created_at.desc()).limit(limit).all()
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'display_name': self.user.display_name if self.user else None,
            'action': self.action,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'entity_name': self.entity_name,
            'description': self.description,
            'extra_data': self.extra_data,
            'metadata': self.extra_data,  # For backward compatibility
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def get_icon(self):
        """Get icon class for this activity type"""
        icons = {
            'created': 'fas fa-plus-circle text-green-500',
            'updated': 'fas fa-edit text-blue-500',
            'deleted': 'fas fa-trash text-red-500',
            'started': 'fas fa-play text-green-500',
            'stopped': 'fas fa-stop text-red-500',
            'completed': 'fas fa-check-circle text-green-500',
            'assigned': 'fas fa-user-plus text-blue-500',
            'commented': 'fas fa-comment text-gray-500',
            'sent': 'fas fa-paper-plane text-blue-500',
            'paid': 'fas fa-dollar-sign text-green-500',
        }
        return icons.get(self.action, 'fas fa-circle text-gray-500')
    
    def get_color(self):
        """Get color class for this activity type"""
        colors = {
            'created': 'green',
            'updated': 'blue',
            'deleted': 'red',
            'started': 'green',
            'stopped': 'red',
            'completed': 'green',
            'assigned': 'blue',
            'commented': 'gray',
            'sent': 'blue',
            'paid': 'green',
        }
        return colors.get(self.action, 'gray')

