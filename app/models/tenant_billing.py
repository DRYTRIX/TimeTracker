from datetime import datetime

from app import db


class TenantBilling(db.Model):
    """Stripe subscription state for a tenant."""

    __tablename__ = "tenant_billing"
    __table_args__ = (
        db.UniqueConstraint("tenant_id", name="uq_tenant_billing_tenant_id"),
        db.UniqueConstraint("stripe_subscription_id", name="uq_tenant_billing_stripe_subscription_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    tier = db.Column(db.String(20), nullable=False, default="basic")  # basic | team | pro
    seat_quantity = db.Column(db.Integer, nullable=False, default=1)

    stripe_customer_id = db.Column(db.String(64), nullable=True, index=True)
    stripe_subscription_id = db.Column(db.String(64), nullable=True, index=True)
    stripe_subscription_item_id = db.Column(db.String(64), nullable=True)
    stripe_price_id = db.Column(db.String(64), nullable=True)

    status = db.Column(db.String(32), nullable=True)  # active | past_due | canceled | ...
    current_period_end = db.Column(db.DateTime, nullable=True)
    cancel_at_period_end = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tenant = db.relationship("Tenant", backref=db.backref("billing", uselist=False))

    def __repr__(self):
        return f"<TenantBilling tenant_id={self.tenant_id} tier={self.tier} seats={self.seat_quantity}>"

