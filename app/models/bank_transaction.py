"""Bank statement transactions for payment reconciliation."""

from datetime import datetime

from app import db


class BankTransaction(db.Model):
    """Imported bank statement line pending match to an invoice payment."""

    __tablename__ = "bank_transactions"

    MATCH_PENDING = "pending"
    MATCH_MATCHED = "matched"
    MATCH_IGNORED = "ignored"

    id = db.Column(db.Integer, primary_key=True)
    account_label = db.Column(db.String(120), nullable=True)
    booking_date = db.Column(db.Date, nullable=False, index=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="EUR")
    counterparty = db.Column(db.String(255), nullable=True)
    reference = db.Column(db.String(255), nullable=True)
    raw_payload = db.Column(db.JSON, nullable=True)
    match_status = db.Column(db.String(20), nullable=False, default=MATCH_PENDING, index=True)
    matched_invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=True, index=True)
    matched_payment_id = db.Column(db.Integer, db.ForeignKey("payments.id"), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    matched_invoice = db.relationship("Invoice", foreign_keys=[matched_invoice_id])
    matched_payment = db.relationship("Payment", foreign_keys=[matched_payment_id])

    def to_dict(self):
        return {
            "id": self.id,
            "account_label": self.account_label,
            "booking_date": self.booking_date.isoformat() if self.booking_date else None,
            "amount": float(self.amount) if self.amount is not None else None,
            "currency": self.currency,
            "counterparty": self.counterparty,
            "reference": self.reference,
            "match_status": self.match_status,
            "matched_invoice_id": self.matched_invoice_id,
            "matched_payment_id": self.matched_payment_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<BankTransaction {self.id} {self.amount} {self.currency} {self.match_status}>"
