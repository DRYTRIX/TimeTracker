"""Payment gateway integration models"""
from datetime import datetime
from decimal import Decimal
from app import db


class PaymentGateway(db.Model):
    """Payment gateway configuration"""
    
    __tablename__ = 'payment_gateways'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True, index=True)
    # Name: 'stripe', 'paypal', 'square', etc.
    
    provider = db.Column(db.String(50), nullable=False)
    # Provider: 'stripe', 'paypal', 'square'
    
    # Configuration (encrypted JSON)
    # Contains: api_key, secret_key, webhook_secret, etc.
    config = db.Column(db.Text, nullable=False)  # Encrypted
    
    # Status
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    is_test_mode = db.Column(db.Boolean, default=False, nullable=False)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<PaymentGateway {self.name} ({self.provider})>'


class PaymentTransaction(db.Model):
    """Payment transaction from gateway"""
    
    __tablename__ = 'payment_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False, index=True)
    gateway_id = db.Column(db.Integer, db.ForeignKey('payment_gateways.id'), nullable=False, index=True)
    
    # Transaction details
    transaction_id = db.Column(db.String(200), nullable=False, unique=True, index=True)
    # Gateway transaction ID (e.g., Stripe charge ID)
    
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default='EUR')
    
    # Gateway fees
    gateway_fee = db.Column(db.Numeric(10, 2), nullable=True)
    net_amount = db.Column(db.Numeric(10, 2), nullable=True)
    
    # Status
    status = db.Column(db.String(20), nullable=False, index=True)
    # Status: 'pending', 'processing', 'completed', 'failed', 'refunded', 'cancelled'
    
    # Payment method
    payment_method = db.Column(db.String(50), nullable=True)
    # e.g., 'card', 'bank_transfer', 'paypal'
    
    # Gateway response (JSON)
    gateway_response = db.Column(db.JSON, nullable=True)
    
    # Error information
    error_message = db.Column(db.Text, nullable=True)
    error_code = db.Column(db.String(50), nullable=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    processed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    invoice = db.relationship('Invoice', backref='payment_transactions')
    gateway = db.relationship('PaymentGateway', backref='transactions')
    
    def __repr__(self):
        return f'<PaymentTransaction {self.transaction_id} ({self.status})>'
    
    def to_dict(self):
        """Convert transaction to dictionary"""
        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'gateway_id': self.gateway_id,
            'transaction_id': self.transaction_id,
            'amount': float(self.amount) if self.amount else None,
            'currency': self.currency,
            'gateway_fee': float(self.gateway_fee) if self.gateway_fee else None,
            'net_amount': float(self.net_amount) if self.net_amount else None,
            'status': self.status,
            'payment_method': self.payment_method,
            'error_message': self.error_message,
            'error_code': self.error_code,
            'created_at': self.created_at.isoformat(),
            'processed_at': self.processed_at.isoformat() if self.processed_at else None
        }

