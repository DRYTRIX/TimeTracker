"""Supplier model for inventory management"""
from datetime import datetime
from app import db


class Supplier(db.Model):
    """Supplier model - represents a supplier/vendor"""
    
    __tablename__ = 'suppliers'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    contact_person = db.Column(db.String(200), nullable=True)
    email = db.Column(db.String(200), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    address = db.Column(db.Text, nullable=True)
    website = db.Column(db.String(500), nullable=True)
    tax_id = db.Column(db.String(100), nullable=True)
    payment_terms = db.Column(db.String(100), nullable=True)  # e.g., "Net 30", "Net 60"
    currency_code = db.Column(db.String(3), nullable=False, default='EUR')
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Relationships
    supplier_items = db.relationship('SupplierStockItem', backref='supplier', lazy='dynamic', cascade='all, delete-orphan')
    
    def __init__(self, code, name, created_by, description=None, contact_person=None,
                 email=None, phone=None, address=None, website=None, tax_id=None,
                 payment_terms=None, currency_code='EUR', is_active=True, notes=None):
        self.code = code.strip().upper()
        self.name = name.strip()
        self.created_by = created_by
        self.description = description.strip() if description else None
        self.contact_person = contact_person.strip() if contact_person else None
        self.email = email.strip() if email else None
        self.phone = phone.strip() if phone else None
        self.address = address.strip() if address else None
        self.website = website.strip() if website else None
        self.tax_id = tax_id.strip() if tax_id else None
        self.payment_terms = payment_terms.strip() if payment_terms else None
        self.currency_code = currency_code.upper()
        self.is_active = is_active
        self.notes = notes.strip() if notes else None
    
    def __repr__(self):
        return f'<Supplier {self.code} ({self.name})>'
    
    def to_dict(self):
        """Convert supplier to dictionary"""
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'contact_person': self.contact_person,
            'email': self.email,
            'phone': self.phone,
            'address': self.address,
            'website': self.website,
            'tax_id': self.tax_id,
            'payment_terms': self.payment_terms,
            'currency_code': self.currency_code,
            'is_active': self.is_active,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by
        }

