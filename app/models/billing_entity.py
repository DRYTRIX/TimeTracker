"""Billing entities: the legal entities that issue invoices, and where clients pay them.

TimeTracker has one seller for the whole instance (``Settings.company_*``). A business that
invoices from several legal entities (a company, a sole trader, a subsidiary abroad) keeps each
of them here, with its own details, payment accounts and invoice defaults.

Part of the optional "Legal entities" module (``billing_entities``). With the module off, or
with no entity on an invoice, invoices fall back to ``Settings.company_*`` as before.
"""

from datetime import datetime

from app import db

STATUSES = ("active", "archived")


class BillingEntity(db.Model):
    """One of our legal entities that issues invoices."""

    __tablename__ = "billing_entities"

    id = db.Column(db.Integer, primary_key=True)
    short_name = db.Column(db.String(200), nullable=False, index=True)  # shown in lists
    legal_name = db.Column(db.String(255), nullable=False)  # printed on invoices
    country = db.Column(db.String(2), nullable=True)  # ISO 3166-1 alpha-2
    registration_number = db.Column(db.String(100), nullable=True)
    vat_number = db.Column(db.String(100), nullable=True)
    address = db.Column(db.Text, nullable=True)
    email = db.Column(db.String(200), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    website = db.Column(db.String(200), nullable=True)

    # Invoice defaults
    number_format = db.Column(db.String(120), nullable=True)  # e.g. "INV-{YYYY}-{SEQ}"
    number_counter = db.Column(db.Integer, nullable=False, default=0)  # used by {SEQ}
    default_vat_category = db.Column(db.String(5), nullable=True)
    default_tax_rate = db.Column(db.Numeric(5, 2), nullable=True)
    default_vat_exemption_code = db.Column(db.String(50), nullable=True)
    default_vat_exemption_reason = db.Column(db.Text, nullable=True)
    default_terms = db.Column(db.Text, nullable=True)
    default_notes = db.Column(db.Text, nullable=True)

    status = db.Column(db.String(20), nullable=False, default="active", index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    payment_accounts = db.relationship(
        "PaymentAccount",
        backref="billing_entity",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="PaymentAccount.currency",
    )

    def __repr__(self):
        return f"<BillingEntity {self.short_name}>"

    @property
    def is_active(self):
        return self.status == "active"

    def active_payment_accounts(self, currency=None):
        query = self.payment_accounts.filter_by(status="active")
        if currency:
            query = query.filter_by(currency=currency.upper())
        return query.all()

    def is_used(self):
        from app.models.invoice import Invoice

        return db.session.query(Invoice.id).filter(Invoice.billing_entity_id == self.id).first() is not None

    def seller_snapshot(self):
        """The 'From' block of an invoice, copied into the invoice when it is created."""
        return {
            "billing_entity_id": self.id,
            "legal_name": self.legal_name or self.short_name,
            "registration_number": self.registration_number or "",
            "vat_number": self.vat_number or "",
            "address": self.address or "",
            "country": self.country or "",
            "email": self.email or "",
            "phone": self.phone or "",
            "website": self.website or "",
        }


class PaymentAccount(db.Model):
    """Where clients pay a billing entity: one record per IBAN and currency.

    Only the fields the app needs are structured (currency, IBAN, status). Bank, SWIFT, beneficiary
    and intermediary banks are typed by hand as one text; ``{IBAN}`` in the text is replaced with
    ``iban``.
    """

    __tablename__ = "payment_accounts"
    __table_args__ = (db.UniqueConstraint("iban", "currency", name="uq_payment_accounts_iban_currency"),)

    id = db.Column(db.Integer, primary_key=True)
    billing_entity_id = db.Column(
        db.Integer, db.ForeignKey("billing_entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    currency = db.Column(db.String(3), nullable=False)
    iban = db.Column(db.String(64), nullable=False)
    bank_name = db.Column(db.String(120), nullable=True)  # short label for lists
    status = db.Column(db.String(20), nullable=False, default="active", index=True)
    details_text = db.Column(db.Text, nullable=True)  # as printed on documents, {IBAN} is filled in
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<PaymentAccount {self.iban} {self.currency}>"

    @property
    def is_active(self):
        return self.status == "active"

    @property
    def iban_short(self):
        iban = (self.iban or "").replace(" ", "")
        return f"{iban[:4]}…{iban[-4:]}" if len(iban) > 8 else iban

    @property
    def label(self):
        parts = [p for p in (self.bank_name, self.currency, self.iban_short) if p]
        return " · ".join(parts)

    @property
    def printed_text(self):
        """Payment details as printed on documents, with {IBAN} filled in."""
        return (self.details_text or "").replace("{IBAN}", self.iban or "")

    def is_used(self):
        from app.models.invoice import Invoice

        return db.session.query(Invoice.id).filter(Invoice.payment_account_id == self.id).first() is not None
