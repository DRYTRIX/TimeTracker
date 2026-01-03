from datetime import datetime, timedelta
from decimal import Decimal
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from .client_prepaid_consumption import ClientPrepaidConsumption
import secrets
import json


class Client(db.Model):
    """Client model for managing client information and rates"""

    __tablename__ = "clients"
    __table_args__ = (
        db.UniqueConstraint("tenant_id", "name", name="uq_clients_tenant_name"),
        db.UniqueConstraint("tenant_id", "portal_username", name="uq_clients_tenant_portal_username"),
    )

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    contact_person = db.Column(db.String(200), nullable=True)
    email = db.Column(db.String(200), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    address = db.Column(db.Text, nullable=True)
    default_hourly_rate = db.Column(db.Numeric(9, 2), nullable=True)
    status = db.Column(db.String(20), default="active", nullable=False)  # 'active' or 'inactive'
    prepaid_hours_monthly = db.Column(db.Numeric(7, 2), nullable=True)
    prepaid_reset_day = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Client portal settings
    portal_enabled = db.Column(db.Boolean, default=False, nullable=False)  # Enable/disable client portal access
    portal_username = db.Column(db.String(80), nullable=True, index=True)  # Portal login username
    portal_password_hash = db.Column(db.String(255), nullable=True)  # Hashed password for portal access
    password_setup_token = db.Column(db.String(100), nullable=True, index=True)  # Token for password setup/reset
    password_setup_token_expires = db.Column(db.DateTime, nullable=True)  # Token expiration time
    portal_issues_enabled = db.Column(db.Boolean, default=True, nullable=False)  # Enable/disable issue reporting in portal

    # Custom fields for flexible data storage (e.g., debtor_number, ERP IDs, etc.)
    custom_fields = db.Column(db.JSON, nullable=True)

    # Relationships
    projects = db.relationship("Project", backref="client_obj", lazy="dynamic", cascade="all, delete-orphan")
    time_entries = db.relationship("TimeEntry", backref="client", lazy="dynamic", cascade="all, delete-orphan")

    def __init__(
        self,
        name,
        description=None,
        contact_person=None,
        email=None,
        phone=None,
        address=None,
        default_hourly_rate=None,
        company=None,
        prepaid_hours_monthly=None,
        prepaid_reset_day=1,
    ):
        """Create a Client.

        Note: company parameter is accepted for test compatibility but not used,
        as the Client model uses 'name' as the primary identifier.
        """
        self.name = name.strip()
        self.description = description.strip() if description else None
        self.contact_person = contact_person.strip() if contact_person else None
        self.email = email.strip() if email else None
        self.phone = phone.strip() if phone else None
        self.address = address.strip() if address else None
        self.default_hourly_rate = Decimal(str(default_hourly_rate)) if default_hourly_rate else None
        self.prepaid_hours_monthly = (
            Decimal(str(prepaid_hours_monthly)) if prepaid_hours_monthly not in (None, "") else None
        )
        try:
            reset_day = int(prepaid_reset_day) if prepaid_reset_day is not None else 1
            self.prepaid_reset_day = max(1, min(28, reset_day))
        except (TypeError, ValueError):
            self.prepaid_reset_day = 1

    def __repr__(self):
        return f"<Client {self.name}>"

    @property
    def is_active(self):
        """Check if client is active"""
        return self.status == "active"

    @property
    def total_projects(self):
        """Get total number of projects for this client"""
        return self.projects.count()

    @property
    def active_projects(self):
        """Get number of active projects for this client"""
        return self.projects.filter_by(status="active").count()

    @property
    def total_hours(self):
        """Calculate total hours across all projects for this client"""
        total_seconds = 0
        for project in self.projects:
            total_seconds += project.total_hours * 3600  # Convert hours to seconds
        return round(total_seconds / 3600, 2)

    @property
    def total_billable_hours(self):
        """Calculate total billable hours across all projects for this client"""
        total_seconds = 0
        for project in self.projects:
            total_seconds += project.total_billable_hours * 3600  # Convert hours to seconds
        return round(total_seconds / 3600, 2)

    @property
    def estimated_total_cost(self):
        """Calculate estimated total cost based on billable hours and rates"""
        total_cost = 0.0
        for project in self.projects:
            if project.billable and project.hourly_rate:
                total_cost += project.estimated_cost
        return total_cost

    @property
    def prepaid_plan_enabled(self):
        """Return True if client has prepaid hours configured."""
        try:
            hours = Decimal(str(self.prepaid_hours_monthly)) if self.prepaid_hours_monthly is not None else Decimal("0")
        except Exception:
            hours = Decimal("0")
        return hours > 0

    @property
    def prepaid_hours_decimal(self):
        """Return prepaid hours as Decimal with two decimal precision."""
        if self.prepaid_hours_monthly is None:
            return Decimal("0")
        try:
            return Decimal(str(self.prepaid_hours_monthly)).quantize(Decimal("0.01"))
        except Exception:
            return Decimal("0")

    def prepaid_month_start(self, reference_datetime):
        """
        Determine the configured prepaid period start date for a given datetime.

        Args:
            reference_datetime (datetime): Datetime to evaluate.
        Returns:
            date: The start date of the prepaid cycle that contains the reference datetime.
        """
        from datetime import timedelta

        if not reference_datetime:
            return None

        reset_day = self.prepaid_reset_day or 1
        reset_day = max(1, min(28, int(reset_day)))

        dt = reference_datetime
        if isinstance(dt, datetime) and hasattr(dt, "date"):
            dt_date = dt.date()
        else:
            dt_date = dt

        if dt_date.day >= reset_day:
            return dt_date.replace(day=reset_day)

        # Move to previous month
        first_of_month = dt_date.replace(day=1)
        previous_day = first_of_month - timedelta(days=1)
        target_day = min(reset_day, previous_day.day)
        return previous_day.replace(day=target_day)

    def get_prepaid_consumed_hours(self, month_start):
        """Return Decimal hours consumed for the given prepaid cycle."""
        if not month_start:
            return Decimal("0")

        try:
            seconds = (
                self.prepaid_consumptions.filter(ClientPrepaidConsumption.allocation_month == month_start)
                .with_entities(db.func.coalesce(db.func.sum(ClientPrepaidConsumption.seconds_consumed), 0))
                .scalar()
                or 0
            )
        except Exception:
            seconds = 0
        return Decimal(seconds) / Decimal("3600")

    def get_prepaid_remaining_hours(self, month_start):
        """Return how many prepaid hours remain for the cycle starting at month_start."""
        if not self.prepaid_plan_enabled or not month_start:
            return Decimal("0")
        consumed = self.get_prepaid_consumed_hours(month_start)
        remaining = self.prepaid_hours_decimal - consumed
        return remaining if remaining > 0 else Decimal("0")

    def archive(self):
        """Archive the client"""
        self.status = "inactive"
        self.updated_at = datetime.utcnow()

    def activate(self):
        """Activate the client"""
        self.status = "active"
        self.updated_at = datetime.utcnow()

    def get_custom_field(self, key, default=None):
        """Get a custom field value by key"""
        if not self.custom_fields:
            return default
        return self.custom_fields.get(key, default)

    def set_custom_field(self, key, value):
        """Set a custom field value"""
        if self.custom_fields is None:
            self.custom_fields = {}
        self.custom_fields[key] = value
        self.updated_at = datetime.utcnow()

    def remove_custom_field(self, key):
        """Remove a custom field"""
        if self.custom_fields and key in self.custom_fields:
            del self.custom_fields[key]
            self.updated_at = datetime.utcnow()

    def get_rendered_links(self):
        """Get all rendered links from active link templates that match this client's custom fields"""
        from .link_template import LinkTemplate

        if not self.custom_fields:
            return []

        links = []
        templates = LinkTemplate.get_active_templates()

        for template in templates:
            field_value = self.get_custom_field(template.field_key)
            if field_value:
                url = template.render_url(field_value)
                if url:
                    links.append(
                        {
                            "id": template.id,
                            "name": template.name,
                            "url": url,
                            "icon": template.icon,
                            "description": template.description,
                        }
                    )

        return links

    def to_dict(self):
        """Convert client to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "contact_person": self.contact_person,
            "email": self.email,
            "phone": self.phone,
            "address": self.address,
            "default_hourly_rate": str(self.default_hourly_rate) if self.default_hourly_rate else None,
            "status": self.status,
            "is_active": self.is_active,
            "total_projects": self.total_projects,
            "active_projects": self.active_projects,
            "prepaid_hours_monthly": (
                float(self.prepaid_hours_monthly) if self.prepaid_hours_monthly is not None else None
            ),
            "prepaid_reset_day": self.prepaid_reset_day,
            "custom_fields": self.custom_fields or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def get_active_clients(cls):
        """Get all active clients ordered by name"""
        return cls.query.filter_by(status="active").order_by(cls.name).all()

    @classmethod
    def get_all_clients(cls):
        """Get all clients ordered by name"""
        return cls.query.order_by(cls.name).all()

    # Client portal helpers
    def set_portal_password(self, password):
        """Set the portal password for this client"""
        if password:
            self.portal_password_hash = generate_password_hash(password)
        else:
            self.portal_password_hash = None

    def check_portal_password(self, password):
        """Check if the provided password matches the portal password"""
        if not self.portal_password_hash or not password:
            return False
        return check_password_hash(self.portal_password_hash, password)

    @property
    def has_portal_access(self):
        """Check if client has portal access enabled and credentials set"""
        return self.portal_enabled and self.portal_username and self.portal_password_hash

    def get_portal_data(self):
        """Get data for client portal view (projects, invoices, time entries)"""
        if not self.has_portal_access:
            return None

        from .project import Project
        from .invoice import Invoice
        from .time_entry import TimeEntry

        # Get active projects for this client
        projects = Project.query.filter_by(client_id=self.id, status="active").order_by(Project.name).all()

        # Get invoices for this client
        invoices = Invoice.query.filter_by(client_id=self.id).order_by(Invoice.issue_date.desc()).limit(50).all()

        # Get time entries for projects belonging to this client
        project_ids = [p.id for p in projects]
        time_entries = (
            TimeEntry.query.filter(TimeEntry.project_id.in_(project_ids), TimeEntry.end_time.isnot(None))
            .order_by(TimeEntry.start_time.desc())
            .limit(100)
            .all()
        )

        return {"client": self, "projects": projects, "invoices": invoices, "time_entries": time_entries}

    def generate_password_setup_token(self, expires_hours=24):
        """Generate a secure token for password setup/reset"""
        token = secrets.token_urlsafe(32)
        self.password_setup_token = token
        self.password_setup_token_expires = datetime.utcnow() + timedelta(hours=expires_hours)
        return token

    def verify_password_setup_token(self, token):
        """Verify if a password setup token is valid"""
        if not self.password_setup_token or not token:
            return False

        if self.password_setup_token != token:
            return False

        if self.password_setup_token_expires and self.password_setup_token_expires < datetime.utcnow():
            return False

        return True

    def clear_password_setup_token(self):
        """Clear the password setup token after use"""
        self.password_setup_token = None
        self.password_setup_token_expires = None

    @classmethod
    def authenticate_portal(cls, username, password):
        """Authenticate a client portal login"""
        client = cls.query.filter_by(portal_username=username, portal_enabled=True).first()
        if not client:
            return None

        if not client.check_portal_password(password):
            return None

        if not client.is_active:
            return None

        return client

    @classmethod
    def find_by_password_token(cls, token):
        """Find a client by password setup token"""
        if not token:
            return None

        client = cls.query.filter_by(password_setup_token=token).first()
        if not client:
            return None

        if client.password_setup_token_expires and client.password_setup_token_expires < datetime.utcnow():
            return None

        return client
