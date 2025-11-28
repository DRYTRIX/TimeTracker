from datetime import datetime
from decimal import Decimal
from app import db
from sqlalchemy import Index


class ExpenseCategory(db.Model):
    """Expense category model with budget tracking"""

    __tablename__ = "expense_categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True, index=True)
    description = db.Column(db.Text, nullable=True)
    code = db.Column(db.String(20), nullable=True, unique=True, index=True)  # Short code for quick reference
    color = db.Column(db.String(7), nullable=True)  # Hex color for UI (e.g., #FF5733)
    icon = db.Column(db.String(50), nullable=True)  # Icon name for UI

    # Budget settings
    monthly_budget = db.Column(db.Numeric(10, 2), nullable=True)
    quarterly_budget = db.Column(db.Numeric(10, 2), nullable=True)
    yearly_budget = db.Column(db.Numeric(10, 2), nullable=True)
    budget_threshold_percent = db.Column(db.Integer, nullable=False, default=80)  # Alert when exceeded

    # Settings
    requires_receipt = db.Column(db.Boolean, default=True, nullable=False)
    requires_approval = db.Column(db.Boolean, default=True, nullable=False)
    default_tax_rate = db.Column(db.Numeric(5, 2), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __init__(self, name, **kwargs):
        self.name = name.strip()
        self.description = kwargs.get("description", "").strip() if kwargs.get("description") else None
        self.code = kwargs.get("code", "").strip() if kwargs.get("code") else None
        self.color = kwargs.get("color")
        self.icon = kwargs.get("icon")
        self.monthly_budget = Decimal(str(kwargs.get("monthly_budget"))) if kwargs.get("monthly_budget") else None
        self.quarterly_budget = Decimal(str(kwargs.get("quarterly_budget"))) if kwargs.get("quarterly_budget") else None
        self.yearly_budget = Decimal(str(kwargs.get("yearly_budget"))) if kwargs.get("yearly_budget") else None
        self.budget_threshold_percent = kwargs.get("budget_threshold_percent", 80)
        self.requires_receipt = kwargs.get("requires_receipt", True)
        self.requires_approval = kwargs.get("requires_approval", True)
        self.default_tax_rate = Decimal(str(kwargs.get("default_tax_rate"))) if kwargs.get("default_tax_rate") else None
        self.is_active = kwargs.get("is_active", True)

    def __repr__(self):
        return f"<ExpenseCategory {self.name}>"

    def get_spent_amount(self, start_date, end_date):
        """Get total amount spent in this category for date range"""
        from app.models.expense import Expense

        query = db.session.query(db.func.sum(Expense.amount + db.func.coalesce(Expense.tax_amount, 0))).filter(
            Expense.category == self.name,
            Expense.status.in_(["approved", "reimbursed"]),
            Expense.expense_date >= start_date,
            Expense.expense_date <= end_date,
        )

        total = query.scalar() or Decimal("0")
        return float(total)

    def get_budget_utilization(self, period="monthly"):
        """Get budget utilization percentage for the current period"""
        from datetime import date

        today = date.today()

        if period == "monthly":
            start_date = date(today.year, today.month, 1)
            budget = self.monthly_budget
        elif period == "quarterly":
            quarter = (today.month - 1) // 3 + 1
            start_month = (quarter - 1) * 3 + 1
            start_date = date(today.year, start_month, 1)
            budget = self.quarterly_budget
        elif period == "yearly":
            start_date = date(today.year, 1, 1)
            budget = self.yearly_budget
        else:
            return None

        if not budget or budget == 0:
            return None

        spent = self.get_spent_amount(start_date, today)
        utilization = (spent / float(budget)) * 100

        return {
            "spent": spent,
            "budget": float(budget),
            "utilization_percent": round(utilization, 2),
            "remaining": float(budget) - spent,
            "over_threshold": utilization >= self.budget_threshold_percent,
        }

    def to_dict(self):
        """Convert category to dictionary for API responses"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "code": self.code,
            "color": self.color,
            "icon": self.icon,
            "monthly_budget": float(self.monthly_budget) if self.monthly_budget else None,
            "quarterly_budget": float(self.quarterly_budget) if self.quarterly_budget else None,
            "yearly_budget": float(self.yearly_budget) if self.yearly_budget else None,
            "budget_threshold_percent": self.budget_threshold_percent,
            "requires_receipt": self.requires_receipt,
            "requires_approval": self.requires_approval,
            "default_tax_rate": float(self.default_tax_rate) if self.default_tax_rate else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def get_active_categories(cls):
        """Get all active categories"""
        return cls.query.filter_by(is_active=True).order_by(cls.name).all()

    @classmethod
    def get_categories_over_budget(cls, period="monthly"):
        """Get categories that are over their budget threshold"""
        categories = cls.get_active_categories()
        over_budget = []

        for category in categories:
            utilization = category.get_budget_utilization(period)
            if utilization and utilization["over_threshold"]:
                over_budget.append({"category": category, "utilization": utilization})

        return over_budget
