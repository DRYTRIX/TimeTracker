from datetime import datetime
from decimal import Decimal
from app import db


class Payment(db.Model):
    """Partial/full payments recorded against invoices."""

    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False, index=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=True)  # If multi-currency per payment
    payment_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    method = db.Column(db.String(50), nullable=True)  # bank_transfer, cash, check, credit_card, paypal, stripe, etc.
    reference = db.Column(db.String(100), nullable=True)  # Transaction ID, check number, etc.
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='completed', nullable=False)  # completed, pending, failed, refunded
    
    # Additional tracking fields
    received_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # User who recorded the payment
    gateway_transaction_id = db.Column(db.String(255), nullable=True)  # For payment gateway transactions
    gateway_fee = db.Column(db.Numeric(10, 2), nullable=True)  # Transaction fees
    net_amount = db.Column(db.Numeric(10, 2), nullable=True)  # Amount after fees
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    receiver = db.relationship('User', backref='received_payments', foreign_keys=[received_by])

    def __repr__(self):
        return f"<Payment {self.amount} {self.currency or 'EUR'} for invoice {self.invoice_id}>"
    
    def calculate_net_amount(self):
        """Calculate net amount after fees"""
        if self.gateway_fee:
            self.net_amount = self.amount - self.gateway_fee
        else:
            self.net_amount = self.amount
    
    def to_dict(self):
        """Convert payment to dictionary for API responses"""
        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'amount': float(self.amount),
            'currency': self.currency,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'method': self.method,
            'reference': self.reference,
            'notes': self.notes,
            'status': self.status,
            'received_by': self.received_by,
            'gateway_transaction_id': self.gateway_transaction_id,
            'gateway_fee': float(self.gateway_fee) if self.gateway_fee else None,
            'net_amount': float(self.net_amount) if self.net_amount else float(self.amount),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class CreditNote(db.Model):
    """Credit notes issued to offset invoices."""

    __tablename__ = 'credit_notes'

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False, index=True)
    credit_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    reason = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<CreditNote {self.credit_number} for invoice {self.invoice_id}>"


class InvoiceReminderSchedule(db.Model):
    """Schedules to send invoice reminders before/after due dates."""

    __tablename__ = 'invoice_reminder_schedules'

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False, index=True)
    days_offset = db.Column(db.Integer, nullable=False)  # negative for before due, positive after
    recipients = db.Column(db.Text, nullable=True)  # comma-separated; default to client email if empty
    template_name = db.Column(db.String(100), nullable=True)
    active = db.Column(db.Boolean, default=True, nullable=False)
    last_sent_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<InvoiceReminderSchedule inv={self.invoice_id} offset={self.days_offset}>"


