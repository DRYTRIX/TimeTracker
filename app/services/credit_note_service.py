"""Credit Note Service — Phase 3.

Provides high-level operations for creating, issuing, and querying credit notes.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app import db


class CreditNoteService:
    """Business logic for credit notes."""

    # ------------------------------------------------------------------
    # Creation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_credit_note(invoice: Any, user_id: int, reason: Optional[str] = None) -> Any:
        """Create a bare (not-yet-committed) CreditNote linked to *invoice*."""
        from app.models.payments import CreditNote
        from app.utils.invoice_numbering import allocate_next_credit_note_number

        credit_number = allocate_next_credit_note_number()
        cn = CreditNote(
            invoice_id=invoice.id,
            credit_number=credit_number,
            amount=Decimal("0"),
            reason=reason or "",
            created_by=user_id,
            status="draft",
            currency_code=getattr(invoice, "currency_code", "EUR") or "EUR",
            tax_rate=getattr(invoice, "tax_rate", Decimal("0")) or Decimal("0"),
            vat_category=getattr(invoice, "vat_category", None),
            notes=reason,
        )
        return cn

    @staticmethod
    def _copy_invoice_items(cn: Any, invoice: Any, qty_multiplier: Decimal = Decimal("1")) -> None:
        """Copy all line items from *invoice* to *cn*, scaling quantity by *qty_multiplier*."""
        from app.models.payments import CreditNoteItem

        line_items = invoice.items.all() if hasattr(invoice.items, "all") else list(invoice.items or [])
        for pos, item in enumerate(sorted(line_items, key=lambda x: getattr(x, "position", 0))):
            qty = Decimal(str(item.quantity or 1)) * qty_multiplier
            cni = CreditNoteItem(
                credit_note_id=cn.id,
                description=item.description,
                quantity=qty,
                unit_price=Decimal(str(item.unit_price or 0)),
                tax_rate=item.tax_rate,
                vat_category=item.vat_category,
                discount_percent=item.discount_percent,
                discount_amount=item.discount_amount,
                position=pos,
                invoice_item_id=item.id,
            )
            db.session.add(cni)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def create_full_credit(
        cls, invoice: Any, user_id: int, reason: Optional[str] = None, auto_issue: bool = True
    ) -> Any:
        """Create a full credit note for *invoice* covering all line items.

        When *auto_issue* is True (default) the credit note is immediately issued and
        the invoice status is set to 'cancelled' because the credit covers the full amount.
        """
        cn = cls._make_credit_note(invoice, user_id, reason)
        db.session.add(cn)
        db.session.flush()  # get cn.id

        cls._copy_invoice_items(cn, invoice)
        db.session.flush()

        cn.calculate_totals()

        if auto_issue:
            cls.issue_credit_note(cn)
            # Full credit → cancel the invoice
            if hasattr(invoice, "status"):
                invoice.status = "cancelled"

        db.session.commit()
        cls._emit_created(cn)
        return cn

    @classmethod
    def create_partial_credit(
        cls,
        invoice: Any,
        user_id: int,
        item_specs: List[Dict[str, Any]],
        reason: Optional[str] = None,
        auto_issue: bool = False,
    ) -> Any:
        """Create a partial credit note for selected lines.

        *item_specs* is a list of dicts with keys:
          - ``invoice_item_id`` (int): source line item id
          - ``quantity`` (Decimal|float|str): quantity to credit (defaults to full line qty)
        """
        from app.models.invoice import InvoiceItem
        from app.models.payments import CreditNoteItem

        cn = cls._make_credit_note(invoice, user_id, reason)
        db.session.add(cn)
        db.session.flush()

        spec_map: Dict[int, Decimal] = {}
        for spec in item_specs:
            iid = int(spec["invoice_item_id"])
            qty = Decimal(str(spec.get("quantity", 0)))
            spec_map[iid] = qty

        line_items = invoice.items.all() if hasattr(invoice.items, "all") else list(invoice.items or [])
        for pos, item in enumerate(sorted(line_items, key=lambda x: getattr(x, "position", 0))):
            if item.id not in spec_map:
                continue
            qty = spec_map[item.id] or Decimal(str(item.quantity or 1))
            cni = CreditNoteItem(
                credit_note_id=cn.id,
                description=item.description,
                quantity=qty,
                unit_price=Decimal(str(item.unit_price or 0)),
                tax_rate=item.tax_rate,
                vat_category=item.vat_category,
                discount_percent=item.discount_percent,
                discount_amount=item.discount_amount,
                position=pos,
                invoice_item_id=item.id,
            )
            db.session.add(cni)

        db.session.flush()
        cn.calculate_totals()

        if auto_issue:
            cls.issue_credit_note(cn)

        db.session.commit()
        cls._emit_created(cn)
        return cn

    @classmethod
    def create_amount_credit(
        cls,
        invoice: Any,
        user_id: int,
        amount: Any,
        reason: Optional[str] = None,
        description: Optional[str] = None,
        auto_issue: bool = False,
    ) -> Any:
        """Create a free-form single-line credit note for a given *amount*."""
        from app.models.payments import CreditNoteItem

        cn = cls._make_credit_note(invoice, user_id, reason)
        # Free-form amount is the total credit against outstanding (tax included /
        # no extra VAT layer), so keep tax_rate at 0 for this mode.
        cn.amount = Decimal(str(amount))
        cn.tax_rate = Decimal("0")
        db.session.add(cn)
        db.session.flush()

        cni = CreditNoteItem(
            credit_note_id=cn.id,
            description=description or reason or "Credit",
            quantity=Decimal("1"),
            unit_price=Decimal(str(amount)),
            tax_rate=Decimal("0"),
            vat_category=cn.vat_category,
            position=0,
        )
        db.session.add(cni)
        db.session.flush()

        cn.calculate_totals()

        if auto_issue:
            cls.issue_credit_note(cn)

        db.session.commit()
        cls._emit_created(cn)
        return cn

    @staticmethod
    def _emit_created(cn: Any) -> None:
        try:
            from app.constants import WebhookEvent
            from app.utils.invoice_events import emit_credit_note_event

            emit_credit_note_event(WebhookEvent.CREDIT_NOTE_CREATED.value, cn)
        except Exception:
            pass

    @staticmethod
    def issue_credit_note(cn: Any) -> None:
        """Mark a credit note as issued and set issue_date if not already set."""
        cn.status = "issued"
        if not cn.issue_date:
            cn.issue_date = date.today()

    @staticmethod
    def recalculate_invoice_outstanding(invoice: Any) -> None:
        """Recompute invoice outstanding_amount (triggers existing property; nothing to store)."""
        # The outstanding_amount property on Invoice already sums credits dynamically.
        # This is a no-op hook for callers that want explicit recalculation semantics.
        _ = invoice.outstanding_amount

    @staticmethod
    def get_credits_for_invoice(invoice_id: int) -> List[Any]:
        from app.models.payments import CreditNote

        return CreditNote.query.filter_by(invoice_id=invoice_id).order_by(CreditNote.created_at.desc()).all()
