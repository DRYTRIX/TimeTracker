from datetime import datetime
from decimal import Decimal

from app import db
from app.utils.invoice_numbering import allocate_next_invoice_number


class Invoice(db.Model):
    """Invoice model for client billing"""

    __tablename__ = "invoices"

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True)
    client_name = db.Column(db.String(200), nullable=False)
    client_email = db.Column(db.String(200), nullable=True)
    client_address = db.Column(db.Text, nullable=True)
    buyer_reference = db.Column(db.String(200), nullable=True)  # PEPPOL BT-10 / EN 16931
    # Link to clients table (enforced by DB schema)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False, index=True)
    quote_id = db.Column(db.Integer, db.ForeignKey("quotes.id"), nullable=True, index=True)

    # Invoice details
    issue_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(
        db.String(20), default="draft", nullable=False
    )  # 'draft', 'issued', 'sent', 'paid', 'overdue', 'cancelled'(void)

    # Billing information
    subtotal = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    tax_rate = db.Column(db.Numeric(5, 2), nullable=False, default=0)  # Percentage
    tax_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    currency_code = db.Column(db.String(3), nullable=False, default="EUR")
    template_id = db.Column(db.Integer, db.ForeignKey("invoice_templates.id"), nullable=True, index=True)
    recurring_invoice_id = db.Column(db.Integer, db.ForeignKey("recurring_invoices.id"), nullable=True, index=True)

    # Notes and terms
    notes = db.Column(db.Text, nullable=True)
    terms = db.Column(db.Text, nullable=True)

    # Payment tracking
    payment_date = db.Column(db.Date, nullable=True)
    payment_method = db.Column(
        db.String(50), nullable=True
    )  # 'cash', 'check', 'bank_transfer', 'credit_card', 'paypal', etc.
    payment_reference = db.Column(db.String(100), nullable=True)  # Transaction ID, check number, etc.
    payment_notes = db.Column(db.Text, nullable=True)
    amount_paid = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    payment_status = db.Column(
        db.String(20), nullable=False, default="unpaid"
    )  # 'unpaid', 'partially_paid', 'fully_paid', 'overpaid'

    # Per-invoice VAT category override for Factur-X / ZUGFeRD (nullable = use settings default)
    vat_category = db.Column(db.String(5), nullable=True)
    vat_exemption_reason = db.Column(db.Text, nullable=True)
    vat_exemption_code = db.Column(db.String(50), nullable=True)

    # Invoice-level discounts (applied after line discounts, before tax)
    discount_percent = db.Column(db.Numeric(5, 2), nullable=True, default=0)
    discount_amount = db.Column(db.Numeric(10, 2), nullable=True, default=0)

    # Italian public-administration procurement codes (FatturaPA DatiOrdineAcquisto)
    cig = db.Column(db.String(15), nullable=True)
    cup = db.Column(db.String(15), nullable=True)

    # Reminder policy (optional per-invoice override; falls back to client then default)
    reminder_policy_id = db.Column(db.Integer, db.ForeignKey("reminder_policies.id"), nullable=True)
    # Accumulated late fees added by the reminder service
    late_fee_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0, server_default="0")

    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    integration_metadata = db.Column(db.JSON, nullable=True)

    # Relationships
    project = db.relationship("Project", backref="invoices")
    client = db.relationship("Client", backref="invoices")
    quote = db.relationship("Quote", backref="invoices")
    creator = db.relationship("User", backref="created_invoices")
    items = db.relationship("InvoiceItem", backref="invoice", lazy="dynamic", cascade="all, delete-orphan")
    payments = db.relationship("Payment", backref="invoice", lazy="dynamic", cascade="all, delete-orphan")
    credits = db.relationship("CreditNote", backref="invoice", lazy="dynamic", cascade="all, delete-orphan")
    reminder_schedules = db.relationship(
        "InvoiceReminderSchedule", backref="invoice", lazy="dynamic", cascade="all, delete-orphan"
    )
    template = db.relationship("InvoiceTemplate", backref="invoices", lazy="joined")
    extra_goods = db.relationship("ExtraGood", backref="invoice", lazy="dynamic", cascade="all, delete-orphan")

    def __init__(self, invoice_number, project_id, client_name, due_date, created_by, client_id, **kwargs):
        self.invoice_number = invoice_number
        self.project_id = project_id
        self.client_name = client_name
        self.due_date = due_date
        self.created_by = created_by
        self.client_id = client_id
        self.quote_id = kwargs.get("quote_id")

        # Set optional fields
        self.client_email = kwargs.get("client_email")
        self.client_address = kwargs.get("client_address")
        self.buyer_reference = kwargs.get("buyer_reference")
        self.issue_date = kwargs.get("issue_date", datetime.utcnow().date())
        self.notes = kwargs.get("notes")
        self.terms = kwargs.get("terms")
        self.tax_rate = Decimal(str(kwargs.get("tax_rate", 0)))
        self.currency_code = kwargs.get("currency_code") or self.currency_code
        self.template_id = kwargs.get("template_id") if kwargs.get("template_id") else None

        # Set payment tracking fields
        self.payment_date = kwargs.get("payment_date")
        self.payment_method = kwargs.get("payment_method")
        self.payment_reference = kwargs.get("payment_reference")
        self.payment_notes = kwargs.get("payment_notes")
        self.amount_paid = Decimal(str(kwargs.get("amount_paid", 0)))
        self.payment_status = kwargs.get("payment_status", "unpaid")
        self.vat_category = kwargs.get("vat_category")
        self.vat_exemption_reason = kwargs.get("vat_exemption_reason")
        self.vat_exemption_code = kwargs.get("vat_exemption_code")
        self.cig = kwargs.get("cig")
        self.cup = kwargs.get("cup")
        if "discount_percent" in kwargs and kwargs.get("discount_percent") is not None:
            self.discount_percent = Decimal(str(kwargs["discount_percent"]))
        if "discount_amount" in kwargs and kwargs.get("discount_amount") is not None:
            self.discount_amount = Decimal(str(kwargs["discount_amount"]))
        if "subtotal" in kwargs and kwargs.get("subtotal") is not None:
            self.subtotal = Decimal(str(kwargs["subtotal"]))
        if "tax_amount" in kwargs and kwargs.get("tax_amount") is not None:
            self.tax_amount = Decimal(str(kwargs["tax_amount"]))
        if "total_amount" in kwargs and kwargs.get("total_amount") is not None:
            self.total_amount = Decimal(str(kwargs["total_amount"]))

    def __repr__(self):
        return f"<Invoice {self.invoice_number} ({self.client_name})>"

    @property
    def is_overdue(self):
        """Check if invoice is overdue"""
        return self.status in ["sent", "issued", "overdue"] and datetime.utcnow().date() > self.due_date

    @property
    def days_overdue(self):
        """Calculate days overdue"""
        if not self.is_overdue:
            return 0
        return (datetime.utcnow().date() - self.due_date).days

    @property
    def is_paid(self):
        """Check if invoice is fully paid"""
        return self.payment_status == "fully_paid"

    @property
    def is_partially_paid(self):
        """Check if invoice is partially paid"""
        return self.payment_status == "partially_paid"

    @property
    def outstanding_amount(self):
        """Calculate outstanding amount including any accrued late fees."""
        credits_total = sum((c.amount for c in self.credits), Decimal("0")) if self.credits else Decimal("0")
        late_fee = Decimal(str(self.late_fee_amount or 0))
        return self.total_amount + late_fee - (self.amount_paid or 0) - credits_total

    @property
    def payment_percentage(self):
        """Calculate payment percentage"""
        if self.total_amount == 0:
            return 0
        return float((self.amount_paid or 0) / self.total_amount * 100)

    @property
    def sorted_payments(self):
        """Get payments sorted by payment_date and created_at (newest first)"""
        from app.models.payments import Payment

        return self.payments.order_by(Payment.payment_date.desc(), Payment.created_at.desc()).all()

    def update_payment_status(self):
        """Update payment status based on amount paid"""
        if not self.amount_paid or self.amount_paid == 0:
            self.payment_status = "unpaid"
        elif self.amount_paid >= self.total_amount:
            if self.amount_paid > self.total_amount:
                self.payment_status = "overpaid"
            else:
                self.payment_status = "fully_paid"
        else:
            self.payment_status = "partially_paid"

    def record_payment(
        self, amount, payment_date=None, payment_method=None, payment_reference=None, payment_notes=None
    ):
        """
        DEPRECATED: Record a payment for this invoice.

        This method is deprecated. Please use the Payment model (app.models.Payment)
        to record payments instead. The Payment model provides:
        - Multiple payment tracking per invoice
        - Payment status management (completed, pending, failed, refunded)
        - Gateway fee tracking
        - Better audit trail

        This method is kept for backwards compatibility only and may be removed in a future version.
        """
        import warnings

        warnings.warn(
            "Invoice.record_payment() is deprecated. Use the Payment model instead.", DeprecationWarning, stacklevel=2
        )

        self.amount_paid = (self.amount_paid or 0) + Decimal(str(amount))
        self.payment_date = payment_date or datetime.utcnow().date()
        if payment_method:
            self.payment_method = payment_method
        if payment_reference:
            self.payment_reference = payment_reference
        if payment_notes:
            self.payment_notes = payment_notes

        self.update_payment_status()

        # Update invoice status based on payment
        if self.payment_status == "fully_paid":
            self.status = "paid"
        elif self.payment_status in ["partially_paid", "overpaid"]:
            # Keep current status but ensure it's not 'paid' if only partially paid
            if self.payment_status == "partially_paid" and self.status == "paid":
                self.status = "sent"

    def release_invoiced_costs_and_expenses(self):
        """Make this invoice's project costs, expenses and prepaid hours billable again.

        Call before deleting the invoice. The database only clears their
        ``invoice_id``; ``invoiced`` would stay True and keep them off every
        later invoice.

        Prepaid hours used by the invoice are given back the same way
        ``PrepaidHoursAllocator`` does before it recalculates an invoice: the
        consumption rows are removed and their time entries are billable again.
        Otherwise fully prepaid entries stay non-billable and are left off later
        invoices, and the rows, left without an invoice, still count against the
        client's prepaid hours and make invoicing their entries again fail on the
        unique ``time_entry_id``.
        """
        from .client_prepaid_consumption import ClientPrepaidConsumption
        from .project_cost import ProjectCost
        from .time_entry import TimeEntry

        for cost in ProjectCost.query.filter_by(invoice_id=self.id).all():
            cost.unmark_as_invoiced()
        for expense in self.expenses.all():
            expense.unmark_as_invoiced()

        consumptions = ClientPrepaidConsumption.query.filter_by(invoice_id=self.id).all()
        entry_ids = [consumption.time_entry_id for consumption in consumptions]
        if entry_ids:
            for entry in TimeEntry.query.filter(TimeEntry.id.in_(entry_ids)).all():
                entry.billable = True
        for consumption in consumptions:
            db.session.delete(consumption)

    def calculate_totals(self):
        """Calculate invoice totals from items, extra goods, and expenses.

        Supports per-line tax rates (item.tax_rate), per-line discounts
        (item.discount_percent / item.discount_amount), and invoice-level
        discounts (self.discount_percent / self.discount_amount).

        Groups taxable amounts by (vat_category, rate) so multi-rate invoices
        produce a correct tax_breakdown() for e-invoice exporters.
        """
        # Optionally apply tax rules before totals (failures logged inside helper)
        self._apply_tax_rules_if_any()

        # --- Per-item line nets ---
        items_net = Decimal("0")
        # Build tax groups keyed by (vat_category, rate)
        tax_groups: dict = {}
        inv_tax_rate = Decimal(str(self.tax_rate or 0))
        inv_vat_cat = (self.vat_category or "S").upper()

        try:
            for item in self.items:
                lnet = item.line_net
                items_net += lnet
                rate = item.effective_tax_rate(self)
                cat = (item.vat_category or inv_vat_cat).upper()
                key = (cat, rate)
                tax_groups[key] = tax_groups.get(key, Decimal("0")) + lnet
        except Exception:
            # Fallback: use stored total_amount for each item without grouping
            items_net = sum(item.total_amount for item in self.items)
            tax_groups = {(inv_vat_cat, inv_tax_rate): items_net}

        # --- Goods & expenses use invoice-level tax ---
        goods_total = Decimal("0")
        expenses_total = Decimal("0")
        try:
            goods_total = sum(good.total_amount for good in self.extra_goods)
        except Exception:
            pass
        try:
            expenses_total = sum(expense.total_amount for expense in self.expenses)
        except Exception:
            pass

        inv_other = goods_total + expenses_total
        if inv_other:
            key = (inv_vat_cat, inv_tax_rate)
            tax_groups[key] = tax_groups.get(key, Decimal("0")) + inv_other

        combined_net = items_net + goods_total + expenses_total

        # --- Invoice-level discount ---
        inv_disc = Decimal(str(self.discount_amount or 0))
        if not inv_disc:
            inv_disc_pct = Decimal(str(self.discount_percent or 0))
            if inv_disc_pct and combined_net:
                inv_disc = combined_net * (inv_disc_pct / 100)

        subtotal = combined_net - inv_disc
        self.subtotal = subtotal

        # Distribute invoice discount proportionally across tax groups
        if inv_disc and combined_net:
            disc_ratio = inv_disc / combined_net
            tax_groups = {k: v * (1 - disc_ratio) for k, v in tax_groups.items()}

        # --- Compute tax ---
        tax_amount = Decimal("0")
        for (cat, rate), taxable in tax_groups.items():
            tax_amount += taxable * (rate / 100)

        self.tax_amount = tax_amount.quantize(Decimal("0.01"))
        self.total_amount = subtotal + self.tax_amount

        # Update status if overdue
        if self.status == "sent" and self.is_overdue:
            self.status = "overdue"

    def tax_breakdown(self):
        """Return per-rate tax grouping suitable for e-invoice exporters.

        Returns a list of dicts sorted by (category, rate):
            [{"category": "S", "rate": 20.0, "taxable": 100.00, "tax": 20.00}, ...]
        """
        inv_tax_rate = Decimal(str(self.tax_rate or 0))
        inv_vat_cat = (self.vat_category or "S").upper()
        groups: dict = {}

        try:
            for item in self.items:
                lnet = item.line_net
                rate = item.effective_tax_rate(self)
                cat = (item.vat_category or inv_vat_cat).upper()
                key = (cat, rate)
                groups[key] = groups.get(key, Decimal("0")) + lnet
        except Exception:
            groups = {(inv_vat_cat, inv_tax_rate): sum(item.total_amount for item in self.items)}

        try:
            goods_total = sum(good.total_amount for good in self.extra_goods)
        except Exception:
            goods_total = Decimal("0")
        try:
            expenses_total = sum(expense.total_amount for expense in self.expenses)
        except Exception:
            expenses_total = Decimal("0")

        inv_other = goods_total + expenses_total
        if inv_other:
            key = (inv_vat_cat, inv_tax_rate)
            groups[key] = groups.get(key, Decimal("0")) + inv_other

        # Apply invoice discount proportionally
        combined = sum(groups.values())
        inv_disc = Decimal(str(self.discount_amount or 0))
        if not inv_disc:
            inv_disc_pct = Decimal(str(self.discount_percent or 0))
            if inv_disc_pct and combined:
                inv_disc = combined * (inv_disc_pct / 100)
        if inv_disc and combined:
            disc_ratio = inv_disc / combined
            groups = {k: v * (1 - disc_ratio) for k, v in groups.items()}

        result = []
        for (cat, rate), taxable in sorted(groups.items(), key=lambda x: (x[0][0], float(x[0][1]))):
            taxable_q = taxable.quantize(Decimal("0.01"))
            tax_q = (taxable * (rate / 100)).quantize(Decimal("0.01"))
            result.append(
                {
                    "category": cat,
                    "rate": float(rate),
                    "taxable": float(taxable_q),
                    "tax": float(tax_q),
                }
            )
        return result

    def _apply_tax_rules_if_any(self):
        """Apply matching tax rule to set `tax_rate` if applicable.
        Chooses the most specific active rule by client->project->country/region.
        """
        try:
            from .tax_rule import TaxRule  # local import to avoid circular

            today = self.issue_date or datetime.utcnow().date()
            query = TaxRule.query.filter(TaxRule.active == True)
            # constrain by date range
            query = query.filter(
                (TaxRule.start_date.is_(None) | (TaxRule.start_date <= today)),
                (TaxRule.end_date.is_(None) | (TaxRule.end_date >= today)),
            )
            candidates = []
            # project-specific
            if self.project_id:
                candidates = query.filter(TaxRule.project_id == self.project_id).all()
            # client-specific
            if not candidates and self.client_id:
                candidates = query.filter(TaxRule.client_id == self.client_id).all()
            # no direct client/project, fallback to country/region — requires client meta; skip if unavailable
            # choose first if any
            if candidates:
                # prefer highest rate if multiple
                candidates.sort(key=lambda r: float(r.rate_percent), reverse=True)
                self.tax_rate = Decimal(str(candidates[0].rate_percent))
        except Exception as exc:
            import logging

            from sqlalchemy.exc import SQLAlchemyError

            logging.getLogger(__name__).warning(
                "Best-effort tax rule lookup failed for invoice %s",
                getattr(self, "id", None),
                exc_info=True,
            )
            if isinstance(exc, SQLAlchemyError):
                try:
                    db.session.rollback()
                except Exception:
                    logging.getLogger(__name__).debug("Rollback after tax-rule DB error also failed", exc_info=True)

    def to_dict(self):
        """Convert invoice to dictionary for API responses"""
        return {
            "id": self.id,
            "invoice_number": self.invoice_number,
            "project_id": self.project_id,
            "client_name": self.client_name,
            "client_email": self.client_email,
            "client_address": self.client_address,
            "buyer_reference": self.buyer_reference,
            "client_id": self.client_id,
            "quote_id": self.quote_id,
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "status": self.status,
            "subtotal": float(self.subtotal),
            "tax_rate": float(self.tax_rate),
            "tax_amount": float(self.tax_amount),
            "total_amount": float(self.total_amount),
            "discount_percent": float(self.discount_percent) if self.discount_percent else 0,
            "discount_amount": float(self.discount_amount) if self.discount_amount else 0,
            "vat_category": getattr(self, "vat_category", None),
            "vat_exemption_reason": getattr(self, "vat_exemption_reason", None),
            "vat_exemption_code": getattr(self, "vat_exemption_code", None),
            "notes": self.notes,
            "terms": self.terms,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_overdue": self.is_overdue,
            "days_overdue": self.days_overdue,
            # Payment tracking fields
            "payment_date": self.payment_date.isoformat() if self.payment_date else None,
            "payment_method": self.payment_method,
            "payment_reference": self.payment_reference,
            "payment_notes": self.payment_notes,
            "amount_paid": float(self.amount_paid) if self.amount_paid else 0,
            "payment_status": self.payment_status,
            "is_paid": self.is_paid,
            "is_partially_paid": self.is_partially_paid,
            "outstanding_amount": float(self.outstanding_amount),
            "payment_percentage": self.payment_percentage,
        }

    @classmethod
    def generate_invoice_number(cls):
        """Allocate a unique invoice number (locks Settings; caller still inserts)."""
        return allocate_next_invoice_number(cls)


