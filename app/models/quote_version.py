from datetime import datetime
from app import db
from app.utils.timezone import now_in_app_timezone
import json

def local_now():
    """Get current time in local timezone as naive datetime (for database storage)"""
    return now_in_app_timezone().replace(tzinfo=None)


class QuoteVersion(db.Model):
    """Model for tracking quote version history"""
    
    __tablename__ = 'quote_versions'
    
    id = db.Column(db.Integer, primary_key=True)
    quote_id = db.Column(db.Integer, db.ForeignKey('quotes.id', ondelete='CASCADE'), nullable=False, index=True)
    version_number = db.Column(db.Integer, nullable=False)  # 1, 2, 3, etc.
    
    # Snapshot of quote data at this version (stored as JSON)
    quote_data = db.Column(db.Text, nullable=False)  # JSON string with complete quote state
    
    # Change information
    changed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    changed_at = db.Column(db.DateTime, default=local_now, nullable=False)
    change_summary = db.Column(db.String(500), nullable=True)  # Brief description of changes
    
    # What changed (for quick reference)
    fields_changed = db.Column(db.String(500), nullable=True)  # Comma-separated list of changed fields
    
    # Relationships
    quote = db.relationship('Quote', backref='versions')
    changer = db.relationship('User', foreign_keys=[changed_by], backref='quote_version_changes')
    
    def __init__(self, quote_id, version_number, quote_data, changed_by, **kwargs):
        self.quote_id = quote_id
        self.version_number = version_number
        self.quote_data = quote_data if isinstance(quote_data, str) else json.dumps(quote_data)
        self.changed_by = changed_by
        self.change_summary = kwargs.get('change_summary', '').strip() if kwargs.get('change_summary') else None
        self.fields_changed = kwargs.get('fields_changed', '').strip() if kwargs.get('fields_changed') else None
    
    def __repr__(self):
        return f'<QuoteVersion {self.version_number} for Quote {self.quote_id}>'
    
    @property
    def data_dict(self):
        """Get quote data as a dictionary"""
        try:
            return json.loads(self.quote_data)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def to_dict(self):
        """Convert version to dictionary for API responses"""
        return {
            'id': self.id,
            'quote_id': self.quote_id,
            'version_number': self.version_number,
            'quote_data': self.data_dict,
            'changed_by': self.changed_by,
            'changer': self.changer.username if self.changer else None,
            'changed_at': self.changed_at.isoformat() if self.changed_at else None,
            'change_summary': self.change_summary,
            'fields_changed': self.fields_changed.split(',') if self.fields_changed else []
        }
    
    @classmethod
    def create_version(cls, quote, changed_by, change_summary=None, fields_changed=None):
        """Create a new version snapshot of a quote"""
        # Get current version number
        last_version = cls.query.filter_by(quote_id=quote.id).order_by(cls.version_number.desc()).first()
        version_number = (last_version.version_number + 1) if last_version else 1
        
        # Create snapshot of quote data
        quote_data = {
            'title': quote.title,
            'description': quote.description,
            'status': quote.status,
            'subtotal': float(quote.subtotal),
            'tax_rate': float(quote.tax_rate),
            'tax_amount': float(quote.tax_amount),
            'total_amount': float(quote.total_amount),
            'currency_code': quote.currency_code,
            'discount_type': quote.discount_type,
            'discount_amount': float(quote.discount_amount) if quote.discount_amount else None,
            'discount_reason': quote.discount_reason,
            'coupon_code': quote.coupon_code,
            'payment_terms': quote.payment_terms,
            'valid_until': quote.valid_until.isoformat() if quote.valid_until else None,
            'notes': quote.notes,
            'terms': quote.terms,
            'visible_to_client': quote.visible_to_client,
            'requires_approval': quote.requires_approval,
            'approval_status': quote.approval_status,
            'items': [{
                'description': item.description,
                'quantity': float(item.quantity),
                'unit_price': float(item.unit_price),
                'unit': item.unit
            } for item in quote.items]
        }
        
        version = cls(
            quote_id=quote.id,
            version_number=version_number,
            quote_data=json.dumps(quote_data),
            changed_by=changed_by,
            change_summary=change_summary,
            fields_changed=','.join(fields_changed) if fields_changed else None
        )
        
        db.session.add(version)
        return version
    
    @classmethod
    def get_quote_versions(cls, quote_id):
        """Get all versions for a quote"""
        return cls.query.filter_by(quote_id=quote_id).order_by(cls.version_number.desc()).all()
    
    @classmethod
    def get_latest_version(cls, quote_id):
        """Get the latest version of a quote"""
        return cls.query.filter_by(quote_id=quote_id).order_by(cls.version_number.desc()).first()

