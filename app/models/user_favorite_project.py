from datetime import datetime
from app import db

class UserFavoriteProject(db.Model):
    """Association table for user favorite projects"""
    
    __tablename__ = 'user_favorite_projects'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Unique constraint to prevent duplicate favorites
    __table_args__ = (
        db.UniqueConstraint('user_id', 'project_id', name='uq_user_project_favorite'),
    )
    
    def __repr__(self):
        return f'<UserFavoriteProject user_id={self.user_id} project_id={self.project_id}>'
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'project_id': self.project_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