class InvoiceItem(db.Model):
    """Invoice line item model"""

    __tablename__ = "invoice_items"

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=False, index=True)

    # Item details
    description = db.Column(db.String(500), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), nullable=False, default=1)  # Hours
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)  # Hourly rate
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)

    # Per-line tax (nullable → falls back to invoice.tax_rate)
    tax_rate = db.Column(db.Numeric(5, 2), nullable=True)
    vat_category = db.Column(db.String(5), nullable=True)

    # Per-line discounts (discount_amount takes priority over discount_percent)
    discount_percent = db.Column(db.Numeric(5, 2), nullable=True, default=0)
    discount_amount = db.Column(db.Numeric(10, 2), nullable=True, default=0)

    # Ordering (lower = first)
    position = db.Column(db.Integer, nullable=True, default=0, server_default="0")

    # Time entry reference (optional)
    time_entry_ids = db.Column(db.Text, nullable=True)  # Comma-separated IDs

    # Inventory integration
    stock_item_id = db.Column(db.Integer, db.ForeignKey("stock_items.id"), nullable=True, index=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"), nullable=True)
    is_stock_item = db.Column(db.Boolean, default=False, nullable=False)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    stock_item = db.relationship("StockItem", foreign_keys=[stock_item_id], lazy="joined")
    warehouse = db.relationship("Warehouse", foreign_keys=[warehouse_id], lazy="joined")

    def __init__(
        self,
        invoice_id,
        description,
        quantity,
        unit_price,
        time_entry_ids=None,
        stock_item_id=None,
        warehouse_id=None,
        tax_rate=None,
        vat_category=None,
        discount_percent=None,
        discount_amount=None,
        position=0,
    ):
        self.invoice_id = invoice_id
        self.description = description
        self.quantity = Decimal(str(quantity))
        self.unit_price = Decimal(str(unit_price))
        self.tax_rate = Decimal(str(tax_rate)) if tax_rate is not None else None
        self.vat_category = vat_category
        self.discount_percent = Decimal(str(discount_percent)) if discount_percent is not None else Decimal("0")
        self.discount_amount = Decimal(str(discount_amount)) if discount_amount is not None else Decimal("0")
        self.position = int(position) if position is not None else 0
        # total_amount = line net after discount
        self.total_amount = self.line_net
        self.time_entry_ids = time_entry_ids
        self.stock_item_id = stock_item_id
        self.warehouse_id = warehouse_id
        self.is_stock_item = stock_item_id is not None

    def __repr__(self):
        return f"<InvoiceItem {self.description} ({self.quantity}h @ {self.unit_price})>"

    @property
    def line_discount_total(self) -> Decimal:
        """The absolute discount amount applied to this line."""
        disc_amt = Decimal(str(self.discount_amount or 0))
        if disc_amt:
            return disc_amt
        disc_pct = Decimal(str(self.discount_percent or 0))
        if disc_pct:
            gross = Decimal(str(self.quantity or 0)) * Decimal(str(self.unit_price or 0))
            return gross * (disc_pct / 100)
        return Decimal("0")

    @property
    def line_net(self) -> Decimal:
        """Net line amount after discount (qty × unit_price − line_discount_total)."""
        gross = Decimal(str(self.quantity or 0)) * Decimal(str(self.unit_price or 0))
        return gross - self.line_discount_total

    def effective_tax_rate(self, invoice) -> Decimal:
        """Return this item's tax rate, falling back to the invoice-level rate."""
        if self.tax_rate is not None:
            return Decimal(str(self.tax_rate))
        return Decimal(str(getattr(invoice, "tax_rate", 0) or 0))

    @property
    def task_name_from_time_entries(self):
        """Task name from first linked time entry, or None for project-level groups."""
        if not self.time_entry_ids:
            return None
        first_id = self.time_entry_ids.split(",")[0].strip()
        if not first_id:
            return None
        try:
            from app.models import TimeEntry

            entry = TimeEntry.query.get(int(first_id))
            if entry and entry.task:
                return entry.task.name
            return None
        except (ValueError, TypeError):
            return None

    def to_dict(self):
        """Convert invoice item to dictionary"""
        return {
            "id": self.id,
            "invoice_id": self.invoice_id,
            "description": self.description,
            "quantity": float(self.quantity),
            "unit_price": float(self.unit_price),
            "total_amount": float(self.total_amount),
            "tax_rate": float(self.tax_rate) if self.tax_rate is not None else None,
            "vat_category": self.vat_category,
            "discount_percent": float(self.discount_percent) if self.discount_percent else 0,
            "discount_amount": float(self.discount_amount) if self.discount_amount else 0,
            "position": self.position or 0,
            "time_entry_ids": self.time_entry_ids,
            "stock_item_id": self.stock_item_id,
            "warehouse_id": self.warehouse_id,
            "is_stock_item": self.is_stock_item,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
