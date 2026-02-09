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
    password_change_required = db.Column(
        db.Boolean, default=False, nullable=False
    )  # Force password change on first login

    # User preferences and settings
    email_notifications = db.Column(db.Boolean, default=True, nullable=False)  # Enable/disable email notifications
    notification_overdue_invoices = db.Column(db.Boolean, default=True, nullable=False)  # Notify about overdue invoices
    notification_task_assigned = db.Column(db.Boolean, default=True, nullable=False)  # Notify when assigned to task
    notification_task_comments = db.Column(db.Boolean, default=True, nullable=False)  # Notify about task comments
    notification_weekly_summary = db.Column(db.Boolean, default=False, nullable=False)  # Send weekly time summary
    timezone = db.Column(db.String(50), nullable=True)  # User-specific timezone override
    date_format = db.Column(db.String(20), default=None, nullable=True)  # None = use system default
    time_format = db.Column(db.String(10), default=None, nullable=True)  # None = use system default
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

    # Calendar item type colors (hex e.g. #3b82f6); when null, app uses defaults
    calendar_color_events = db.Column(db.String(7), nullable=True)
    calendar_color_tasks = db.Column(db.String(7), nullable=True)
    calendar_color_time_entries = db.Column(db.String(7), nullable=True)
    # Calendar default view: 'day' | 'week' | 'month'; None = use last view (session)
    calendar_default_view = db.Column(db.String(10), nullable=True)

    # UI feature flags - allow users to customize which features are visible
    # All default to True (enabled) for backward compatibility
    # Calendar section
    ui_show_calendar = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide Calendar section

    # Time Tracking section items
    ui_show_project_templates = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide Project Templates
    ui_show_gantt_chart = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide Gantt Chart
    ui_show_kanban_board = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide Kanban Board
    ui_show_weekly_goals = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide Weekly Goals
    ui_show_issues = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide Issues feature

    # CRM section
    ui_show_quotes = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide Quotes

    # Finance & Expenses section items
    ui_show_reports = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide Reports
    ui_show_report_builder = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide Report Builder
    ui_show_scheduled_reports = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide Scheduled Reports
    ui_show_invoice_approvals = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide Invoice Approvals
    ui_show_payment_gateways = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide Payment Gateways
    ui_show_recurring_invoices = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide Recurring Invoices
    ui_show_payments = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide Payments
    ui_show_mileage = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide Mileage
    ui_show_per_diem = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide Per Diem
    ui_show_budget_alerts = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide Budget Alerts

    # Inventory section
    ui_show_inventory = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide Inventory section

    # Analytics
    ui_show_analytics = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide Analytics

    # Tools & Data section
    ui_show_tools = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide Tools & Data section
    ui_show_integrations = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide Integrations
    ui_show_import_export = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide Import/Export
    ui_show_saved_filters = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide Saved Filters

    # CRM section (additional)
    ui_show_contacts = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide Contacts
    ui_show_deals = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide Deals
    ui_show_leads = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide Leads

    # Finance section (additional)
    ui_show_invoices = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide Invoices
    ui_show_expenses = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide Expenses

    # Time Tracking section (additional)
    ui_show_time_entry_templates = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide Time Entry Templates

    # Advanced features
    ui_show_workflows = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide Workflows
    ui_show_time_approvals = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide Time Approvals
    ui_show_activity_feed = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide Activity Feed
    ui_show_recurring_tasks = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide Recurring Tasks
    ui_show_team_chat = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide Team Chat
    ui_show_client_portal = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide Client Portal
    ui_show_kiosk = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide Kiosk Mode
    ui_show_donate = db.Column(db.Boolean, default=True, nullable=False)  # Show/hide donate/support UI

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
    def is_super_admin(self):
        """Check if user is a super admin"""
        # Check if user has super_admin role
        return any(role.name == "super_admin" for role in self.roles)

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

    def is_online(self):
        """Check if user is currently online (active within last 15 minutes)"""
        if not self.last_login:
            return False
        from datetime import timedelta
        threshold = datetime.utcnow() - timedelta(minutes=15)
        return self.last_login >= threshold

    def get_status(self):
        """Get user status: 'online', 'offline', or 'away'"""
        if not self.last_login:
            return "offline"
        
        from datetime import timedelta
        now = datetime.utcnow()
        time_since_login = now - self.last_login
        
        # Online if active within last 15 minutes
        if time_since_login <= timedelta(minutes=15):
            return "online"
        # Away if active within last 1 hour
        elif time_since_login <= timedelta(hours=1):
            return "away"
        # Offline otherwise
        else:
            return "offline"

    def to_dict(self):
        """Convert user to dictionary for API responses.
        Includes resolved date_format and time_format (user override or system default) for clients (e.g. mobile).
        """
        from app.utils.timezone import (
            get_resolved_date_format_key,
            get_resolved_time_format_key,
            get_user_timezone_name,
            get_app_timezone,
        )
        try:
            resolved_date = get_resolved_date_format_key(self)
            resolved_time = get_resolved_time_format_key(self)
            resolved_timezone = get_user_timezone_name(self) or get_app_timezone()
        except Exception:
            resolved_date = "YYYY-MM-DD"
            resolved_time = "24h"
            resolved_timezone = "Europe/Rome"
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
            "status": self.get_status(),
            "date_format": resolved_date,
            "time_format": resolved_time,
            "timezone": resolved_timezone,
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
        # Auto-assign role from legacy role field if user has no roles assigned
        if not self.roles and self.role:
            self._auto_assign_role_from_legacy()
        
        # Super admin users have all permissions
        if self.role == "admin" and not self.roles:
            # Legacy admin users without roles have all permissions
            return True

        # Check if any of the user's roles have this permission
        for role in self.roles:
            if role.has_permission(permission_name):
                return True
        
        # Fallback: Check legacy role field if no roles assigned
        # This handles cases where role assignment failed or user is in transition
        if not self.roles and self.role:
            from app.models import Role
            legacy_role = Role.query.filter_by(name=self.role).first()
            if legacy_role and legacy_role.has_permission(permission_name):
                return True
        
        return False
    
    def _auto_assign_role_from_legacy(self):
        """Auto-assign role from legacy role field if user has no roles assigned"""
        if self.roles or not self.role:
            return
        
        from app.models import Role
        role_obj = Role.query.filter_by(name=self.role).first()
        if role_obj:
            self.roles.append(role_obj)
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()

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

    @property
    def primary_role_name(self):
        """Get the primary role name for display purposes.
        Returns the first role name from roles, or falls back to the legacy role field."""
        if self.roles:
            # Return the first role name (roles are typically ordered by importance)
            return self.roles[0].name
        # Fallback to legacy role field for backward compatibility
        return self.role

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
