from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
import os


class User(UserMixin, db.Model):
    """User model for username-based authentication"""

    __tablename__ = "users"
    __table_args__ = (db.UniqueConstraint("oidc_issuer", "oidc_sub", name="uq_users_oidc_issuer_sub"),)

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(200), nullable=True, index=True)
    full_name = db.Column(db.String(200), nullable=True)
    role = db.Column(db.String(20), default="user", nullable=False)  # 'user' or 'admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    theme_preference = db.Column(db.String(10), default=None, nullable=True)  # 'light' | 'dark' | None=system
    preferred_language = db.Column(db.String(8), default=None, nullable=True)  # e.g., 'en', 'de'
    oidc_sub = db.Column(db.String(255), nullable=True)
    oidc_issuer = db.Column(db.String(255), nullable=True)
    avatar_filename = db.Column(db.String(255), nullable=True)
    password_hash = db.Column(db.String(255), nullable=True)

    # User preferences and settings
    email_notifications = db.Column(db.Boolean, default=True, nullable=False)  # Enable/disable email notifications
    notification_overdue_invoices = db.Column(db.Boolean, default=True, nullable=False)  # Notify about overdue invoices
    notification_task_assigned = db.Column(db.Boolean, default=True, nullable=False)  # Notify when assigned to task
    notification_task_comments = db.Column(db.Boolean, default=True, nullable=False)  # Notify about task comments
    notification_weekly_summary = db.Column(db.Boolean, default=False, nullable=False)  # Send weekly time summary
    timezone = db.Column(db.String(50), nullable=True)  # User-specific timezone override
    date_format = db.Column(db.String(20), default="YYYY-MM-DD", nullable=False)  # Date format preference
    time_format = db.Column(db.String(10), default="24h", nullable=False)  # '12h' or '24h'
    week_start_day = db.Column(db.Integer, default=1, nullable=False)  # 0=Sunday, 1=Monday, etc.

    # Time rounding preferences
    time_rounding_enabled = db.Column(db.Boolean, default=True, nullable=False)  # Enable/disable time rounding
    time_rounding_minutes = db.Column(db.Integer, default=1, nullable=False)  # Rounding interval: 1, 5, 10, 15, 30, 60
    time_rounding_method = db.Column(db.String(10), default="nearest", nullable=False)  # 'nearest', 'up', or 'down'

    # Overtime settings
    standard_hours_per_day = db.Column(
        db.Float, default=8.0, nullable=False
    )  # Standard working hours per day for overtime calculation

    # Client portal settings
    client_portal_enabled = db.Column(db.Boolean, default=False, nullable=False)  # Enable/disable client portal access
    client_id = db.Column(
        db.Integer, db.ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True
    )  # Link user to a client for portal access

    # Relationships
    time_entries = db.relationship("TimeEntry", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    project_costs = db.relationship("ProjectCost", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    favorite_projects = db.relationship(
        "Project",
        secondary="user_favorite_projects",
        lazy="dynamic",
        backref=db.backref("favorited_by", lazy="dynamic"),
    )
    roles = db.relationship("Role", secondary="user_roles", lazy="joined", backref=db.backref("users", lazy="dynamic"))
    client = db.relationship("Client", backref="portal_users", lazy="joined")

    def __init__(self, username, role="user", email=None, full_name=None):
        self.username = username.lower().strip()
        self.role = role
        self.email = email or None
        self.full_name = full_name or None
        # Set default for standard_hours_per_day if not set by SQLAlchemy
        if not hasattr(self, "standard_hours_per_day") or self.standard_hours_per_day is None:
            self.standard_hours_per_day = 8.0

    def __repr__(self):
        return f"<User {self.username}>"

    def set_password(self, password):
        """
        Set the user's password hash.
        For OIDC users, password is optional.
        """
        if password:
            self.password_hash = generate_password_hash(password)
        else:
            self.password_hash = None

    def check_password(self, password):
        """
        Check if the provided password matches the user's password hash.
        Returns False if no password is set or if password doesn't match.
        """
        if not self.password_hash or not password:
            return False
        return check_password_hash(self.password_hash, password)

    @property
    def has_password(self):
        """Check if user has a password set"""
        return bool(self.password_hash)

    @property
    def is_admin(self):
        """Check if user is an admin"""
        # Backward compatibility: check legacy role field first
        if self.role == "admin":
            return True
        # Check if user has any admin role
        return any(role.name in ["admin", "super_admin"] for role in self.roles)

    @property
    def active_timer(self):
        """Get the user's currently active timer"""
        from .time_entry import TimeEntry

        return TimeEntry.query.filter_by(user_id=self.id, end_time=None).first()

    @property
    def total_hours(self):
        """Calculate total hours worked by this user"""
        from .time_entry import TimeEntry

        total_seconds = (
            db.session.query(db.func.sum(TimeEntry.duration_seconds))
            .filter(TimeEntry.user_id == self.id, TimeEntry.end_time.isnot(None))
            .scalar()
            or 0
        )
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

        return (
            self.time_entries.filter(TimeEntry.end_time.isnot(None))
            .order_by(TimeEntry.start_time.desc())
            .limit(limit)
            .all()
        )

    def update_last_login(self):
        """Update the last login timestamp"""
        self.last_login = datetime.utcnow()
        db.session.commit()

    def to_dict(self):
        """Convert user to dictionary for API responses"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "display_name": self.display_name,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "is_active": self.is_active,
            "total_hours": self.total_hours,
            "avatar_url": self.get_avatar_url(),
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

            # Avatars are now stored in /data volume to persist between container updates
            upload_folder = os.path.join(current_app.config.get("UPLOAD_FOLDER", "/data/uploads"), "avatars")
            return os.path.join(upload_folder, self.avatar_filename)
        except Exception:
            # Fallback for development/non-docker environments
            return os.path.join("/data/uploads", "avatars", self.avatar_filename)

    def has_avatar(self):
        """Check whether the user's avatar file exists on disk"""
        path = self.get_avatar_path()
        return bool(path and os.path.exists(path))

    # Favorite projects helpers
    def add_favorite_project(self, project):
        """Add a project to user's favorites"""
        if not self.is_project_favorite(project):
            self.favorite_projects.append(project)
            db.session.commit()

    def remove_favorite_project(self, project):
        """Remove a project from user's favorites"""
        if self.is_project_favorite(project):
            self.favorite_projects.remove(project)
            db.session.commit()

    def is_project_favorite(self, project):
        """Check if a project is in user's favorites"""
        from .project import Project

        if isinstance(project, int):
            project_id = project
            return self.favorite_projects.filter_by(id=project_id).count() > 0
        elif isinstance(project, Project):
            return self.favorite_projects.filter_by(id=project.id).count() > 0
        return False

    def get_favorite_projects(self, status="active"):
        """Get user's favorite projects, optionally filtered by status"""
        query = self.favorite_projects
        if status:
            query = query.filter_by(status=status)
        return query.order_by("name").all()

    # Permission and role helpers
    def has_permission(self, permission_name):
        """Check if user has a specific permission through any of their roles"""
        # Super admin users have all permissions
        if self.role == "admin" and not self.roles:
            # Legacy admin users without roles have all permissions
            return True

        # Check if any of the user's roles have this permission
        for role in self.roles:
            if role.has_permission(permission_name):
                return True
        return False

    def has_any_permission(self, *permission_names):
        """Check if user has any of the specified permissions"""
        return any(self.has_permission(perm) for perm in permission_names)

    def has_all_permissions(self, *permission_names):
        """Check if user has all of the specified permissions"""
        return all(self.has_permission(perm) for perm in permission_names)

    def add_role(self, role):
        """Add a role to this user"""
        if role not in self.roles:
            self.roles.append(role)

    def remove_role(self, role):
        """Remove a role from this user"""
        if role in self.roles:
            self.roles.remove(role)

    def get_all_permissions(self):
        """Get all permissions this user has through their roles"""
        permissions = set()
        for role in self.roles:
            for permission in role.permissions:
                permissions.add(permission)
        return list(permissions)

    def get_role_names(self):
        """Get list of role names for this user"""
        return [r.name for r in self.roles]

    # Client portal helpers
    @property
    def is_client_portal_user(self):
        """Check if user has client portal access enabled"""
        return self.client_portal_enabled and self.client_id is not None

    def get_client_portal_data(self):
        """Get data for client portal view (projects, invoices, time entries for assigned client)"""
        if not self.is_client_portal_user:
            return None

        from .project import Project
        from .invoice import Invoice
        from .time_entry import TimeEntry
        from .client import Client

        # Get client - try relationship first, then query by ID if needed
        client = self.client
        if not client and self.client_id:
            # Relationship might not be loaded, query directly
            client = Client.query.get(self.client_id)

        if not client:
            return None

        # Get active projects for this client
        projects = Project.query.filter_by(client_id=client.id, status="active").order_by(Project.name).all()

        # Get invoices for this client
        invoices = Invoice.query.filter_by(client_id=client.id).order_by(Invoice.issue_date.desc()).limit(50).all()

        # Get time entries for projects belonging to this client
        project_ids = [p.id for p in projects]
        time_entries = (
            TimeEntry.query.filter(TimeEntry.project_id.in_(project_ids), TimeEntry.end_time.isnot(None))
            .order_by(TimeEntry.start_time.desc())
            .limit(100)
            .all()
        )

        return {"client": client, "projects": projects, "invoices": invoices, "time_entries": time_entries}
