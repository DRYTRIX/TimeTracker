from datetime import datetime
from decimal import Decimal
from app import db
from sqlalchemy import Index


class Expense(db.Model):
    """Expense tracking model for business expenses"""

    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=True, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=True, index=True)

    # Expense details
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(
        db.String(50), nullable=False
    )  # 'travel', 'meals', 'accommodation', 'supplies', 'software', 'equipment', 'services', 'other'
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency_code = db.Column(db.String(3), nullable=False, default="EUR")

    # Tax information
    tax_amount = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    tax_rate = db.Column(db.Numeric(5, 2), nullable=True, default=0)  # Percentage

    # Payment information
    payment_method = db.Column(
        db.String(50), nullable=True
    )  # 'cash', 'credit_card', 'bank_transfer', 'company_card', etc.
    payment_date = db.Column(db.Date, nullable=True)

    # Status and approval
    status = db.Column(
        db.String(20), default="pending", nullable=False
    )  # 'pending', 'approved', 'rejected', 'reimbursed'
    approved_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)

    # Billing and invoicing
    billable = db.Column(db.Boolean, default=False, nullable=False)
    reimbursable = db.Column(db.Boolean, default=True, nullable=False)
    invoiced = db.Column(db.Boolean, default=False, nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=True, index=True)
    reimbursed = db.Column(db.Boolean, default=False, nullable=False)
    reimbursed_at = db.Column(db.DateTime, nullable=True)

    # Date and metadata
    expense_date = db.Column(db.Date, nullable=False, index=True)
    receipt_path = db.Column(db.String(500), nullable=True)
    receipt_number = db.Column(db.String(100), nullable=True)
    vendor = db.Column(db.String(200), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    # Tags for categorization
    tags = db.Column(db.String(500), nullable=True)  # Comma-separated tags

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = db.relationship("User", foreign_keys=[user_id], backref=db.backref("expenses", lazy="dynamic"))
    approver = db.relationship(
        "User", foreign_keys=[approved_by], backref=db.backref("approved_expenses", lazy="dynamic")
    )
    project = db.relationship("Project", backref=db.backref("expenses", lazy="dynamic"))
    client = db.relationship("Client", backref=db.backref("expenses", lazy="dynamic"))
    invoice = db.relationship("Invoice", backref=db.backref("expenses", lazy="dynamic"))

    # Add composite indexes for common query patterns
    __table_args__ = (
        Index("ix_expenses_user_date", "user_id", "expense_date"),
        Index("ix_expenses_status_date", "status", "expense_date"),
        Index("ix_expenses_project_date", "project_id", "expense_date"),
    )

    def __init__(self, user_id, title, category, amount, expense_date, **kwargs):
        self.user_id = user_id
        self.title = title.strip() if title else None
        self.category = category
        self.amount = Decimal(str(amount))
        self.expense_date = expense_date

        # Optional fields
        self.description = kwargs.get("description", "").strip() if kwargs.get("description") else None
        self.project_id = kwargs.get("project_id")
        self.client_id = kwargs.get("client_id")
        self.currency_code = kwargs.get("currency_code", "EUR")
        self.tax_amount = Decimal(str(kwargs.get("tax_amount", 0)))
        self.tax_rate = Decimal(str(kwargs.get("tax_rate", 0)))
        self.payment_method = kwargs.get("payment_method")
        self.payment_date = kwargs.get("payment_date")
        self.billable = kwargs.get("billable", False)
        self.reimbursable = kwargs.get("reimbursable", True)
        self.receipt_path = kwargs.get("receipt_path")
        self.receipt_number = kwargs.get("receipt_number")
        self.vendor = kwargs.get("vendor")
        self.notes = kwargs.get("notes", "").strip() if kwargs.get("notes") else None
        self.tags = kwargs.get("tags")
        self.status = kwargs.get("status", "pending")

    def __repr__(self):
        return f"<Expense {self.title} ({self.amount} {self.currency_code})>"

    @property
    def is_approved(self):
        """Check if expense is approved"""
        return self.status == "approved"

    @property
    def is_rejected(self):
        """Check if expense is rejected"""
        return self.status == "rejected"

    @property
    def is_reimbursed(self):
        """Check if expense has been reimbursed"""
        return self.reimbursed and self.reimbursed_at is not None

    @property
    def is_invoiced(self):
        """Check if this expense has been invoiced"""
        return self.invoiced and self.invoice_id is not None

    @property
    def total_amount(self):
        """Calculate total amount including tax"""
        return self.amount + (self.tax_amount or 0)

    @property
    def tag_list(self):
        """Get list of tags"""
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(",") if tag.strip()]

    def approve(self, approved_by_user_id, notes=None):
        """Approve the expense"""
        self.status = "approved"
        self.approved_by = approved_by_user_id
        self.approved_at = datetime.utcnow()
        if notes:
            self.notes = (self.notes or "") + f"\n\nApproval notes: {notes}"
        self.updated_at = datetime.utcnow()

    def reject(self, rejected_by_user_id, reason):
        """Reject the expense"""
        self.status = "rejected"
        self.approved_by = rejected_by_user_id
        self.approved_at = datetime.utcnow()
        self.rejection_reason = reason
        self.updated_at = datetime.utcnow()

    def mark_as_reimbursed(self):
        """Mark this expense as reimbursed"""
        self.reimbursed = True
        self.reimbursed_at = datetime.utcnow()
        self.status = "reimbursed"
        self.updated_at = datetime.utcnow()

    def mark_as_invoiced(self, invoice_id):
        """Mark this expense as invoiced"""
        self.invoiced = True
        self.invoice_id = invoice_id
        self.updated_at = datetime.utcnow()

    def unmark_as_invoiced(self):
        """Unmark this expense as invoiced (e.g., if invoice is deleted)"""
        self.invoiced = False
        self.invoice_id = None
        self.updated_at = datetime.utcnow()

    def to_dict(self):
        """Convert expense to dictionary for API responses"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "client_id": self.client_id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "amount": float(self.amount),
            "currency_code": self.currency_code,
            "tax_amount": float(self.tax_amount) if self.tax_amount else 0,
            "tax_rate": float(self.tax_rate) if self.tax_rate else 0,
            "total_amount": float(self.total_amount),
            "payment_method": self.payment_method,
            "payment_date": self.payment_date.isoformat() if self.payment_date else None,
            "status": self.status,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejection_reason": self.rejection_reason,
            "billable": self.billable,
            "reimbursable": self.reimbursable,
            "invoiced": self.invoiced,
            "invoice_id": self.invoice_id,
            "reimbursed": self.reimbursed,
            "reimbursed_at": self.reimbursed_at.isoformat() if self.reimbursed_at else None,
            "expense_date": self.expense_date.isoformat() if self.expense_date else None,
            "receipt_path": self.receipt_path,
            "receipt_number": self.receipt_number,
            "vendor": self.vendor,
            "notes": self.notes,
            "tags": self.tag_list,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "user": self.user.username if self.user else None,
            "project": self.project.name if self.project else None,
            "client": self.client.name if self.client else None,
            "approver": self.approver.username if self.approver else None,
        }

    @classmethod
    def get_expenses(
        cls,
        user_id=None,
        project_id=None,
        client_id=None,
        start_date=None,
        end_date=None,
        status=None,
        category=None,
        billable_only=False,
        reimbursable_only=False,
    ):
        """Get expenses with optional filters"""
        query = cls.query

        if user_id:
            query = query.filter(cls.user_id == user_id)

        if project_id:
            query = query.filter(cls.project_id == project_id)

        if client_id:
            query = query.filter(cls.client_id == client_id)

        if start_date:
            query = query.filter(cls.expense_date >= start_date)

        if end_date:
            query = query.filter(cls.expense_date <= end_date)

        if status:
            query = query.filter(cls.status == status)

        if category:
            query = query.filter(cls.category == category)

        if billable_only:
            query = query.filter(cls.billable == True)

        if reimbursable_only:
            query = query.filter(cls.reimbursable == True)

        return query.order_by(cls.expense_date.desc()).all()

    @classmethod
    def get_total_expenses(
        cls,
        user_id=None,
        project_id=None,
        client_id=None,
        start_date=None,
        end_date=None,
        status=None,
        category=None,
        include_tax=True,
    ):
        """Calculate total expenses with optional filters"""
        query = db.session.query(
            db.func.sum(cls.amount if not include_tax else cls.amount + db.func.coalesce(cls.tax_amount, 0))
        )

        if user_id:
            query = query.filter(cls.user_id == user_id)

        if project_id:
            query = query.filter(cls.project_id == project_id)

        if client_id:
            query = query.filter(cls.client_id == client_id)

        if start_date:
            query = query.filter(cls.expense_date >= start_date)

        if end_date:
            query = query.filter(cls.expense_date <= end_date)

        if status:
            query = query.filter(cls.status == status)

        if category:
            query = query.filter(cls.category == category)

        total = query.scalar() or Decimal("0")
        return float(total)

    @classmethod
    def get_expenses_by_category(cls, user_id=None, start_date=None, end_date=None, status=None):
        """Get expenses grouped by category"""
        query = db.session.query(
            cls.category,
            db.func.sum(cls.amount + db.func.coalesce(cls.tax_amount, 0)).label("total_amount"),
            db.func.count(cls.id).label("count"),
        )

        if user_id:
            query = query.filter(cls.user_id == user_id)

        if start_date:
            query = query.filter(cls.expense_date >= start_date)

        if end_date:
            query = query.filter(cls.expense_date <= end_date)

        if status:
            query = query.filter(cls.status == status)

        results = query.group_by(cls.category).all()

        return [
            {"category": category, "total_amount": float(total_amount), "count": count}
            for category, total_amount, count in results
        ]

    @classmethod
    def get_pending_approvals(cls, user_id=None):
        """Get expenses pending approval"""
        query = cls.query.filter_by(status="pending")

        if user_id:
            query = query.filter(cls.user_id == user_id)

        return query.order_by(cls.expense_date.desc()).all()

    @classmethod
    def get_pending_reimbursements(cls, user_id=None):
        """Get approved expenses pending reimbursement"""
        query = cls.query.filter(cls.status == "approved", cls.reimbursable == True, cls.reimbursed == False)

        if user_id:
            query = query.filter(cls.user_id == user_id)

        return query.order_by(cls.expense_date.desc()).all()

    @classmethod
    def get_uninvoiced_expenses(cls, project_id=None, client_id=None):
        """Get billable expenses that haven't been invoiced yet"""
        query = cls.query.filter(cls.status == "approved", cls.billable == True, cls.invoiced == False)

        if project_id:
            query = query.filter(cls.project_id == project_id)

        if client_id:
            query = query.filter(cls.client_id == client_id)

        return query.order_by(cls.expense_date.desc()).all()

    @classmethod
    def get_expense_categories(cls):
        """Get list of available expense categories"""
        return [
            "travel",
            "meals",
            "accommodation",
            "supplies",
            "software",
            "equipment",
            "services",
            "marketing",
            "training",
            "other",
        ]

    @classmethod
    def get_payment_methods(cls):
        """Get list of available payment methods"""
        return ["cash", "credit_card", "debit_card", "bank_transfer", "company_card", "paypal", "other"]
