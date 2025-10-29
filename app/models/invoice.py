from datetime import datetime
from decimal import Decimal
from app import db

class Invoice(db.Model):
    """Invoice model for client billing"""
    
    __tablename__ = 'invoices'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, index=True)
    client_name = db.Column(db.String(200), nullable=False)
    client_email = db.Column(db.String(200), nullable=True)
    client_address = db.Column(db.Text, nullable=True)
    # Link to clients table (enforced by DB schema)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False, index=True)
    
    # Invoice details
    issue_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='draft', nullable=False)  # 'draft', 'sent', 'paid', 'overdue', 'cancelled'
    
    # Billing information
    subtotal = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    tax_rate = db.Column(db.Numeric(5, 2), nullable=False, default=0)  # Percentage
    tax_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    currency_code = db.Column(db.String(3), nullable=False, default='EUR')
    template_id = db.Column(db.Integer, db.ForeignKey('invoice_templates.id'), nullable=True, index=True)
    
    # Notes and terms
    notes = db.Column(db.Text, nullable=True)
    terms = db.Column(db.Text, nullable=True)
    
    # Payment tracking
    payment_date = db.Column(db.Date, nullable=True)
    payment_method = db.Column(db.String(50), nullable=True)  # 'cash', 'check', 'bank_transfer', 'credit_card', 'paypal', etc.
    payment_reference = db.Column(db.String(100), nullable=True)  # Transaction ID, check number, etc.
    payment_notes = db.Column(db.Text, nullable=True)
    amount_paid = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    payment_status = db.Column(db.String(20), nullable=False, default='unpaid')  # 'unpaid', 'partially_paid', 'fully_paid', 'overpaid'
    
    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    project = db.relationship('Project', backref='invoices')
    client = db.relationship('Client', backref='invoices')
    creator = db.relationship('User', backref='created_invoices')
    items = db.relationship('InvoiceItem', backref='invoice', lazy='dynamic', cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='invoice', lazy='dynamic', cascade='all, delete-orphan')
    credits = db.relationship('CreditNote', backref='invoice', lazy='dynamic', cascade='all, delete-orphan')
    reminder_schedules = db.relationship('InvoiceReminderSchedule', backref='invoice', lazy='dynamic', cascade='all, delete-orphan')
    template = db.relationship('InvoiceTemplate', backref='invoices', lazy='joined')
    extra_goods = db.relationship('ExtraGood', backref='invoice', lazy='dynamic', cascade='all, delete-orphan')
    
    def __init__(self, invoice_number, project_id, client_name, due_date, created_by, client_id, **kwargs):
        self.invoice_number = invoice_number
        self.project_id = project_id
        self.client_name = client_name
        self.due_date = due_date
        self.created_by = created_by
        self.client_id = client_id
        
        # Set optional fields
        self.client_email = kwargs.get('client_email')
        self.client_address = kwargs.get('client_address')
        self.issue_date = kwargs.get('issue_date', datetime.utcnow().date())
        self.notes = kwargs.get('notes')
        self.terms = kwargs.get('terms')
        self.tax_rate = Decimal(str(kwargs.get('tax_rate', 0)))
        self.currency_code = kwargs.get('currency_code') or self.currency_code
        self.template_id = kwargs.get('template_id') if kwargs.get('template_id') else None
        
        # Set payment tracking fields
        self.payment_date = kwargs.get('payment_date')
        self.payment_method = kwargs.get('payment_method')
        self.payment_reference = kwargs.get('payment_reference')
        self.payment_notes = kwargs.get('payment_notes')
        self.amount_paid = Decimal(str(kwargs.get('amount_paid', 0)))
        self.payment_status = kwargs.get('payment_status', 'unpaid')
    
    def __repr__(self):
        return f'<Invoice {self.invoice_number} ({self.client_name})>'
    
    @property
    def is_overdue(self):
        """Check if invoice is overdue"""
        return self.status in ['sent', 'overdue'] and datetime.utcnow().date() > self.due_date
    
    @property
    def days_overdue(self):
        """Calculate days overdue"""
        if not self.is_overdue:
            return 0
        return (datetime.utcnow().date() - self.due_date).days
    
    @property
    def is_paid(self):
        """Check if invoice is fully paid"""
        return self.payment_status == 'fully_paid'
    
    @property
    def is_partially_paid(self):
        """Check if invoice is partially paid"""
        return self.payment_status == 'partially_paid'
    
    @property
    def outstanding_amount(self):
        """Calculate outstanding amount"""
        credits_total = sum((c.amount for c in self.credits), Decimal('0')) if self.credits else Decimal('0')
        return self.total_amount - (self.amount_paid or 0) - credits_total
    
    @property
    def payment_percentage(self):
        """Calculate payment percentage"""
        if self.total_amount == 0:
            return 0
        return float((self.amount_paid or 0) / self.total_amount * 100)
    
    @property
    def sorted_payments(self):
        """Get payments sorted by payment_date and created_at (newest first)"""
        from app.models.payments import Payment
        return self.payments.order_by(Payment.payment_date.desc(), Payment.created_at.desc()).all()
    
    def update_payment_status(self):
        """Update payment status based on amount paid"""
        if not self.amount_paid or self.amount_paid == 0:
            self.payment_status = 'unpaid'
        elif self.amount_paid >= self.total_amount:
            if self.amount_paid > self.total_amount:
                self.payment_status = 'overpaid'
            else:
                self.payment_status = 'fully_paid'
        else:
            self.payment_status = 'partially_paid'
    
    def record_payment(self, amount, payment_date=None, payment_method=None, payment_reference=None, payment_notes=None):
        """
        DEPRECATED: Record a payment for this invoice.
        
        This method is deprecated. Please use the Payment model (app.models.Payment)
        to record payments instead. The Payment model provides:
        - Multiple payment tracking per invoice
        - Payment status management (completed, pending, failed, refunded)
        - Gateway fee tracking
        - Better audit trail
        
        This method is kept for backwards compatibility only and may be removed in a future version.
        """
        import warnings
        warnings.warn(
            "Invoice.record_payment() is deprecated. Use the Payment model instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        self.amount_paid = (self.amount_paid or 0) + Decimal(str(amount))
        self.payment_date = payment_date or datetime.utcnow().date()
        if payment_method:
            self.payment_method = payment_method
        if payment_reference:
            self.payment_reference = payment_reference
        if payment_notes:
            self.payment_notes = payment_notes
        
        self.update_payment_status()
        
        # Update invoice status based on payment
        if self.payment_status == 'fully_paid':
            self.status = 'paid'
        elif self.payment_status in ['partially_paid', 'overpaid']:
            # Keep current status but ensure it's not 'paid' if only partially paid
            if self.payment_status == 'partially_paid' and self.status == 'paid':
                self.status = 'sent'
    
    def calculate_totals(self):
        """Calculate invoice totals from items and extra goods"""
        # Optionally apply tax rules before totals
        try:
            self._apply_tax_rules_if_any()
        except Exception:
            pass
        items_total = sum(item.total_amount for item in self.items)
        goods_total = sum(good.total_amount for good in self.extra_goods)
        subtotal = items_total + goods_total
        self.subtotal = subtotal
        self.tax_amount = subtotal * (self.tax_rate / 100)
        self.total_amount = subtotal + self.tax_amount
        
        # Update status if overdue
        if self.status == 'sent' and self.is_overdue:
            self.status = 'overdue'

    def _apply_tax_rules_if_any(self):
        """Apply matching tax rule to set `tax_rate` if applicable.
        Chooses the most specific active rule by client->project->country/region.
        """
        try:
            from .tax_rule import TaxRule  # local import to avoid circular
            today = self.issue_date or datetime.utcnow().date()
            query = TaxRule.query.filter(TaxRule.active == True)
            # constrain by date range
            query = query.filter(
                (TaxRule.start_date.is_(None) | (TaxRule.start_date <= today)),
                (TaxRule.end_date.is_(None) | (TaxRule.end_date >= today)),
            )
            candidates = []
            # project-specific
            if self.project_id:
                candidates = query.filter(TaxRule.project_id == self.project_id).all()
            # client-specific
            if not candidates and self.client_id:
                candidates = query.filter(TaxRule.client_id == self.client_id).all()
            # no direct client/project, fallback to country/region — requires client meta; skip if unavailable
            # choose first if any
            if candidates:
                # prefer highest rate if multiple
                candidates.sort(key=lambda r: float(r.rate_percent), reverse=True)
                self.tax_rate = Decimal(str(candidates[0].rate_percent))
        except Exception:
            # Best-effort only
            pass
    
    def to_dict(self):
        """Convert invoice to dictionary for API responses"""
        return {
            'id': self.id,
            'invoice_number': self.invoice_number,
            'project_id': self.project_id,
            'client_name': self.client_name,
            'client_email': self.client_email,
            'client_address': self.client_address,
            'client_id': self.client_id,
            'issue_date': self.issue_date.isoformat() if self.issue_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'status': self.status,
            'subtotal': float(self.subtotal),
            'tax_rate': float(self.tax_rate),
            'tax_amount': float(self.tax_amount),
            'total_amount': float(self.total_amount),
            'notes': self.notes,
            'terms': self.terms,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_overdue': self.is_overdue,
            'days_overdue': self.days_overdue,
            # Payment tracking fields
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'payment_method': self.payment_method,
            'payment_reference': self.payment_reference,
            'payment_notes': self.payment_notes,
            'amount_paid': float(self.amount_paid) if self.amount_paid else 0,
            'payment_status': self.payment_status,
            'is_paid': self.is_paid,
            'is_partially_paid': self.is_partially_paid,
            'outstanding_amount': float(self.outstanding_amount),
            'payment_percentage': self.payment_percentage
        }
    
    @classmethod
    def generate_invoice_number(cls):
        """Generate a unique invoice number"""
        from datetime import datetime
        
        # Format: INV-YYYYMMDD-XXX
        today = datetime.utcnow()
        date_prefix = today.strftime('%Y%m%d')
        
        # Find the next available number for today
        existing = cls.query.filter(
            cls.invoice_number.like(f'INV-{date_prefix}-%')
        ).order_by(cls.invoice_number.desc()).first()
        
        if existing:
            # Extract the number part and increment
            try:
                last_num = int(existing.invoice_number.split('-')[-1])
                next_num = last_num + 1
            except (ValueError, IndexError):
                next_num = 1
        else:
            next_num = 1
        
        return f'INV-{date_prefix}-{next_num:03d}'


class InvoiceItem(db.Model):
    """Invoice line item model"""
    
    __tablename__ = 'invoice_items'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False, index=True)
    
    # Item details
    description = db.Column(db.String(500), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), nullable=False, default=1)  # Hours
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)  # Hourly rate
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Time entry reference (optional)
    time_entry_ids = db.Column(db.String(500), nullable=True)  # Comma-separated IDs
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __init__(self, invoice_id, description, quantity, unit_price, time_entry_ids=None):
        self.invoice_id = invoice_id
        self.description = description
        self.quantity = Decimal(str(quantity))
        self.unit_price = Decimal(str(unit_price))
        self.total_amount = self.quantity * self.unit_price
        self.time_entry_ids = time_entry_ids
    
    def __repr__(self):
        return f'<InvoiceItem {self.description} ({self.quantity}h @ {self.unit_price})>'
    
    def to_dict(self):
        """Convert invoice item to dictionary"""
        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'description': self.description,
            'quantity': float(self.quantity),
            'unit_price': float(self.unit_price),
            'total_amount': float(self.total_amount),
            'time_entry_ids': self.time_entry_ids,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
