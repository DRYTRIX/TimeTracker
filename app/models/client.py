from datetime import datetime
from decimal import Decimal
from app import db

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    projects = db.relationship('Project', backref='client_obj', lazy='dynamic', cascade='all, delete-orphan')
    
    def __init__(self, name, description=None, contact_person=None, email=None, phone=None, address=None, default_hourly_rate=None):
        self.name = name.strip()
        self.description = description.strip() if description else None
        self.contact_person = contact_person.strip() if contact_person else None
        self.email = email.strip() if email else None
        self.phone = phone.strip() if phone else None
        self.address = address.strip() if address else None
        self.default_hourly_rate = Decimal(str(default_hourly_rate)) if default_hourly_rate else None
    
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
