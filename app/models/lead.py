from datetime import datetime
from decimal import Decimal
from app import db
from app.utils.timezone import now_in_app_timezone

def local_now():
    """Get current time in local timezone as naive datetime (for database storage)"""
    return now_in_app_timezone().replace(tzinfo=None)

class Lead(db.Model):
    """Lead model for managing potential clients"""
    
    __tablename__ = 'leads'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Lead information
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    company_name = db.Column(db.String(200), nullable=True)
    email = db.Column(db.String(200), nullable=True, index=True)
    phone = db.Column(db.String(50), nullable=True)
    
    # Lead details
    title = db.Column(db.String(100), nullable=True)
    source = db.Column(db.String(100), nullable=True)  # 'website', 'referral', 'social', 'ad', etc.
    status = db.Column(db.String(50), nullable=False, default='new', index=True)  # 'new', 'contacted', 'qualified', 'converted', 'lost'
    
    # Lead scoring
    score = db.Column(db.Integer, nullable=True, default=0)  # Lead score (0-100)
    
    # Estimated value
    estimated_value = db.Column(db.Numeric(10, 2), nullable=True)
    currency_code = db.Column(db.String(3), nullable=False, default='EUR')
    
    # Conversion
    converted_to_client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=True, index=True)
    converted_to_deal_id = db.Column(db.Integer, db.ForeignKey('deals.id'), nullable=True, index=True)
    converted_at = db.Column(db.DateTime, nullable=True)
    converted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Notes
    notes = db.Column(db.Text, nullable=True)
    tags = db.Column(db.String(500), nullable=True)  # Comma-separated tags
    
    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)  # Lead owner
    created_at = db.Column(db.DateTime, default=local_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=local_now, onupdate=local_now, nullable=False)
    
    # Relationships
    converted_to_client = db.relationship('Client', foreign_keys=[converted_to_client_id], backref='converted_from_leads')
    converted_to_deal = db.relationship('Deal', foreign_keys=[converted_to_deal_id])
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_leads')
    owner = db.relationship('User', foreign_keys=[owner_id], backref='owned_leads')
    converter = db.relationship('User', foreign_keys=[converted_by], backref='converted_leads')
    activities = db.relationship('LeadActivity', backref='lead', lazy='dynamic', cascade='all, delete-orphan')
    
    def __init__(self, first_name, last_name, created_by, **kwargs):
        self.first_name = first_name.strip()
        self.last_name = last_name.strip()
        self.created_by = created_by
        
        # Set optional fields
        self.company_name = kwargs.get('company_name', '').strip() if kwargs.get('company_name') else None
        self.email = kwargs.get('email', '').strip() if kwargs.get('email') else None
        self.phone = kwargs.get('phone', '').strip() if kwargs.get('phone') else None
        self.title = kwargs.get('title', '').strip() if kwargs.get('title') else None
        self.source = kwargs.get('source', '').strip() if kwargs.get('source') else None
        self.status = kwargs.get('status', 'new').strip()
        self.score = kwargs.get('score', 0)
        self.estimated_value = Decimal(str(kwargs.get('estimated_value'))) if kwargs.get('estimated_value') else None
        self.currency_code = kwargs.get('currency_code', 'EUR')
        self.notes = kwargs.get('notes', '').strip() if kwargs.get('notes') else None
        self.tags = kwargs.get('tags', '').strip() if kwargs.get('tags') else None
        self.owner_id = kwargs.get('owner_id', created_by)  # Default to creator
    
    def __repr__(self):
        return f'<Lead {self.first_name} {self.last_name}>'
    
    @property
    def full_name(self):
        """Get full name of lead"""
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def display_name(self):
        """Get display name with company if available"""
        if self.company_name:
            return f"{self.full_name} ({self.company_name})"
        return self.full_name
    
    @property
    def is_converted(self):
        """Check if lead has been converted"""
        return self.converted_to_client_id is not None or self.converted_to_deal_id is not None
    
    @property
    def is_lost(self):
        """Check if lead is lost"""
        return self.status == 'lost'
    
    def convert_to_client(self, client_id, user_id):
        """Convert lead to client"""
        self.converted_to_client_id = client_id
        self.status = 'converted'
        self.converted_at = local_now()
        self.converted_by = user_id
        self.updated_at = local_now()
    
    def convert_to_deal(self, deal_id, user_id):
        """Convert lead to deal"""
        self.converted_to_deal_id = deal_id
        self.status = 'converted'
        self.converted_at = local_now()
        self.converted_by = user_id
        self.updated_at = local_now()
    
    def mark_lost(self):
        """Mark lead as lost"""
        self.status = 'lost'
        self.updated_at = local_now()
    
    def to_dict(self):
        """Convert lead to dictionary"""
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'display_name': self.display_name,
            'company_name': self.company_name,
            'email': self.email,
            'phone': self.phone,
            'title': self.title,
            'source': self.source,
            'status': self.status,
            'score': self.score,
            'estimated_value': float(self.estimated_value) if self.estimated_value else None,
            'currency_code': self.currency_code,
            'converted_to_client_id': self.converted_to_client_id,
            'converted_to_deal_id': self.converted_to_deal_id,
            'converted_at': self.converted_at.isoformat() if self.converted_at else None,
            'converted_by': self.converted_by,
            'notes': self.notes,
            'tags': self.tags.split(',') if self.tags else [],
            'created_by': self.created_by,
            'owner_id': self.owner_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_converted': self.is_converted,
            'is_lost': self.is_lost
        }
    
    @classmethod
    def get_active_leads(cls, user_id=None):
        """Get active (non-converted, non-lost) leads, optionally filtered by owner"""
        query = cls.query.filter(~cls.status.in_(['converted', 'lost']))
        if user_id:
            query = query.filter_by(owner_id=user_id)
        return query.order_by(cls.score.desc(), cls.created_at.desc()).all()
    
    @classmethod
    def get_leads_by_status(cls, status):
        """Get leads by status"""
        return cls.query.filter_by(status=status).order_by(cls.score.desc(), cls.created_at.desc()).all()

