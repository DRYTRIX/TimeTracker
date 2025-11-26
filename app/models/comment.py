from datetime import datetime
from app import db
from app.utils.timezone import now_in_app_timezone

class Comment(db.Model):
    """Comment model for project and task discussions"""
    
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    
    # Reference to either project, task, or quote (one will be null)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True, index=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=True, index=True)
    quote_id = db.Column(db.Integer, db.ForeignKey('quotes.id', ondelete='CASCADE'), nullable=True, index=True)
    
    # Author of the comment
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Visibility: True = internal team comment, False = client-visible comment
    is_internal = db.Column(db.Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=now_in_app_timezone, nullable=False)
    updated_at = db.Column(db.DateTime, default=now_in_app_timezone, onupdate=now_in_app_timezone, nullable=False)
    
    # Optional: for threaded comments (replies to other comments)
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=True, index=True)
    
    # Relationships
    author = db.relationship('User', backref='comments')
    project = db.relationship('Project', backref='comments')
    task = db.relationship('Task', backref='comments')
    quote = db.relationship('Quote', backref='comments')
    
    # Self-referential relationship for replies
    parent = db.relationship('Comment', remote_side=[id], backref='replies')
    
    def __init__(self, content, user_id, project_id=None, task_id=None, quote_id=None, parent_id=None, is_internal=True):
        """Create a comment.
        
        Args:
            content: The comment text
            user_id: ID of the user creating the comment
            project_id: ID of the project (if this is a project comment)
            task_id: ID of the task (if this is a task comment)
            parent_id: ID of parent comment (if this is a reply)
        """
        if not project_id and not task_id and not quote_id:
            raise ValueError("Comment must be associated with either a project, task, or quote")
        
        # Ensure only one target is set
        targets = [x for x in [project_id, task_id, quote_id] if x is not None]
        if len(targets) > 1:
            raise ValueError("Comment cannot be associated with multiple targets")
        
        self.content = content.strip()
        self.user_id = user_id
        self.project_id = project_id
        self.task_id = task_id
        self.quote_id = quote_id
        self.parent_id = parent_id
        self.is_internal = is_internal
    
    def __repr__(self):
        if self.project_id:
            target = f"Project {self.project_id}"
        elif self.task_id:
            target = f"Task {self.task_id}"
        elif self.quote_id:
            target = f"Quote {self.quote_id}"
        else:
            target = "Unknown"
        return f'<Comment by {self.author.username if self.author else "Unknown"} on {target}>'
    
    @property
    def is_reply(self):
        """Check if this comment is a reply to another comment"""
        return self.parent_id is not None
    
    @property
    def target_type(self):
        """Get the type of target this comment is attached to"""
        if self.project_id:
            return 'project'
        elif self.task_id:
            return 'task'
        elif self.quote_id:
            return 'quote'
        return 'unknown'
    
    @property
    def target_name(self):
        """Get the name of the target this comment is attached to"""
        if self.project_id and self.project:
            return self.project.name
        elif self.task_id and self.task:
            return self.task.name
        elif self.quote_id and self.quote:
            return self.quote.title
        return 'Unknown'
    
    @property
    def reply_count(self):
        """Get the number of replies to this comment"""
        return len(self.replies) if self.replies else 0
    
    def can_edit(self, user):
        """Check if a user can edit this comment"""
        return user.id == self.user_id or user.is_admin
    
    def can_delete(self, user):
        """Check if a user can delete this comment"""
        return user.id == self.user_id or user.is_admin
    
    def edit_content(self, new_content, user):
        """Edit the comment content"""
        if not self.can_edit(user):
            raise PermissionError("User does not have permission to edit this comment")
        
        self.content = new_content.strip()
        self.updated_at = now_in_app_timezone()
        db.session.commit()
    
    def delete_comment(self, user):
        """Delete the comment (soft delete by clearing content)"""
        if not self.can_delete(user):
            raise PermissionError("User does not have permission to delete this comment")
        
        # If the comment has replies, we'll mark it as deleted but keep the structure
        if self.replies:
            self.content = "[Comment deleted]"
            self.updated_at = now_in_app_timezone()
        else:
            # If no replies, we can safely delete it
            db.session.delete(self)
        
        db.session.commit()
    
    def to_dict(self):
        """Convert comment to dictionary for API responses"""
        return {
            'id': self.id,
            'content': self.content,
            'project_id': self.project_id,
            'task_id': self.task_id,
            'quote_id': self.quote_id,
            'user_id': self.user_id,
            'author': self.author.username if self.author else None,
            'author_full_name': self.author.full_name if self.author and self.author.full_name else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'parent_id': self.parent_id,
            'is_reply': self.is_reply,
            'reply_count': self.reply_count,
            'target_type': self.target_type,
            'target_name': self.target_name,
            'is_internal': self.is_internal
        }
    
    @classmethod
    def get_project_comments(cls, project_id, include_replies=True):
        """Get all comments for a project"""
        query = cls.query.filter_by(project_id=project_id)
        
        if not include_replies:
            query = query.filter_by(parent_id=None)
        
        return query.order_by(cls.created_at.asc()).all()
    
    @classmethod
    def get_task_comments(cls, task_id, include_replies=True):
        """Get all comments for a task"""
        query = cls.query.filter_by(task_id=task_id)
        
        if not include_replies:
            query = query.filter_by(parent_id=None)
        
        return query.order_by(cls.created_at.asc()).all()
    
    @classmethod
    def get_user_comments(cls, user_id, limit=None):
        """Get recent comments by a user"""
        query = cls.query.filter_by(user_id=user_id).order_by(cls.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @classmethod
    def get_quote_comments(cls, quote_id, include_replies=True, include_internal=True):
        """Get all comments for a quote"""
        query = cls.query.filter_by(quote_id=quote_id)
        
        if not include_internal:
            query = query.filter_by(is_internal=False)
        
        if not include_replies:
            query = query.filter_by(parent_id=None)
        
        return query.order_by(cls.created_at.asc()).all()
    
    @classmethod
    def get_recent_comments(cls, limit=10):
        """Get recent comments across all projects, tasks, and quotes"""
        return cls.query.order_by(cls.created_at.desc()).limit(limit).all()
