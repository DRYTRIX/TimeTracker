from datetime import datetime
from decimal import Decimal
from sqlalchemy import and_
from app import db
from app.utils.timezone import now_in_app_timezone

def local_now():
    """Get current time in local timezone as naive datetime (for database storage)"""
    return now_in_app_timezone().replace(tzinfo=None)

class Quote(db.Model):
    """Quote model for managing client quotes that can be accepted as projects"""
    
    __tablename__ = 'quotes'
    
    id = db.Column(db.Integer, primary_key=True)
    quote_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False, index=True)
    
    # Quote details
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='draft', nullable=False)  # 'draft', 'sent', 'accepted', 'rejected', 'expired'
    
    # Financial details (calculated from items)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    tax_rate = db.Column(db.Numeric(5, 2), nullable=False, default=0)  # Tax rate percentage
    tax_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    currency_code = db.Column(db.String(3), nullable=False, default='EUR')
    
    # Discount fields
    discount_type = db.Column(db.String(20), nullable=True)  # 'percentage' or 'fixed'
    discount_amount = db.Column(db.Numeric(10, 2), nullable=True, default=0)  # Discount value
    discount_reason = db.Column(db.String(500), nullable=True)  # Reason for discount
    coupon_code = db.Column(db.String(50), nullable=True, index=True)  # Optional coupon code
    
    # Validity and dates
    valid_until = db.Column(db.Date, nullable=True)  # Quote expiration date
    sent_at = db.Column(db.DateTime, nullable=True)  # When quote was sent to client
    accepted_at = db.Column(db.DateTime, nullable=True)  # When quote was accepted
    rejected_at = db.Column(db.DateTime, nullable=True)  # When quote was rejected
    
    # Approval Workflow fields
    approval_status = db.Column(db.String(20), default='not_required', nullable=False) # 'not_required', 'pending', 'approved', 'rejected'
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    rejected_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Client portal visibility
    visible_to_client = db.Column(db.Boolean, default=False, nullable=False)  # Whether quote is visible in client portal
    
    # PDF template
    template_id = db.Column(db.Integer, db.ForeignKey('quote_pdf_templates.id'), nullable=True, index=True)
    
    # Relationships
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True, index=True)  # Created project when accepted
    
    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    accepted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=local_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=local_now, onupdate=local_now, nullable=False)
    
    # Notes
    notes = db.Column(db.Text, nullable=True)  # Internal notes
    terms = db.Column(db.Text, nullable=True)  # Terms and conditions
    
    # Payment terms
    payment_terms = db.Column(db.String(100), nullable=True)  # e.g., "Net 30", "Net 60", "Due on Receipt", "2/10 Net 30"
    
    # Relationships
    client = db.relationship('Client', backref='quotes')
    project = db.relationship('Project', primaryjoin='Quote.project_id == Project.id', foreign_keys='[Quote.project_id]', uselist=False)
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_quotes')
    accepter = db.relationship('User', foreign_keys=[accepted_by], backref='accepted_quotes')
    approver = db.relationship('User', foreign_keys=[approved_by], backref='approved_quotes')
    rejecter = db.relationship('User', foreign_keys=[rejected_by], backref='rejected_quotes')
    items = db.relationship('QuoteItem', backref='quote', lazy='dynamic', cascade='all, delete-orphan')
    template = db.relationship('QuotePDFTemplate', backref='quotes', lazy='joined')
    
    def __init__(self, quote_number, client_id, title, created_by, **kwargs):
        self.quote_number = quote_number
        self.client_id = client_id
        self.title = title.strip()
        self.created_by = created_by
        
        # Set optional fields
        self.description = kwargs.get('description', '').strip() if kwargs.get('description') else None
        self.status = kwargs.get('status', 'draft')
        self.tax_rate = Decimal(str(kwargs.get('tax_rate', 0)))
        self.currency_code = kwargs.get('currency_code', 'EUR')
        self.valid_until = kwargs.get('valid_until')
        self.notes = kwargs.get('notes', '').strip() if kwargs.get('notes') else None
        self.terms = kwargs.get('terms', '').strip() if kwargs.get('terms') else None
        self.payment_terms = kwargs.get('payment_terms', '').strip() if kwargs.get('payment_terms') else None
        self.visible_to_client = kwargs.get('visible_to_client', False)
        self.template_id = kwargs.get('template_id')
        
        # Discount fields
        self.discount_type = kwargs.get('discount_type')
        if kwargs.get('discount_amount'):
            self.discount_amount = Decimal(str(kwargs.get('discount_amount')))
        else:
            self.discount_amount = Decimal('0')
        self.discount_reason = kwargs.get('discount_reason', '').strip() if kwargs.get('discount_reason') else None
        self.coupon_code = kwargs.get('coupon_code', '').strip().upper() if kwargs.get('coupon_code') else None
    
    def __repr__(self):
        return f'<Quote {self.quote_number} ({self.title})>'
    
    @property
    def is_draft(self):
        """Check if quote is in draft status"""
        return self.status == 'draft'
    
    @property
    def is_sent(self):
        """Check if quote has been sent"""
        return self.status == 'sent'
    
    @property
    def is_accepted(self):
        """Check if quote has been accepted"""
        return self.status == 'accepted'
    
    @property
    def is_rejected(self):
        """Check if quote has been rejected"""
        return self.status == 'rejected'
    
    @property
    def is_expired(self):
        """Check if quote has expired"""
        if not self.valid_until:
            return False
        return local_now().date() > self.valid_until
    
    @property
    def can_be_accepted(self):
        """Check if quote can be accepted (sent and not expired)"""
        return self.status == 'sent' and not self.is_expired
    
    @property
    def has_project(self):
        """Check if quote has been converted to a project"""
        return self.project_id is not None
    
    def calculate_totals(self):
        """Calculate quote totals from items, applying discount if any"""
        items_total = sum(item.total_amount for item in self.items)
        self.subtotal = items_total
        
        # Apply discount if set
        discount_value = Decimal('0')
        if self.discount_type and self.discount_amount:
            if self.discount_type == 'percentage':
                # Percentage discount applied to subtotal
                discount_value = self.subtotal * (self.discount_amount / 100)
            elif self.discount_type == 'fixed':
                # Fixed discount amount
                discount_value = min(self.discount_amount, self.subtotal)  # Can't discount more than subtotal
        
        # Calculate subtotal after discount
        subtotal_after_discount = self.subtotal - discount_value
        
        # Calculate tax on discounted amount
        self.tax_amount = subtotal_after_discount * (self.tax_rate / 100)
        self.total_amount = subtotal_after_discount + self.tax_amount
    
    @property
    def discount_value(self):
        """Calculate the discount value based on type"""
        if not self.discount_type or not self.discount_amount:
            return Decimal('0')
        
        if self.discount_type == 'percentage':
            return self.subtotal * (self.discount_amount / 100)
        elif self.discount_type == 'fixed':
            return min(self.discount_amount, self.subtotal)
        return Decimal('0')
    
    @property
    def subtotal_after_discount(self):
        """Get subtotal after discount is applied"""
        return self.subtotal - self.discount_value
    
    def calculate_due_date_from_payment_terms(self, issue_date=None):
        """Calculate due date based on payment terms
        
        Args:
            issue_date: Date to calculate from (defaults to today)
            
        Returns:
            Date object or None if payment terms cannot be parsed
        """
        from datetime import timedelta
        from app.utils.timezone import local_now
        
        if not self.payment_terms:
            return None
        
        if issue_date is None:
            issue_date = local_now().date()
        
        payment_terms = self.payment_terms.strip().upper()
        
        # Parse common payment terms
        # "Net 30" -> 30 days
        # "Net 60" -> 60 days
        # "Due on Receipt" -> 0 days
        # "2/10 Net 30" -> 30 days (ignore early payment discount)
        # "Net 15" -> 15 days
        # etc.
        
        if 'DUE ON RECEIPT' in payment_terms or 'IMMEDIATE' in payment_terms:
            return issue_date
        
        # Extract number from "Net XX" pattern
        import re
        match = re.search(r'NET\s*(\d+)', payment_terms)
        if match:
            days = int(match.group(1))
            return issue_date + timedelta(days=days)
        
        # Try to extract any number (fallback)
        numbers = re.findall(r'\d+', payment_terms)
        if numbers:
            days = int(numbers[-1])  # Use last number found
            return issue_date + timedelta(days=days)
        
        return None
    
    def send(self):
        """Mark quote as sent"""
        if self.requires_approval and self.approval_status != 'approved':
            raise ValueError("Quote requires approval before it can be sent")
        self.status = 'sent'
        self.sent_at = local_now()
        self.updated_at = local_now()
    
    def request_approval(self):
        """Request approval for the quote"""
        if not self.requires_approval:
            raise ValueError("Quote does not require approval")
        if self.approval_status == 'approved':
            raise ValueError("Quote is already approved")
        self.approval_status = 'pending'
        self.updated_at = local_now()
    
    def approve(self, user_id, notes=None):
        """Approve the quote"""
        if not self.requires_approval:
            raise ValueError("Quote does not require approval")
        if self.approval_status != 'pending':
            raise ValueError("Quote is not pending approval")
        self.approval_status = 'approved'
        self.approved_by = user_id
        self.approved_at = local_now()
        if notes:
            self.notes = (self.notes or '') + f'\n\nApproval notes: {notes}'
        self.updated_at = local_now()
    
    def reject_approval(self, user_id, reason):
        """Reject the quote in approval workflow"""
        if not self.requires_approval:
            raise ValueError("Quote does not require approval")
        if self.approval_status != 'pending':
            raise ValueError("Quote is not pending approval")
        self.approval_status = 'rejected'
        self.rejected_by = user_id
        self.rejected_at = local_now()
        self.rejection_reason = reason
        self.updated_at = local_now()
    
    def accept(self, user_id, project_id=None):
        """Accept the quote and optionally link to a project"""
        if not self.can_be_accepted:
            raise ValueError("Quote cannot be accepted in its current state")
        
        self.status = 'accepted'
        self.accepted_at = local_now()
        self.accepted_by = user_id
        if project_id:
            self.project_id = project_id
        self.updated_at = local_now()
    
    def reject(self):
        """Reject the quote"""
        if self.status not in ['sent', 'draft']:
            raise ValueError("Quote cannot be rejected in its current state")
        
        self.status = 'rejected'
        self.rejected_at = local_now()
        self.updated_at = local_now()
    
    def expire(self):
        """Mark quote as expired"""
        if self.status == 'sent':
            self.status = 'expired'
            self.updated_at = local_now()
    
    def to_dict(self):
        """Convert quote to dictionary for API responses"""
        self.calculate_totals()  # Ensure totals are up to date
        return {
            'id': self.id,
            'quote_number': self.quote_number,
            'client_id': self.client_id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'subtotal': float(self.subtotal),
            'discount_type': self.discount_type,
            'discount_amount': float(self.discount_amount) if self.discount_amount else 0,
            'discount_value': float(self.discount_value),
            'discount_reason': self.discount_reason,
            'coupon_code': self.coupon_code,
            'subtotal_after_discount': float(self.subtotal_after_discount),
            'tax_rate': float(self.tax_rate),
            'tax_amount': float(self.tax_amount),
            'total_amount': float(self.total_amount),
            'currency_code': self.currency_code,
            'valid_until': self.valid_until.isoformat() if self.valid_until else None,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'accepted_at': self.accepted_at.isoformat() if self.accepted_at else None,
            'rejected_at': self.rejected_at.isoformat() if self.rejected_at else None,
            'project_id': self.project_id,
            'created_by': self.created_by,
            'accepted_by': self.accepted_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'notes': self.notes,
            'terms': self.terms,
            'visible_to_client': self.visible_to_client,
            'template_id': self.template_id,
            'is_draft': self.is_draft,
            'is_sent': self.is_sent,
            'is_accepted': self.is_accepted,
            'is_rejected': self.is_rejected,
            'is_expired': self.is_expired,
            'can_be_accepted': self.can_be_accepted,
            'has_project': self.has_project,
            'items': [item.to_dict() for item in self.items]
        }
    
    @classmethod
    def generate_quote_number(cls):
        """Generate a unique quote number"""
        # Format: QUO-YYYYMMDD-XXX
        today = local_now()
        date_prefix = today.strftime('%Y%m%d')
        
        # Find the next available number for today
        existing = cls.query.filter(
            cls.quote_number.like(f'QUO-{date_prefix}-%')
        ).order_by(cls.quote_number.desc()).first()
        
        if existing:
            # Extract the number part and increment
            try:
                last_num = int(existing.quote_number.split('-')[-1])
                next_num = last_num + 1
            except (ValueError, IndexError):
                next_num = 1
        else:
            next_num = 1
        
        return f'QUO-{date_prefix}-{next_num:03d}'


