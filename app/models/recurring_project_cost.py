from datetime import datetime, timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta

from app import db


class RecurringProjectCost(db.Model):
    """Recurring project cost template for automated expense generation."""

    __tablename__ = "recurring_project_costs"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    description = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    billable = db.Column(db.Boolean, nullable=False, default=True)
    currency_code = db.Column(db.String(3), nullable=False, default="EUR")

    frequency = db.Column(db.String(20), nullable=False)  # daily, weekly, monthly, yearly
    interval = db.Column(db.Integer, nullable=False, default=1)
    next_run_date = db.Column(db.Date, nullable=False, index=True)
    end_date = db.Column(db.Date, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    last_generated_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    project = db.relationship("Project", backref=db.backref("recurring_costs", lazy="dynamic"))
    user = db.relationship("User", backref=db.backref("recurring_project_costs", lazy="dynamic"))

    def __init__(
        self,
        project_id,
        user_id,
        description,
        category,
        amount,
        frequency,
        next_run_date,
        **kwargs,
    ):
        self.project_id = project_id
        self.user_id = user_id
        self.description = description.strip() if description else ""
        self.category = category
        self.amount = Decimal(str(amount))
        self.frequency = frequency
        self.next_run_date = next_run_date
        self.interval = kwargs.get("interval", 1)
        self.end_date = kwargs.get("end_date")
        self.billable = kwargs.get("billable", True)
        self.currency_code = kwargs.get("currency_code", "EUR")
        self.is_active = kwargs.get("is_active", True)

    def __repr__(self):
        return f"<RecurringProjectCost {self.description} ({self.frequency})>"

    def calculate_next_run_date(self, from_date=None):
        if from_date is None:
            from_date = datetime.utcnow().date()

        if self.frequency == "daily":
            return from_date + timedelta(days=self.interval)
        if self.frequency == "weekly":
            return from_date + timedelta(weeks=self.interval)
        if self.frequency == "monthly":
            return from_date + relativedelta(months=self.interval)
        if self.frequency == "yearly":
            return from_date + relativedelta(years=self.interval)
        raise ValueError(f"Invalid frequency: {self.frequency}")

    def should_generate_today(self):
        if not self.is_active:
            return False

        today = datetime.utcnow().date()
        if self.end_date and today > self.end_date:
            return False
        return today >= self.next_run_date

    def generate_cost(self):
        from app.services.recurring_project_cost_service import RecurringProjectCostService

        return RecurringProjectCostService().generate_cost(self)

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "description": self.description,
            "category": self.category,
            "amount": float(self.amount),
            "billable": self.billable,
            "currency_code": self.currency_code,
            "frequency": self.frequency,
            "interval": self.interval,
            "next_run_date": self.next_run_date.isoformat() if self.next_run_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "is_active": self.is_active,
            "last_generated_at": self.last_generated_at.isoformat() if self.last_generated_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "project": self.project.name if self.project else None,
            "user": self.user.username if self.user else None,
        }
