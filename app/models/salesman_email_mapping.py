"""
Salesman Email Mapping Model

Maps salesman initials (from client custom fields) to email addresses
for automated report distribution.
"""
from datetime import datetime
from app import db


class SalesmanEmailMapping(db.Model):
    """Maps salesman initials to email addresses for report distribution"""

    __tablename__ = "salesman_email_mappings"

    id = db.Column(db.Integer, primary_key=True)
    salesman_initial = db.Column(db.String(20), nullable=False, unique=True, index=True)
    email_address = db.Column(db.String(255), nullable=True)  # Direct email address
    email_pattern = db.Column(db.String(255), nullable=True)  # Pattern like '{value}@test.de'
    domain = db.Column(db.String(255), nullable=True)  # Domain for pattern-based emails
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __init__(self, salesman_initial, email_address=None, email_pattern=None, domain=None, notes=None):
        """Create a salesman email mapping"""
        self.salesman_initial = salesman_initial.strip().upper()
        self.email_address = email_address.strip() if email_address else None
        self.email_pattern = email_pattern.strip() if email_pattern else None
        self.domain = domain.strip() if domain else None
        self.notes = notes.strip() if notes else None

    def __repr__(self):
        return f"<SalesmanEmailMapping {self.salesman_initial} -> {self.get_email()}>"

    def get_email(self):
        """Get the email address for this salesman initial"""
        if self.email_address:
            return self.email_address
        elif self.email_pattern and self.salesman_initial:
            # Replace {value} with the salesman initial
            return self.email_pattern.replace("{value}", self.salesman_initial)
        elif self.domain and self.salesman_initial:
            # Default pattern: {initial}@domain
            return f"{self.salesman_initial}@{self.domain}"
        return None

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "salesman_initial": self.salesman_initial,
            "email_address": self.email_address,
            "email_pattern": self.email_pattern,
            "domain": self.domain,
            "is_active": self.is_active,
            "notes": self.notes,
            "resolved_email": self.get_email(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def get_email_for_initial(cls, initial):
        """Get email address for a salesman initial"""
        if not initial:
            return None
        
        initial = initial.strip().upper()
        mapping = cls.query.filter_by(salesman_initial=initial, is_active=True).first()
        if mapping:
            return mapping.get_email()
        return None

    @classmethod
    def get_all_active(cls):
        """Get all active mappings"""
        return cls.query.filter_by(is_active=True).order_by(cls.salesman_initial).all()

