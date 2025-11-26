from datetime import datetime
from app import db
from app.utils.timezone import now_in_app_timezone

def local_now():
    """Get current time in local timezone as naive datetime (for database storage)"""
    return now_in_app_timezone().replace(tzinfo=None)

class ContactCommunication(db.Model):
    """Model for tracking communications with contacts"""
    
    __tablename__ = 'contact_communications'
    
    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey('contacts.id'), nullable=False, index=True)
    
    # Communication details
    type = db.Column(db.String(50), nullable=False)  # 'email', 'call', 'meeting', 'note', 'message'
    subject = db.Column(db.String(500), nullable=True)
    content = db.Column(db.Text, nullable=True)
    
    # Direction
    direction = db.Column(db.String(20), nullable=False, default='outbound')  # 'inbound', 'outbound'
    
    # Dates
    communication_date = db.Column(db.DateTime, nullable=False, default=local_now, index=True)
    follow_up_date = db.Column(db.DateTime, nullable=True)  # When to follow up
    
    # Status
    status = db.Column(db.String(50), nullable=True)  # 'completed', 'pending', 'scheduled', 'cancelled'
    
    # Related entities
    related_project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True, index=True)
    related_quote_id = db.Column(db.Integer, db.ForeignKey('quotes.id'), nullable=True, index=True)
    related_deal_id = db.Column(db.Integer, db.ForeignKey('deals.id'), nullable=True, index=True)
    
    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=local_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=local_now, onupdate=local_now, nullable=False)
    
    # Relationships
    # Note: 'contact' backref is created by Contact.communications relationship
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_communications')
    related_project = db.relationship('Project', foreign_keys=[related_project_id])
    related_quote = db.relationship('Quote', foreign_keys=[related_quote_id])
    related_deal = db.relationship('Deal', foreign_keys=[related_deal_id])
    
    def __init__(self, contact_id, type, created_by, **kwargs):
        self.contact_id = contact_id
        self.type = type.strip()
        self.created_by = created_by
        
        # Set optional fields
        self.subject = kwargs.get('subject', '').strip() if kwargs.get('subject') else None
        self.content = kwargs.get('content', '').strip() if kwargs.get('content') else None
        self.direction = kwargs.get('direction', 'outbound').strip()
        self.status = kwargs.get('status', 'completed').strip() if kwargs.get('status') else None
        self.communication_date = kwargs.get('communication_date') or local_now()
        self.follow_up_date = kwargs.get('follow_up_date')
        self.related_project_id = kwargs.get('related_project_id')
        self.related_quote_id = kwargs.get('related_quote_id')
        self.related_deal_id = kwargs.get('related_deal_id')
    
    def __repr__(self):
        return f'<ContactCommunication {self.type} with {self.contact.full_name if self.contact else "Unknown"}>'
    
    def to_dict(self):
        """Convert communication to dictionary"""
        return {
            'id': self.id,
            'contact_id': self.contact_id,
            'type': self.type,
            'subject': self.subject,
            'content': self.content,
            'direction': self.direction,
            'status': self.status,
            'communication_date': self.communication_date.isoformat() if self.communication_date else None,
            'follow_up_date': self.follow_up_date.isoformat() if self.follow_up_date else None,
            'related_project_id': self.related_project_id,
            'related_quote_id': self.related_quote_id,
            'related_deal_id': self.related_deal_id,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def get_recent_communications(cls, contact_id=None, limit=50):
        """Get recent communications, optionally filtered by contact"""
        query = cls.query
        if contact_id:
            query = query.filter_by(contact_id=contact_id)
        return query.order_by(cls.communication_date.desc()).limit(limit).all()

