from datetime import datetime, timedelta
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from app import db


class RecurringInvoice(db.Model):
    """Recurring invoice template model for automated billing"""
    
    __tablename__ = 'recurring_invoices'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)  # Template name/description
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False, index=True)
    
    # Recurrence settings
    frequency = db.Column(db.String(20), nullable=False)  # 'daily', 'weekly', 'monthly', 'yearly'
    interval = db.Column(db.Integer, nullable=False, default=1)  # Every N periods (e.g., every 2 weeks)
    next_run_date = db.Column(db.Date, nullable=False)  # Next date to generate invoice
    end_date = db.Column(db.Date, nullable=True)  # Optional end date for recurrence
    
    # Invoice template settings (copied to generated invoices)
    client_name = db.Column(db.String(200), nullable=False)
    client_email = db.Column(db.String(200), nullable=True)
    client_address = db.Column(db.Text, nullable=True)
    due_date_days = db.Column(db.Integer, nullable=False, default=30)  # Days from issue date to due date
    tax_rate = db.Column(db.Numeric(5, 2), nullable=False, default=0)
    currency_code = db.Column(db.String(3), nullable=False, default='EUR')
    notes = db.Column(db.Text, nullable=True)
    terms = db.Column(db.Text, nullable=True)
    template_id = db.Column(db.Integer, db.ForeignKey('invoice_templates.id'), nullable=True, index=True)
    
    # Auto-send settings
    auto_send = db.Column(db.Boolean, nullable=False, default=False)  # Automatically send via email when generated
    auto_include_time_entries = db.Column(db.Boolean, nullable=False, default=True)  # Include unbilled time entries
    
    # Status
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    
    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_generated_at = db.Column(db.DateTime, nullable=True)  # Last time an invoice was generated
    
    # Relationships
    project = db.relationship('Project', backref='recurring_invoices')
    client = db.relationship('Client', backref='recurring_invoices')
    creator = db.relationship('User', backref='created_recurring_invoices')
    template = db.relationship('InvoiceTemplate', backref='recurring_invoices')
    generated_invoices = db.relationship('Invoice', backref='recurring_invoice_template', lazy='dynamic', foreign_keys='[Invoice.recurring_invoice_id]')
    
    def __init__(self, name, project_id, client_id, frequency, next_run_date, created_by, **kwargs):
        self.name = name
        self.project_id = project_id
        self.client_id = client_id
        self.frequency = frequency
        self.next_run_date = next_run_date
        self.created_by = created_by
        
        # Set optional fields
        self.interval = kwargs.get('interval', 1)
        self.end_date = kwargs.get('end_date')
        self.client_name = kwargs.get('client_name', '')
        self.client_email = kwargs.get('client_email')
        self.client_address = kwargs.get('client_address')
        self.due_date_days = kwargs.get('due_date_days', 30)
        self.tax_rate = Decimal(str(kwargs.get('tax_rate', 0)))
        self.currency_code = kwargs.get('currency_code', 'EUR')
        self.notes = kwargs.get('notes')
        self.terms = kwargs.get('terms')
        self.template_id = kwargs.get('template_id')
        self.auto_send = kwargs.get('auto_send', False)
        self.auto_include_time_entries = kwargs.get('auto_include_time_entries', True)
        self.is_active = kwargs.get('is_active', True)
    
    def __repr__(self):
        return f'<RecurringInvoice {self.name} ({self.frequency})>'
    
    def calculate_next_run_date(self, from_date=None):
        """Calculate the next run date based on frequency and interval"""
        if from_date is None:
            from_date = datetime.utcnow().date()
        
        if self.frequency == 'daily':
            return from_date + timedelta(days=self.interval)
        elif self.frequency == 'weekly':
            return from_date + timedelta(weeks=self.interval)
        elif self.frequency == 'monthly':
            return from_date + relativedelta(months=self.interval)
        elif self.frequency == 'yearly':
            return from_date + relativedelta(years=self.interval)
        else:
            raise ValueError(f"Invalid frequency: {self.frequency}")
    
    def should_generate_today(self):
        """Check if invoice should be generated today"""
        if not self.is_active:
            return False
        
        today = datetime.utcnow().date()
        
        # Check if we've reached the end date
        if self.end_date and today > self.end_date:
            return False
        
        # Check if it's time to generate
        return today >= self.next_run_date
    
    def generate_invoice(self):
        """Generate an invoice from this recurring template"""
        from app.models import Invoice, InvoiceItem, TimeEntry, Settings
        
        if not self.should_generate_today():
            return None
        
        # Get settings for currency
        settings = Settings.get_settings()
        currency_code = self.currency_code or (settings.currency if settings else 'EUR')
        
        # Calculate dates
        issue_date = datetime.utcnow().date()
        due_date = issue_date + timedelta(days=self.due_date_days)
        
        # Generate invoice number
        invoice_number = Invoice.generate_invoice_number()
        
        # Create invoice
        invoice = Invoice(
            invoice_number=invoice_number,
            project_id=self.project_id,
            client_name=self.client_name,
            due_date=due_date,
            created_by=self.created_by,
            client_id=self.client_id,
            client_email=self.client_email,
            client_address=self.client_address,
            tax_rate=self.tax_rate,
            notes=self.notes,
            terms=self.terms,
            currency_code=currency_code,
            template_id=self.template_id,
            issue_date=issue_date
        )
        
        # Link to recurring invoice template
        invoice.recurring_invoice_id = self.id
        
        db.session.add(invoice)
        
        # Auto-include time entries if enabled
        if self.auto_include_time_entries:
            # Get unbilled time entries for this project
            time_entries = TimeEntry.query.filter(
                TimeEntry.project_id == self.project_id,
                TimeEntry.end_time.isnot(None),
                TimeEntry.billable == True
            ).order_by(TimeEntry.start_time.desc()).all()
            
            # Filter out entries already billed
            unbilled_entries = []
            for entry in time_entries:
                already_billed = False
                for other_invoice in self.project.invoices:
                    if other_invoice.id != invoice.id:
                        for item in other_invoice.items:
                            if item.time_entry_ids and str(entry.id) in item.time_entry_ids.split(','):
                                already_billed = True
                                break
                    if already_billed:
                        break
                
                if not already_billed:
                    unbilled_entries.append(entry)
            
            # Group and create invoice items
            if unbilled_entries:
                from app.models.rate_override import RateOverride
                grouped_entries = {}
                for entry in unbilled_entries:
                    if entry.task_id:
                        key = f"task_{entry.task_id}"
                        description = f"Task: {entry.task.name if entry.task else 'Unknown Task'}"
                    else:
                        key = f"project_{entry.project_id}"
                        description = f"Project: {entry.project.name}"
                    
                    if key not in grouped_entries:
                        grouped_entries[key] = {
                            'description': description,
                            'entries': [],
                            'total_hours': Decimal('0'),
                        }
                    
                    grouped_entries[key]['entries'].append(entry)
                    grouped_entries[key]['total_hours'] += entry.duration_hours
                
                # Create invoice items
                hourly_rate = RateOverride.resolve_rate(self.project)
                for group in grouped_entries.values():
                    if group['total_hours'] > 0:
                        item = InvoiceItem(
                            invoice_id=invoice.id,
                            description=group['description'],
                            quantity=group['total_hours'],
                            unit_price=hourly_rate,
                            time_entry_ids=','.join(str(e.id) for e in group['entries'])
                        )
                        db.session.add(item)
        
        # Calculate totals
        invoice.calculate_totals()
        
        # Update recurring invoice
        self.last_generated_at = datetime.utcnow()
        self.next_run_date = self.calculate_next_run_date(issue_date)
        
        return invoice
    
    def to_dict(self):
        """Convert recurring invoice to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'project_id': self.project_id,
            'client_id': self.client_id,
            'frequency': self.frequency,
            'interval': self.interval,
            'next_run_date': self.next_run_date.isoformat() if self.next_run_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'client_name': self.client_name,
            'client_email': self.client_email,
            'due_date_days': self.due_date_days,
            'tax_rate': float(self.tax_rate),
            'currency_code': self.currency_code,
            'auto_send': self.auto_send,
            'auto_include_time_entries': self.auto_include_time_entries,
            'is_active': self.is_active,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_generated_at': self.last_generated_at.isoformat() if self.last_generated_at else None
        }

