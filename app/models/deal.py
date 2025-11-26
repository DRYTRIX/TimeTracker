from datetime import datetime
from decimal import Decimal
from app import db
from app.utils.timezone import now_in_app_timezone

def local_now():
    """Get current time in local timezone as naive datetime (for database storage)"""
    return now_in_app_timezone().replace(tzinfo=None)

class Deal(db.Model):
    """Deal/Opportunity model for sales pipeline management"""
    
    __tablename__ = 'deals'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=True, index=True)  # Can be null for leads
    contact_id = db.Column(db.Integer, db.ForeignKey('contacts.id'), nullable=True, index=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=True, index=True)  # If converted from lead
    
    # Deal information
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Pipeline stage
    stage = db.Column(db.String(50), nullable=False, default='prospecting', index=True)
    # Common stages: 'prospecting', 'qualification', 'proposal', 'negotiation', 'closed_won', 'closed_lost'
    
    # Financial details
    value = db.Column(db.Numeric(10, 2), nullable=True)  # Deal value
    currency_code = db.Column(db.String(3), nullable=False, default='EUR')
    probability = db.Column(db.Integer, nullable=True, default=50)  # Win probability (0-100)
    expected_close_date = db.Column(db.Date, nullable=True, index=True)
    actual_close_date = db.Column(db.Date, nullable=True)
    
    # Status
    status = db.Column(db.String(20), default='open', nullable=False)  # 'open', 'won', 'lost', 'cancelled'
    
    # Loss reason (if lost)
    loss_reason = db.Column(db.String(500), nullable=True)
    
    # Related entities
    related_quote_id = db.Column(db.Integer, db.ForeignKey('quotes.id'), nullable=True, index=True)
    related_project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True, index=True)
    
    # Notes
    notes = db.Column(db.Text, nullable=True)
    
    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)  # Deal owner
    created_at = db.Column(db.DateTime, default=local_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=local_now, onupdate=local_now, nullable=False)
    closed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    client = db.relationship('Client', backref='deals')
    contact = db.relationship('Contact', backref='deals')
    lead = db.relationship('Lead', foreign_keys=[lead_id], backref='deals')
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_deals')
    owner = db.relationship('User', foreign_keys=[owner_id], backref='owned_deals')
    related_quote = db.relationship('Quote', foreign_keys=[related_quote_id])
    related_project = db.relationship('Project', foreign_keys=[related_project_id])
    activities = db.relationship('DealActivity', backref='deal', lazy='dynamic', cascade='all, delete-orphan')
    
    def __init__(self, name, created_by, **kwargs):
        self.name = name.strip()
        self.created_by = created_by
        
        # Set optional fields
        self.client_id = kwargs.get('client_id')
        self.contact_id = kwargs.get('contact_id')
        self.lead_id = kwargs.get('lead_id')
        self.description = kwargs.get('description', '').strip() if kwargs.get('description') else None
        self.stage = kwargs.get('stage', 'prospecting').strip()
        self.value = Decimal(str(kwargs.get('value'))) if kwargs.get('value') else None
        self.currency_code = kwargs.get('currency_code', 'EUR')
        self.probability = kwargs.get('probability', 50)
        self.expected_close_date = kwargs.get('expected_close_date')
        self.status = kwargs.get('status', 'open').strip()
        self.loss_reason = kwargs.get('loss_reason', '').strip() if kwargs.get('loss_reason') else None
        self.related_quote_id = kwargs.get('related_quote_id')
        self.related_project_id = kwargs.get('related_project_id')
        self.notes = kwargs.get('notes', '').strip() if kwargs.get('notes') else None
        self.owner_id = kwargs.get('owner_id', created_by)  # Default to creator
    
    def __repr__(self):
        return f'<Deal {self.name} ({self.stage})>'
    
    @property
    def weighted_value(self):
        """Calculate probability-weighted value"""
        if not self.value:
            return Decimal('0')
        return self.value * (Decimal(str(self.probability)) / 100)
    
    @property
    def is_open(self):
        """Check if deal is still open"""
        return self.status == 'open'
    
    @property
    def is_won(self):
        """Check if deal is won"""
        return self.status == 'won'
    
    @property
    def is_lost(self):
        """Check if deal is lost"""
        return self.status == 'lost'
    
    def close_won(self, close_date=None):
        """Mark deal as won"""
        self.status = 'won'
        self.stage = 'closed_won'
        self.actual_close_date = close_date or local_now().date()
        self.closed_at = local_now()
        self.updated_at = local_now()
    
    def close_lost(self, reason=None, close_date=None):
        """Mark deal as lost"""
        self.status = 'lost'
        self.stage = 'closed_lost'
        self.actual_close_date = close_date or local_now().date()
        self.closed_at = local_now()
        if reason:
            self.loss_reason = reason
        self.updated_at = local_now()
    
    def to_dict(self):
        """Convert deal to dictionary"""
        return {
            'id': self.id,
            'client_id': self.client_id,
            'contact_id': self.contact_id,
            'lead_id': self.lead_id,
            'name': self.name,
            'description': self.description,
            'stage': self.stage,
            'value': float(self.value) if self.value else None,
            'currency_code': self.currency_code,
            'probability': self.probability,
            'weighted_value': float(self.weighted_value),
            'expected_close_date': self.expected_close_date.isoformat() if self.expected_close_date else None,
            'actual_close_date': self.actual_close_date.isoformat() if self.actual_close_date else None,
            'status': self.status,
            'loss_reason': self.loss_reason,
            'related_quote_id': self.related_quote_id,
            'related_project_id': self.related_project_id,
            'notes': self.notes,
            'created_by': self.created_by,
            'owner_id': self.owner_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'is_open': self.is_open,
            'is_won': self.is_won,
            'is_lost': self.is_lost
        }
    
    @classmethod
    def get_open_deals(cls, user_id=None):
        """Get open deals, optionally filtered by owner"""
        query = cls.query.filter_by(status='open')
        if user_id:
            query = query.filter_by(owner_id=user_id)
        return query.order_by(cls.expected_close_date, cls.created_at.desc()).all()
    
    @classmethod
    def get_deals_by_stage(cls, stage):
        """Get deals by pipeline stage"""
        return cls.query.filter_by(stage=stage, status='open').order_by(cls.expected_close_date).all()

