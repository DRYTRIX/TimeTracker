from datetime import datetime
from decimal import Decimal

from app import db


class ClientPrepaidConsumption(db.Model):
    """Ledger entries tracking which time entries consumed prepaid hours."""

    __tablename__ = "client_prepaid_consumptions"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False, index=True)
    time_entry_id = db.Column(db.Integer, db.ForeignKey("time_entries.id"), nullable=False, unique=True, index=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=True, index=True)
    allocation_month = db.Column(db.Date, nullable=False, index=True)
    seconds_consumed = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    client = db.relationship(
        "Client", backref=db.backref("prepaid_consumptions", lazy="dynamic", cascade="all, delete-orphan")
    )
    time_entry = db.relationship("TimeEntry", backref=db.backref("prepaid_consumption", uselist=False))
    invoice = db.relationship("Invoice", backref=db.backref("prepaid_consumptions", lazy="dynamic"))

    def __repr__(self):
        month = self.allocation_month.isoformat() if self.allocation_month else "?"
        return f"<ClientPrepaidConsumption client={self.client_id} entry={self.time_entry_id} month={month}>"

    @property
    def hours_consumed(self) -> Decimal:
        """Return consumed prepaid hours as Decimal."""
        if not self.seconds_consumed:
            return Decimal("0")
        return (Decimal(self.seconds_consumed) / Decimal("3600")).quantize(Decimal("0.01"))
