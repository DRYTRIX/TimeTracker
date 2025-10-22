from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
import os

class User(UserMixin, db.Model):
    """User model for username-based authentication"""
    
    __tablename__ = 'users'
    __table_args__ = (
        db.UniqueConstraint('oidc_issuer', 'oidc_sub', name='uq_users_oidc_issuer_sub'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(200), nullable=True, index=True)
    full_name = db.Column(db.String(200), nullable=True)
    role = db.Column(db.String(20), default='user', nullable=False)  # 'user' or 'admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    theme_preference = db.Column(db.String(10), default=None, nullable=True)  # 'light' | 'dark' | None=system
    preferred_language = db.Column(db.String(8), default=None, nullable=True)  # e.g., 'en', 'de'
    oidc_sub = db.Column(db.String(255), nullable=True)
    oidc_issuer = db.Column(db.String(255), nullable=True)
    avatar_filename = db.Column(db.String(255), nullable=True)
    
    # Relationships
    time_entries = db.relationship('TimeEntry', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    project_costs = db.relationship('ProjectCost', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def __init__(self, username, role='user', email=None, full_name=None):
        self.username = username.lower().strip()
        self.role = role
        self.email = (email or None)
        self.full_name = (full_name or None)
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    @property
    def is_admin(self):
        """Check if user is an admin"""
        return self.role == 'admin'
    
    @property
    def active_timer(self):
        """Get the user's currently active timer"""
        from .time_entry import TimeEntry
        return TimeEntry.query.filter_by(
            user_id=self.id,
            end_time=None
        ).first()
    
    @property
    def total_hours(self):
        """Calculate total hours worked by this user"""
        from .time_entry import TimeEntry
        total_seconds = db.session.query(
            db.func.sum(TimeEntry.duration_seconds)
        ).filter(
            TimeEntry.user_id == self.id,
            TimeEntry.end_time.isnot(None)
        ).scalar() or 0
        return round(total_seconds / 3600, 2)

    @property
    def display_name(self):
        """Preferred display name: full name if available, else username"""
        if self.full_name and self.full_name.strip():
            return self.full_name.strip()
        return self.username
    
    def get_recent_entries(self, limit=10):
        """Get recent time entries for this user"""
        from .time_entry import TimeEntry
        return self.time_entries.filter(
            TimeEntry.end_time.isnot(None)
        ).order_by(
            TimeEntry.start_time.desc()
        ).limit(limit).all()
    
    def update_last_login(self):
        """Update the last login timestamp"""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def to_dict(self):
        """Convert user to dictionary for API responses"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'display_name': self.display_name,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'is_active': self.is_active,
            'total_hours': self.total_hours,
            'avatar_url': self.get_avatar_url(),
        }

    # Avatar helpers
    def get_avatar_url(self):
        """Return the public URL for the user's avatar, or None if not set"""
        if self.avatar_filename:
            return f"/uploads/avatars/{self.avatar_filename}"
        return None

    def get_avatar_path(self):
        """Return absolute filesystem path to the user's avatar, or None if not set"""
        if not self.avatar_filename:
            return None
        try:
            from flask import current_app
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'avatars')
            return os.path.join(upload_folder, self.avatar_filename)
        except Exception:
            return os.path.join('app', 'static', 'uploads', 'avatars', self.avatar_filename)

    def has_avatar(self):
        """Check whether the user's avatar file exists on disk"""
        path = self.get_avatar_path()
        return bool(path and os.path.exists(path))
