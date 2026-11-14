from datetime import datetime, date as _date
from decimal import Decimal

from app import db


class Payment(db.Model):
    """Partial/full payments recorded against invoices."""

    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=False, index=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=True)  # If multi-currency per payment
    payment_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    method = db.Column(db.String(50), nullable=True)  # bank_transfer, cash, check, credit_card, paypal, stripe, etc.
    reference = db.Column(db.String(100), nullable=True)  # Transaction ID, check number, etc.
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default="completed", nullable=False)  # completed, pending, failed, refunded

    # Additional tracking fields
    received_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)  # User who recorded the payment
    gateway_transaction_id = db.Column(db.String(255), nullable=True)  # For payment gateway transactions
    gateway_fee = db.Column(db.Numeric(10, 2), nullable=True)  # Transaction fees
    net_amount = db.Column(db.Numeric(10, 2), nullable=True)  # Amount after fees

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    receiver = db.relationship("User", backref="received_payments", foreign_keys=[received_by])

    def __repr__(self):
        return f"<Payment {self.amount} {self.currency or 'EUR'} for invoice {self.invoice_id}>"

    def calculate_net_amount(self):
        """Calculate net amount after fees"""
        if self.gateway_fee:
            self.net_amount = self.amount - self.gateway_fee
        else:
            self.net_amount = self.amount

    def to_dict(self):
        """Convert payment to dictionary for API responses"""
        return {
            "id": self.id,
            "invoice_id": self.invoice_id,
            "amount": float(self.amount),
            "currency": self.currency,
            "payment_date": self.payment_date.isoformat() if self.payment_date else None,
            "method": self.method,
            "reference": self.reference,
            "notes": self.notes,
            "status": self.status,
            "received_by": self.received_by,
            "gateway_transaction_id": self.gateway_transaction_id,
            "gateway_fee": float(self.gateway_fee) if self.gateway_fee else None,
            "net_amount": float(self.net_amount) if self.net_amount else float(self.amount),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class CreditNote(db.Model):
    """Credit notes issued to offset invoices."""

    __tablename__ = "credit_notes"

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=False, index=True)
    credit_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    # Legacy flat amount field — preserved for backward compat; new code uses total_amount.
    amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    reason = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Extended fields (migration 212)
    status = db.Column(db.String(20), default="draft", nullable=False)
    issue_date = db.Column(db.Date, nullable=True)
    currency_code = db.Column(db.String(3), nullable=True, default="EUR")
    subtotal = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    tax_amount = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    total_amount = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    tax_rate = db.Column(db.Numeric(5, 2), nullable=True, default=0)
    vat_category = db.Column(db.String(5), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    # Relationships
    items = db.relationship(
        "CreditNoteItem", backref="credit_note", lazy="dynamic", cascade="all, delete-orphan"
    )
    creator = db.relationship("User", backref="created_credit_notes", foreign_keys=[created_by])

    def __repr__(self):
        return f"<CreditNote {self.credit_number} for invoice {self.invoice_id}>"

    # ------------------------------------------------------------------
    # Totals
    # ------------------------------------------------------------------

    def calculate_totals(self):
        """Recalculate subtotal / tax_amount / total_amount from line items.

        Falls back to the legacy `amount` field when there are no items.
        """
        line_items = self.items.all() if hasattr(self.items, "all") else list(self.items or [])
        if not line_items:
            # Legacy flat-amount mode
            subtotal = Decimal(str(self.amount or 0))
            rate = Decimal(str(self.tax_rate or 0))
            tax = (subtotal * rate / 100).quantize(Decimal("0.01"))
            self.subtotal = subtotal
            self.tax_amount = tax
            self.total_amount = subtotal + tax
            return

        subtotal = Decimal("0")
        tax_total = Decimal("0")
        for item in line_items:
            line_subtotal = Decimal(str(item.total_amount or 0))
            subtotal += line_subtotal
            item_rate = Decimal(str(item.tax_rate if item.tax_rate is not None else (self.tax_rate or 0)))
            tax_total += (line_subtotal * item_rate / 100).quantize(Decimal("0.01"))

        self.subtotal = subtotal
        self.tax_amount = tax_total
        self.total_amount = subtotal + tax_total
        # Keep legacy amount in sync
        self.amount = self.total_amount

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self, include_items=True):
        d = {
            "id": self.id,
            "invoice_id": self.invoice_id,
            "credit_number": self.credit_number,
            "status": self.status,
            "amount": float(self.amount or 0),
            "subtotal": float(self.subtotal or 0),
            "tax_amount": float(self.tax_amount or 0),
            "total_amount": float(self.total_amount or 0),
            "tax_rate": float(self.tax_rate or 0),
            "vat_category": self.vat_category,
            "currency_code": self.currency_code or "EUR",
            "reason": self.reason,
            "notes": self.notes,
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_items:
            line_items = self.items.all() if hasattr(self.items, "all") else list(self.items or [])
            d["items"] = [i.to_dict() for i in sorted(line_items, key=lambda x: x.position)]
        return d


class CreditNoteItem(db.Model):
    """Line item on a credit note."""

    __tablename__ = "credit_note_items"

    id = db.Column(db.Integer, primary_key=True)
    credit_note_id = db.Column(db.Integer, db.ForeignKey("credit_notes.id"), nullable=False, index=True)
    description = db.Column(db.String(500), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), nullable=False, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    tax_rate = db.Column(db.Numeric(5, 2), nullable=True)
    vat_category = db.Column(db.String(5), nullable=True)
    discount_percent = db.Column(db.Numeric(5, 2), nullable=True, default=0)
    discount_amount = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    position = db.Column(db.Integer, nullable=False, default=0)
    invoice_item_id = db.Column(db.Integer, db.ForeignKey("invoice_items.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Optional back-reference to source invoice item
    source_invoice_item = db.relationship("InvoiceItem", foreign_keys=[invoice_item_id])

    def __init__(
        self,
        credit_note_id,
        description,
        quantity,
        unit_price,
        tax_rate=None,
        vat_category=None,
        discount_percent=None,
        discount_amount=None,
        position=0,
        invoice_item_id=None,
    ):
        self.credit_note_id = credit_note_id
        self.description = description
        self.quantity = Decimal(str(quantity))
        self.unit_price = Decimal(str(unit_price))
        self.tax_rate = Decimal(str(tax_rate)) if tax_rate is not None else None
        self.vat_category = vat_category
        self.discount_percent = Decimal(str(discount_percent)) if discount_percent is not None else Decimal("0")
        self.discount_amount = Decimal(str(discount_amount)) if discount_amount is not None else Decimal("0")
        self.position = int(position) if position is not None else 0
        self.invoice_item_id = invoice_item_id
        self.total_amount = self.line_net

    @property
    def line_discount_total(self) -> Decimal:
        disc_amt = Decimal(str(self.discount_amount or 0))
        if disc_amt:
            return disc_amt
        disc_pct = Decimal(str(self.discount_percent or 0))
        if disc_pct:
            gross = Decimal(str(self.quantity or 1)) * Decimal(str(self.unit_price or 0))
            return (gross * disc_pct / 100).quantize(Decimal("0.01"))
        return Decimal("0")

    @property
    def line_net(self) -> Decimal:
        gross = Decimal(str(self.quantity or 1)) * Decimal(str(self.unit_price or 0))
        return max(Decimal("0"), gross - self.line_discount_total)

    def to_dict(self):
        return {
            "id": self.id,
            "credit_note_id": self.credit_note_id,
            "description": self.description,
            "quantity": float(self.quantity),
            "unit_price": float(self.unit_price),
            "total_amount": float(self.total_amount),
            "tax_rate": float(self.tax_rate) if self.tax_rate is not None else None,
            "vat_category": self.vat_category,
            "discount_percent": float(self.discount_percent or 0),
            "discount_amount": float(self.discount_amount or 0),
            "position": self.position,
            "invoice_item_id": self.invoice_item_id,
        }


class InvoiceReminderSchedule(db.Model):
    """Schedules to send invoice reminders before/after due dates."""

    __tablename__ = "invoice_reminder_schedules"

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=False, index=True)
    days_offset = db.Column(db.Integer, nullable=False)  # negative for before due, positive after
    recipients = db.Column(db.Text, nullable=True)  # comma-separated; default to client email if empty
    template_name = db.Column(db.String(100), nullable=True)
    active = db.Column(db.Boolean, default=True, nullable=False)
    last_sent_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<InvoiceReminderSchedule inv={self.invoice_id} offset={self.days_offset}>"
