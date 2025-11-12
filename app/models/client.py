from datetime import datetime
from decimal import Decimal
from app import db
from .client_prepaid_consumption import ClientPrepaidConsumption

class Client(db.Model):
    """Client model for managing client information and rates"""
    
    __tablename__ = 'clients'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True, index=True)
    description = db.Column(db.Text, nullable=True)
    contact_person = db.Column(db.String(200), nullable=True)
    email = db.Column(db.String(200), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    address = db.Column(db.Text, nullable=True)
    default_hourly_rate = db.Column(db.Numeric(9, 2), nullable=True)
    status = db.Column(db.String(20), default='active', nullable=False)  # 'active' or 'inactive'
    prepaid_hours_monthly = db.Column(db.Numeric(7, 2), nullable=True)
    prepaid_reset_day = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    projects = db.relationship('Project', backref='client_obj', lazy='dynamic', cascade='all, delete-orphan')
    
    def __init__(self, name, description=None, contact_person=None, email=None, phone=None, address=None, default_hourly_rate=None, company=None, prepaid_hours_monthly=None, prepaid_reset_day=1):
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
        self.prepaid_hours_monthly = Decimal(str(prepaid_hours_monthly)) if prepaid_hours_monthly not in (None, '') else None
        try:
            reset_day = int(prepaid_reset_day) if prepaid_reset_day is not None else 1
            self.prepaid_reset_day = max(1, min(28, reset_day))
        except (TypeError, ValueError):
            self.prepaid_reset_day = 1
    
    def __repr__(self):
        return f'<Client {self.name}>'
    
    @property
    def is_active(self):
        """Check if client is active"""
        return self.status == 'active'
    
    @property
    def total_projects(self):
        """Get total number of projects for this client"""
        return self.projects.count()
    
    @property
    def active_projects(self):
        """Get number of active projects for this client"""
        return self.projects.filter_by(status='active').count()
    
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
            hours = Decimal(str(self.prepaid_hours_monthly)) if self.prepaid_hours_monthly is not None else Decimal('0')
        except Exception:
            hours = Decimal('0')
        return hours > 0

    @property
    def prepaid_hours_decimal(self):
        """Return prepaid hours as Decimal with two decimal precision."""
        if self.prepaid_hours_monthly is None:
            return Decimal('0')
        try:
            return Decimal(str(self.prepaid_hours_monthly)).quantize(Decimal('0.01'))
        except Exception:
            return Decimal('0')

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
        if isinstance(dt, datetime) and hasattr(dt, 'date'):
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
            return Decimal('0')

        try:
            seconds = self.prepaid_consumptions.filter(
                ClientPrepaidConsumption.allocation_month == month_start
            ).with_entities(
                db.func.coalesce(db.func.sum(ClientPrepaidConsumption.seconds_consumed), 0)
            ).scalar() or 0
        except Exception:
            seconds = 0
        return Decimal(seconds) / Decimal('3600')

    def get_prepaid_remaining_hours(self, month_start):
        """Return how many prepaid hours remain for the cycle starting at month_start."""
        if not self.prepaid_plan_enabled or not month_start:
            return Decimal('0')
        consumed = self.get_prepaid_consumed_hours(month_start)
        remaining = self.prepaid_hours_decimal - consumed
        return remaining if remaining > 0 else Decimal('0')
    
    def archive(self):
        """Archive the client"""
        self.status = 'inactive'
        self.updated_at = datetime.utcnow()
    
    def activate(self):
        """Activate the client"""
        self.status = 'active'
        self.updated_at = datetime.utcnow()
    
    def to_dict(self):
        """Convert client to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'contact_person': self.contact_person,
            'email': self.email,
            'phone': self.phone,
            'address': self.address,
            'default_hourly_rate': str(self.default_hourly_rate) if self.default_hourly_rate else None,
            'status': self.status,
            'is_active': self.is_active,
            'total_projects': self.total_projects,
            'active_projects': self.active_projects,
            'prepaid_hours_monthly': float(self.prepaid_hours_monthly) if self.prepaid_hours_monthly is not None else None,
            'prepaid_reset_day': self.prepaid_reset_day,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def get_active_clients(cls):
        """Get all active clients ordered by name"""
        return cls.query.filter_by(status='active').order_by(cls.name).all()
    
    @classmethod
    def get_all_clients(cls):
        """Get all clients ordered by name"""
        return cls.query.order_by(cls.name).all()
