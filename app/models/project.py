from datetime import datetime
from decimal import Decimal
from app import db

class Project(db.Model):
    """Project model for client projects with billing information"""
    
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    billable = db.Column(db.Boolean, default=True, nullable=False)
    hourly_rate = db.Column(db.Numeric(9, 2), nullable=True)
    billing_ref = db.Column(db.String(100), nullable=True)
    # Short project code for compact display (e.g., on Kanban cards)
    code = db.Column(db.String(20), nullable=True, unique=True, index=True)
    status = db.Column(db.String(20), default='active', nullable=False)  # 'active', 'inactive', or 'archived'
    # Estimates & budgets
    estimated_hours = db.Column(db.Float, nullable=True)
    budget_amount = db.Column(db.Numeric(10, 2), nullable=True)
    budget_threshold_percent = db.Column(db.Integer, nullable=False, default=80)  # alert when exceeded
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    # Archiving metadata
    archived_at = db.Column(db.DateTime, nullable=True, index=True)
    archived_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    archived_reason = db.Column(db.Text, nullable=True)
    
    # Relationships
    time_entries = db.relationship('TimeEntry', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    tasks = db.relationship('Task', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    costs = db.relationship('ProjectCost', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    extra_goods = db.relationship('ExtraGood', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    # comments relationship is defined via backref in Comment model
    
    def __init__(self, name, client_id=None, description=None, billable=True, hourly_rate=None, billing_ref=None, client=None, budget_amount=None, budget_threshold_percent=80, code=None, created_by=None):
        """Create a Project.

        Backward-compatible initializer that accepts either client_id or client name.
        If client name is provided and client_id is not, the corresponding Client
        record will be found or created on the fly and client_id will be set.
        
        Note: created_by parameter is accepted for test compatibility but not used,
        as the Project model doesn't track creator information.
        """
        from .client import Client  # local import to avoid circular dependencies

        self.name = name.strip()
        self.description = description.strip() if description else None
        self.billable = billable
        self.hourly_rate = Decimal(str(hourly_rate)) if hourly_rate else None
        self.billing_ref = billing_ref.strip() if billing_ref else None
        self.code = code.strip().upper() if code and code.strip() else None
        self.budget_amount = Decimal(str(budget_amount)) if budget_amount else None
        self.budget_threshold_percent = budget_threshold_percent if budget_threshold_percent else 80

        resolved_client_id = client_id
        if resolved_client_id is None and client:
            # Find or create client by name
            client_name = client.strip()
            existing = Client.query.filter_by(name=client_name).first()
            if existing:
                resolved_client_id = existing.id
            else:
                new_client = Client(name=client_name)
                db.session.add(new_client)
                # Flush to obtain id without committing the whole transaction
                try:
                    db.session.flush()
                    resolved_client_id = new_client.id
                except Exception:
                    # If flush fails, fallback to committing
                    db.session.commit()
                    resolved_client_id = new_client.id

        self.client_id = resolved_client_id
    
    def __repr__(self):
        return f'<Project {self.name} ({self.client_obj.name if self.client_obj else "Unknown Client"})>'
    
    @property
    def client(self):
        """Get client name for backward compatibility"""
        return self.client_obj.name if self.client_obj else "Unknown Client"
    
    @property
    def is_active(self):
        """Check if project is active"""
        return self.status == 'active'
    
    @property
    def is_archived(self):
        """Check if project is archived"""
        return self.status == 'archived'
    
    @property
    def archived_by_user(self):
        """Get the user who archived this project"""
        if self.archived_by:
            from .user import User
            return User.query.get(self.archived_by)
        return None

    @property
    def code_display(self):
        """Return configured short code or a fallback derived from project name.

        Fallback: first 4 non-space characters of the project name, uppercased.
        """
        if self.code:
            return self.code
        try:
            base = (self.name or '').replace(' ', '')
            return (base.upper()[:4]) if base else ''
        except Exception:
            return ''
    
    @property
    def total_hours(self):
        """Calculate total hours spent on this project"""
        from .time_entry import TimeEntry
        total_seconds = db.session.query(
            db.func.sum(TimeEntry.duration_seconds)
        ).filter(
            TimeEntry.project_id == self.id,
            TimeEntry.end_time.isnot(None)
        ).scalar() or 0
        return round(total_seconds / 3600, 2)
    
    @property
    def total_billable_hours(self):
        """Calculate total billable hours spent on this project"""
        from .time_entry import TimeEntry
        total_seconds = db.session.query(
            db.func.sum(TimeEntry.duration_seconds)
        ).filter(
            TimeEntry.project_id == self.id,
            TimeEntry.end_time.isnot(None),
            TimeEntry.billable == True
        ).scalar() or 0
        return round(total_seconds / 3600, 2)
    
    @property
    def estimated_cost(self):
        """Calculate estimated cost based on billable hours and hourly rate"""
        if not self.billable or not self.hourly_rate:
            return 0.0
        return float(self.total_billable_hours) * float(self.hourly_rate)
    
    @property
    def total_costs(self):
        """Calculate total project costs (expenses)"""
        from .project_cost import ProjectCost
        total = db.session.query(
            db.func.sum(ProjectCost.amount)
        ).filter(
            ProjectCost.project_id == self.id
        ).scalar() or 0
        return float(total)
    
    @property
    def total_billable_costs(self):
        """Calculate total billable project costs"""
        from .project_cost import ProjectCost
        total = db.session.query(
            db.func.sum(ProjectCost.amount)
        ).filter(
            ProjectCost.project_id == self.id,
            ProjectCost.billable == True
        ).scalar() or 0
        return float(total)
    
    @property
    def total_project_value(self):
        """Calculate total project value (billable hours + billable costs)"""
        return self.estimated_cost + self.total_billable_costs

    @property
    def actual_hours(self):
        """Alias for total hours for clarity in estimates vs actuals."""
        return self.total_hours

    @property
    def budget_consumed_amount(self):
        """Compute consumed budget using effective rate logic when available.

        Falls back to project.hourly_rate if no overrides are present.
        """
        try:
            from .rate_override import RateOverride
            hours = self.total_billable_hours
            # Use project-level override if present, else project rate
            rate = RateOverride.resolve_rate(self, user_id=None)
            return float(hours * float(rate))
        except Exception:
            if self.hourly_rate:
                return float(self.total_billable_hours * float(self.hourly_rate))
            return 0.0

    @property
    def budget_threshold_exceeded(self):
        if not self.budget_amount:
            return False
        try:
            threshold = (self.budget_threshold_percent or 0) / 100.0
            return self.budget_consumed_amount >= float(self.budget_amount) * threshold
        except Exception:
            return False
    
    def get_entries_by_user(self, user_id=None, start_date=None, end_date=None):
        """Get time entries for this project, optionally filtered by user and date range"""
        from .time_entry import TimeEntry
        query = self.time_entries.filter(TimeEntry.end_time.isnot(None))
        
        if user_id:
            query = query.filter(TimeEntry.user_id == user_id)
        
        if start_date:
            query = query.filter(TimeEntry.start_time >= start_date)
        
        if end_date:
            query = query.filter(TimeEntry.start_time <= end_date)
        
        return query.order_by(TimeEntry.start_time.desc()).all()
    
    def get_user_totals(self, start_date=None, end_date=None):
        """Get total hours per user for this project"""
        from .time_entry import TimeEntry
        from .user import User
        
        query = db.session.query(
            User.id,
            User.username,
            User.full_name,
            db.func.sum(TimeEntry.duration_seconds).label('total_seconds')
        ).join(TimeEntry).filter(
            TimeEntry.project_id == self.id,
            TimeEntry.end_time.isnot(None)
        )
        
        if start_date:
            query = query.filter(TimeEntry.start_time >= start_date)
        
        if end_date:
            query = query.filter(TimeEntry.start_time <= end_date)
        
        results = query.group_by(User.id, User.username, User.full_name).all()
        
        return [
            {
                'username': (full_name.strip() if full_name and full_name.strip() else username),
                'total_hours': round(total_seconds / 3600, 2)
            }
            for _id, username, full_name, total_seconds in results
        ]
    
    def archive(self, user_id=None, reason=None):
        """Archive the project with metadata
        
        Args:
            user_id: ID of the user archiving the project
            reason: Optional reason for archiving
        """
        self.status = 'archived'
        self.archived_at = datetime.utcnow()
        self.archived_by = user_id
        self.archived_reason = reason
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def unarchive(self):
        """Unarchive the project and clear archiving metadata"""
        self.status = 'active'
        self.archived_at = None
        self.archived_by = None
        self.archived_reason = None
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def deactivate(self):
        """Mark project as inactive"""
        self.status = 'inactive'
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def activate(self):
        """Activate the project"""
        self.status = 'active'
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def is_favorited_by(self, user):
        """Check if this project is favorited by a specific user"""
        from .user import User
        if isinstance(user, int):
            user_id = user
            return self.favorited_by.filter_by(id=user_id).count() > 0
        elif isinstance(user, User):
            return self.favorited_by.filter_by(id=user.id).count() > 0
        return False
    
    def to_dict(self, user=None):
        """Convert project to dictionary for API responses"""
        data = {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'code_display': self.code_display,
            'client': self.client,
            'description': self.description,
            'billable': self.billable,
            'hourly_rate': float(self.hourly_rate) if self.hourly_rate else None,
            'billing_ref': self.billing_ref,
            'status': self.status,
            'estimated_hours': self.estimated_hours,
            'budget_amount': float(self.budget_amount) if self.budget_amount else None,
            'budget_threshold_percent': self.budget_threshold_percent,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'total_hours': self.total_hours,
            'total_billable_hours': self.total_billable_hours,
            'estimated_cost': float(self.estimated_cost) if self.estimated_cost else None,
            'budget_consumed_amount': self.budget_consumed_amount,
            'budget_threshold_exceeded': self.budget_threshold_exceeded,
            'total_costs': self.total_costs,
            'total_billable_costs': self.total_billable_costs,
            'total_project_value': self.total_project_value,
            # Archiving metadata
            'is_archived': self.is_archived,
            'archived_at': self.archived_at.isoformat() if self.archived_at else None,
            'archived_by': self.archived_by,
            'archived_reason': self.archived_reason,
        }
        # Include favorite status if user is provided
        if user:
            data['is_favorite'] = self.is_favorited_by(user)
        return data
