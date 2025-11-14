from datetime import datetime
from app import db
from app.utils.timezone import now_in_app_timezone


def local_now():
    """Get current time in local timezone as naive datetime (for database storage)"""
    return now_in_app_timezone().replace(tzinfo=None)


class InvoiceEmail(db.Model):
    """Model for tracking invoice emails sent to clients"""
    
    __tablename__ = 'invoice_emails'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False, index=True)
    
    # Email details
    recipient_email = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(500), nullable=False)
    sent_at = db.Column(db.DateTime, nullable=False, default=local_now)
    sent_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Tracking
    opened_at = db.Column(db.DateTime, nullable=True)  # When email was opened (if tracked)
    opened_count = db.Column(db.Integer, nullable=False, default=0)  # Number of times opened
    last_opened_at = db.Column(db.DateTime, nullable=True)  # Last time email was opened
    
    # Payment tracking
    paid_at = db.Column(db.DateTime, nullable=True)  # When invoice was marked as paid (if after email)
    
    # Status
    status = db.Column(db.String(20), nullable=False, default='sent')  # 'sent', 'opened', 'paid', 'bounced', 'failed'
    
    # Error tracking
    error_message = db.Column(db.Text, nullable=True)  # Error message if send failed
    
    # Metadata
    created_at = db.Column(db.DateTime, default=local_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=local_now, onupdate=local_now, nullable=False)
    
    # Relationships
    invoice = db.relationship('Invoice', backref='email_records')
    sender = db.relationship('User', backref='sent_invoice_emails')
    
    def __init__(self, invoice_id, recipient_email, subject, sent_by, **kwargs):
        self.invoice_id = invoice_id
        self.recipient_email = recipient_email
        self.subject = subject
        self.sent_by = sent_by
        self.status = kwargs.get('status', 'sent')
        self.error_message = kwargs.get('error_message')
    
    def __repr__(self):
        return f'<InvoiceEmail {self.invoice_id} -> {self.recipient_email} ({self.status})>'
    
    def mark_opened(self):
        """Mark email as opened"""
        if not self.opened_at:
            self.opened_at = local_now()
        self.last_opened_at = local_now()
        self.opened_count += 1
        if self.status == 'sent':
            self.status = 'opened'
    
    def mark_paid(self):
        """Mark invoice as paid (after email was sent)"""
        if not self.paid_at:
            self.paid_at = local_now()
        self.status = 'paid'
    
    def mark_failed(self, error_message):
        """Mark email send as failed"""
        self.status = 'failed'
        self.error_message = error_message
    
    def mark_bounced(self):
        """Mark email as bounced"""
        self.status = 'bounced'
    
    def to_dict(self):
        """Convert invoice email to dictionary"""
        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'recipient_email': self.recipient_email,
            'subject': self.subject,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'sent_by': self.sent_by,
            'opened_at': self.opened_at.isoformat() if self.opened_at else None,
            'opened_count': self.opened_count,
            'last_opened_at': self.last_opened_at.isoformat() if self.last_opened_at else None,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
            'status': self.status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

