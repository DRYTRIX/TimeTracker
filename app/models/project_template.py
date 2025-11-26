"""Project template model for reusable project configurations"""
from datetime import datetime
from decimal import Decimal
from app import db


class ProjectTemplate(db.Model):
    """Template for creating projects with pre-configured settings"""
    
    __tablename__ = 'project_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    
    # Template configuration (JSON)
    # Contains: client_id (optional), description, billable, hourly_rate, 
    # billing_ref, code, estimated_hours, budget_amount, budget_threshold_percent
    config = db.Column(db.JSON, nullable=False, default=dict)
    
    # Template tasks (JSON array of task configurations)
    # Each task: {name, description, priority, status, estimated_hours}
    tasks = db.Column(db.JSON, nullable=True, default=list)
    
    # Template categories/tags
    category = db.Column(db.String(100), nullable=True, index=True)
    tags = db.Column(db.JSON, nullable=True, default=list)
    
    # Visibility
    is_public = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Usage statistics
    usage_count = db.Column(db.Integer, default=0, nullable=False)
    last_used_at = db.Column(db.DateTime, nullable=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    creator = db.relationship('User', backref='project_templates')
    
    def __repr__(self):
        return f'<ProjectTemplate {self.name}>'
    
    def to_dict(self):
        """Convert template to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'config': self.config or {},
            'tasks': self.tasks or [],
            'category': self.category,
            'tags': self.tags or [],
            'is_public': self.is_public,
            'created_by': self.created_by,
            'usage_count': self.usage_count,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

