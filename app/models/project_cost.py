from datetime import datetime
from decimal import Decimal
from app import db


class ProjectCost(db.Model):
    """Project cost model for tracking expenses beyond hourly work"""

    __tablename__ = "project_costs"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    # Cost details
    description = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # 'travel', 'materials', 'services', 'equipment', 'other'
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency_code = db.Column(db.String(3), nullable=False, default="EUR")

    # Billing
    billable = db.Column(db.Boolean, default=True, nullable=False)
    invoiced = db.Column(db.Boolean, default=False, nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=True, index=True)

    # Date and metadata
    cost_date = db.Column(db.Date, nullable=False, index=True)
    notes = db.Column(db.Text, nullable=True)
    receipt_path = db.Column(db.String(500), nullable=True)  # Path to uploaded receipt

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    # project and user relationships defined via backref

    def __init__(
        self,
        project_id,
        user_id,
        description,
        category,
        amount,
        cost_date,
        billable=True,
        notes=None,
        currency_code="EUR",
        receipt_path=None,
    ):
        self.project_id = project_id
        self.user_id = user_id
        self.description = description.strip() if description else None
        self.category = category
        self.amount = Decimal(str(amount))
        self.cost_date = cost_date
        self.billable = billable
        self.notes = notes.strip() if notes else None
        self.currency_code = currency_code
        self.receipt_path = receipt_path

    def __repr__(self):
        return f"<ProjectCost {self.description} ({self.amount} {self.currency_code})>"

    @property
    def is_invoiced(self):
        """Check if this cost has been invoiced"""
        return self.invoiced and self.invoice_id is not None

    def mark_as_invoiced(self, invoice_id):
        """Mark this cost as invoiced"""
        self.invoiced = True
        self.invoice_id = invoice_id
        self.updated_at = datetime.utcnow()

    def unmark_as_invoiced(self):
        """Unmark this cost as invoiced (e.g., if invoice is deleted)"""
        self.invoiced = False
        self.invoice_id = None
        self.updated_at = datetime.utcnow()

    def to_dict(self):
        """Convert project cost to dictionary for API responses"""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "description": self.description,
            "category": self.category,
            "amount": float(self.amount),
            "currency_code": self.currency_code,
            "billable": self.billable,
            "invoiced": self.invoiced,
            "invoice_id": self.invoice_id,
            "cost_date": self.cost_date.isoformat() if self.cost_date else None,
            "notes": self.notes,
            "receipt_path": self.receipt_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "project": self.project.name if self.project else None,
            "user": self.user.username if self.user else None,
        }

    @classmethod
    def get_project_costs(cls, project_id, start_date=None, end_date=None, user_id=None, billable_only=False):
        """Get costs for a specific project with optional filters"""
        query = cls.query.filter_by(project_id=project_id)

        if start_date:
            query = query.filter(cls.cost_date >= start_date)

        if end_date:
            query = query.filter(cls.cost_date <= end_date)

        if user_id:
            query = query.filter(cls.user_id == user_id)

        if billable_only:
            query = query.filter(cls.billable == True)

        return query.order_by(cls.cost_date.desc()).all()

    @classmethod
    def get_total_costs(cls, project_id, start_date=None, end_date=None, user_id=None, billable_only=False):
        """Calculate total costs for a project with optional filters"""
        query = db.session.query(db.func.sum(cls.amount)).filter_by(project_id=project_id)

        if start_date:
            query = query.filter(cls.cost_date >= start_date)

        if end_date:
            query = query.filter(cls.cost_date <= end_date)

        if user_id:
            query = query.filter(cls.user_id == user_id)

        if billable_only:
            query = query.filter(cls.billable == True)

        total = query.scalar() or Decimal("0")
        return float(total)

    @classmethod
    def get_uninvoiced_costs(cls, project_id):
        """Get all billable costs that haven't been invoiced yet"""
        return (
            cls.query.filter_by(project_id=project_id, billable=True, invoiced=False)
            .order_by(cls.cost_date.desc())
            .all()
        )

    @classmethod
    def get_costs_by_category(cls, project_id, start_date=None, end_date=None):
        """Get costs grouped by category"""
        query = db.session.query(
            cls.category, db.func.sum(cls.amount).label("total_amount"), db.func.count(cls.id).label("count")
        ).filter_by(project_id=project_id)

        if start_date:
            query = query.filter(cls.cost_date >= start_date)

        if end_date:
            query = query.filter(cls.cost_date <= end_date)

        results = query.group_by(cls.category).all()

        return [
            {"category": category, "total_amount": float(total_amount), "count": count}
            for category, total_amount, count in results
        ]
