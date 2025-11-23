"""Warehouse model for inventory management"""
from datetime import datetime
from app import db


class Warehouse(db.Model):
    """Warehouse model - represents a storage location"""
    
    __tablename__ = 'warehouses'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    address = db.Column(db.Text, nullable=True)
    contact_person = db.Column(db.String(200), nullable=True)
    contact_email = db.Column(db.String(200), nullable=True)
    contact_phone = db.Column(db.String(50), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Relationships
    stock_levels = db.relationship('WarehouseStock', backref='warehouse', lazy='dynamic', cascade='all, delete-orphan')
    stock_movements = db.relationship('StockMovement', backref='warehouse', lazy='dynamic', cascade='all, delete-orphan')
    
    def __init__(self, name, code, created_by, address=None, contact_person=None, 
                 contact_email=None, contact_phone=None, is_active=True, notes=None):
        self.name = name.strip()
        self.code = code.strip().upper()
        self.created_by = created_by
        self.address = address.strip() if address else None
        self.contact_person = contact_person.strip() if contact_person else None
        self.contact_email = contact_email.strip() if contact_email else None
        self.contact_phone = contact_phone.strip() if contact_phone else None
        self.is_active = is_active
        self.notes = notes.strip() if notes else None
    
    def __repr__(self):
        return f'<Warehouse {self.code} ({self.name})>'
    
    def to_dict(self):
        """Convert warehouse to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'address': self.address,
            'contact_person': self.contact_person,
            'contact_email': self.contact_email,
            'contact_phone': self.contact_phone,
            'is_active': self.is_active,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by
        }