class QuoteItem(db.Model):
    """Quote line item model"""
    
    __tablename__ = 'quote_items'
    
    id = db.Column(db.Integer, primary_key=True)
    quote_id = db.Column(db.Integer, db.ForeignKey('quotes.id'), nullable=False, index=True)
    
    # Item details
    description = db.Column(db.String(500), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), nullable=False, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Optional fields
    unit = db.Column(db.String(20), nullable=True)  # 'hours', 'days', 'items', etc.
    
    # Metadata
    created_at = db.Column(db.DateTime, default=local_now, nullable=False)
    
    def __init__(self, quote_id, description, quantity, unit_price, unit=None):
        self.quote_id = quote_id
        self.description = description.strip()
        self.quantity = Decimal(str(quantity))
        self.unit_price = Decimal(str(unit_price))
        self.total_amount = self.quantity * self.unit_price
        self.unit = unit.strip() if unit else None
    
    def __repr__(self):
        return f'<QuoteItem {self.description} ({self.quantity} @ {self.unit_price})>'
    
    def to_dict(self):
        """Convert quote item to dictionary"""
        return {
            'id': self.id,
            'quote_id': self.quote_id,
            'description': self.description,
            'quantity': float(self.quantity),
            'unit_price': float(self.unit_price),
            'total_amount': float(self.total_amount),
            'unit': self.unit,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class QuotePDFTemplate(db.Model):
    """Model for storing quote PDF templates by page size"""
    
    __tablename__ = 'quote_pdf_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    page_size = db.Column(db.String(20), nullable=False, unique=True)  # A4, Letter, A3, etc.
    template_html = db.Column(db.Text, nullable=True)
    template_css = db.Column(db.Text, nullable=True)
    design_json = db.Column(db.Text, nullable=True)  # Konva.js design state
    is_default = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=local_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=local_now, onupdate=local_now, nullable=False)
    
    # Standard page sizes and their dimensions in mm (for reference)
    PAGE_SIZES = {
        'A4': {'width': 210, 'height': 297},
        'Letter': {'width': 216, 'height': 279},
        'Legal': {'width': 216, 'height': 356},
        'A3': {'width': 297, 'height': 420},
        'A5': {'width': 148, 'height': 210},
        'Tabloid': {'width': 279, 'height': 432},
    }
    
    def __repr__(self):
        return f'<QuotePDFTemplate {self.page_size}>'
    
    @classmethod
    def get_template(cls, page_size='A4'):
        """Get template for a specific page size, creating default if needed"""
        template = cls.query.filter_by(page_size=page_size).first()
        if not template:
            template = cls(page_size=page_size, is_default=(page_size == 'A4'))
            db.session.add(template)
            db.session.commit()
        return template
    
    @classmethod
    def get_all_templates(cls):
        """Get all templates"""
        return cls.query.order_by(cls.page_size).all()
    
    @classmethod
    def get_default_template(cls):
        """Get the default template"""
        template = cls.query.filter_by(is_default=True).first()
        if not template:
            template = cls.get_template('A4')
            template.is_default = True
            db.session.commit()
        return template

