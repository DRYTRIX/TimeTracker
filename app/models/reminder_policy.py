"""Models for invoice reminder policies and policy levels."""

from datetime import datetime
from decimal import Decimal

from app import db


class ReminderPolicy(db.Model):
    """A named set of reminder levels that can be applied to clients/invoices."""

    __tablename__ = "reminder_policies"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    is_default = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    levels = db.relationship(
        "ReminderPolicyLevel",
        backref="policy",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="ReminderPolicyLevel.sort_order",
    )

    def __repr__(self):
        return f"<ReminderPolicy {self.name!r} default={self.is_default}>"

    @classmethod
    def get_default(cls):
        """Return the first active policy with is_default=True, or None."""
        return cls.query.filter_by(is_default=True, active=True).first()

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "active": self.active,
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "levels": [lv.to_dict() for lv in self.levels],
        }


class ReminderPolicyLevel(db.Model):
    """A single trigger level within a reminder policy."""

    __tablename__ = "reminder_policy_levels"

    id = db.Column(db.Integer, primary_key=True)
    policy_id = db.Column(
        db.Integer, db.ForeignKey("reminder_policies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # negative = before due date, positive = after due date (days)
    days_offset = db.Column(db.Integer, nullable=False)
    template_name = db.Column(db.String(100), nullable=True)
    # 'fixed' | 'percent_annual' | null
    late_fee_type = db.Column(db.String(20), nullable=True)
    late_fee_value = db.Column(db.Numeric(10, 2), nullable=True)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<ReminderPolicyLevel policy={self.policy_id} offset={self.days_offset}>"

    def to_dict(self):
        return {
            "id": self.id,
            "policy_id": self.policy_id,
            "days_offset": self.days_offset,
            "template_name": self.template_name,
            "late_fee_type": self.late_fee_type,
            "late_fee_value": float(self.late_fee_value) if self.late_fee_value is not None else None,
            "sort_order": self.sort_order,
            "active": self.active,
        }
