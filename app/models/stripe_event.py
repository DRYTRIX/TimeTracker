from datetime import datetime

from app import db


class StripeEvent(db.Model):
    """Idempotency table for Stripe webhooks."""

    __tablename__ = "stripe_events"

    id = db.Column(db.Integer, primary_key=True)
    stripe_event_id = db.Column(db.String(128), unique=True, nullable=False, index=True)
    event_type = db.Column(db.String(128), nullable=True, index=True)

    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True)

    received_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    processed_at = db.Column(db.DateTime, nullable=True)

    payload_json = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<StripeEvent {self.stripe_event_id} {self.event_type}>"

