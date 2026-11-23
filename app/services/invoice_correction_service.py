"""Correct an issued invoice: cancel it, or cancel it and reissue its lines as a new draft.

An issued invoice keeps its lines and amounts. To change them, the invoice is cancelled with a reason
and, for "Cancel and reissue", copied into a new draft with the next number: same header, lines,
expenses, project costs and extra goods, and the same time entries with the same hours. The
cancelled invoice stays in the list and keeps its number.

The reason goes to the audit trail (``AuditLog.reason``), on the cancelled invoice's status change and
on the new draft, which is how the draft knows what it replaces.
"""

from __future__ import annotations

from collections import OrderedDict
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from app import db
from app.models import Invoice, InvoiceItem, InvoiceTimeLink

# An invoice that may be corrected: issued and not yet paid or cancelled
CORRECTABLE_STATUSES = ("issued", "sent", "overdue")

AUDIT_ENTITY = "Invoice"
REISSUE_FIELD = "reissue_of"
REASON_MAX_LENGTH = 1000


class InvoiceCorrectionError(ValueError):
    """The invoice cannot be corrected as asked."""

    code = "invoice_correction_error"


class CancelReasonRequiredError(InvoiceCorrectionError):
    code = "reason_required"

    def __init__(self):
        super().__init__("A reason is required to cancel an issued invoice")


class InvoiceNotCorrectableError(InvoiceCorrectionError):
    code = "invalid_status"

    def __init__(self, invoice: Invoice):
        self.invoice = invoice
        super().__init__(
            f"Invoice {invoice.invoice_number} is {invoice.status or 'draft'}; "
            "only an issued, sent or overdue invoice can be cancelled or reissued"
        )


class InvoiceHasPaymentsError(InvoiceCorrectionError):
    code = "has_payments"
    message = "This invoice has payments; use a credit note"

    def __init__(self, invoice: Invoice):
        self.invoice = invoice
        super().__init__(self.message)


class InvoiceCorrectionService:
    """Cancel, or cancel and reissue, an issued invoice. The caller commits."""

    # ------------------------------------------------------------------
    # Readers
    # ------------------------------------------------------------------
    @staticmethod
    def can_correct(invoice: Invoice) -> bool:
        """The status allows a correction (the Correct menu is shown)."""
        return (invoice.status or "draft") in CORRECTABLE_STATUSES

    @staticmethod
    def has_payments(invoice: Invoice) -> bool:
        """Money was received on the invoice: it can only be credited, not cancelled or reissued."""
        from app.models.payments import Payment

        if Decimal(str(invoice.amount_paid or 0)) > 0:
            return True
        if invoice.id is None:
            return False
        return invoice.payments.filter(Payment.status == "completed").first() is not None

    @staticmethod
    def reissue_of(invoice: Invoice) -> Optional[Dict]:
        """``{"invoice": cancelled invoice or None, "number": its number, "reason": ...}`` for a reissued draft."""
        from app.models.audit_log import AuditLog

        row = (
            AuditLog.query.filter(
                AuditLog.entity_type == AUDIT_ENTITY,
                AuditLog.entity_id == invoice.id,
                AuditLog.field_name == REISSUE_FIELD,
            )
            .order_by(AuditLog.id.desc())
            .first()
        )
        if row is None:
            return None
        meta = row.get_entity_metadata() or {}
        original = db.session.get(Invoice, meta.get("invoice_id")) if meta.get("invoice_id") else None
        return {
            "invoice": original,
            "number": original.invoice_number if original else meta.get("invoice_number"),
            "reason": row.reason,
        }

    @staticmethod
    def cancellation(invoice: Invoice) -> Optional[Dict]:
        """``{"reason": ..., "reissued_as": new draft or None}`` for an invoice cancelled here, else None."""
        from app.models.audit_log import AuditLog

        if invoice.status != "cancelled":
            return None
        row = (
            AuditLog.query.filter(
                AuditLog.entity_type == AUDIT_ENTITY,
                AuditLog.entity_id == invoice.id,
                AuditLog.field_name == "status",
                AuditLog.reason.isnot(None),
            )
            .order_by(AuditLog.id.desc())
            .first()
        )
        if row is None:
            return None
        meta = row.get_entity_metadata() or {}
        reissued = db.session.get(Invoice, meta.get("reissued_as_id")) if meta.get("reissued_as_id") else None
        return {"reason": row.reason, "reissued_as": reissued}

    # ------------------------------------------------------------------
    # Writers
    # ------------------------------------------------------------------
    def cancel(self, invoice: Invoice, reason: str, user_id: Optional[int]) -> Invoice:
        """Cancel an issued invoice. Its time entries, expenses, costs and prepaid hours are released."""
        reason = self._require(invoice, reason)
        previous_status = invoice.status
        self._cancel(invoice, user_id)
        self._log_cancel(invoice, previous_status, reason, user_id)
        db.session.flush()
        return invoice

    def reissue(self, invoice: Invoice, reason: str, user_id: Optional[int]) -> Invoice:
        """Cancel an issued invoice and copy it into a new draft with the next number. Returns the draft.

        The draft gets the same header, lines (as edited on the invoice), extra goods, expenses and
        project costs, and new links for the same time entries with the same hours. Prepaid hours
        the invoice used move to the draft as they are.
        """
        from app.models import ClientPrepaidConsumption, ProjectCost
        from app.services.invoice_time_service import InvoiceTimeService

        reason = self._require(invoice, reason)
        times = InvoiceTimeService()
        previous_status = invoice.status

        # What the invoice bills now, read before the cancellation releases it
        lines, prepaid = self._time_links(invoice)
        items = invoice.items.order_by(InvoiceItem.position.asc(), InvoiceItem.id.asc()).all()
        costs = ProjectCost.query.filter(ProjectCost.invoice_id == invoice.id).all()
        expenses = invoice.expenses.all()
        consumptions = ClientPrepaidConsumption.query.filter(ClientPrepaidConsumption.invoice_id == invoice.id).all()

        draft = self._copy_header(invoice, user_id)
        db.session.add(draft)
        db.session.flush()

        new_items: Dict[int, InvoiceItem] = {}
        for item in items:
            copy = InvoiceItem(
                invoice_id=draft.id,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                stock_item_id=item.stock_item_id,
                warehouse_id=item.warehouse_id,
                tax_rate=item.tax_rate,
                vat_category=item.vat_category,
                discount_percent=item.discount_percent,
                discount_amount=item.discount_amount,
                position=item.position,
            )
            copy.is_stock_item = item.is_stock_item
            db.session.add(copy)
            new_items[item.id] = copy
        self._copy_extra_goods(invoice, draft, user_id)
        db.session.flush()

        # Move what stays billed to the draft, so cancelling the invoice does not release it
        for cost in costs:
            cost.mark_as_invoiced(draft.id)
        for expense in expenses:
            expense.mark_as_invoiced(draft.id)
        for consumption in consumptions:
            consumption.invoice_id = draft.id
        db.session.flush()

        self._cancel(invoice, user_id)

        # The same entries, with the same hours, on the copied lines
        for item_id, pairs in lines.items():
            times.link_entries(draft, new_items[item_id], pairs, created_by=user_id)
        if prepaid:
            times.link_entries(draft, None, prepaid, created_by=user_id)

        draft.calculate_totals()
        self._log_cancel(invoice, previous_status, reason, user_id, reissued_as=draft)
        self._log_reissue(draft, invoice, reason, user_id)
        db.session.flush()
        return draft

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _cancel(invoice: Invoice, user_id: Optional[int]) -> None:
        """Cancel through ``InvoiceService.transition_status``: it releases the invoice's hours, costs and expenses."""
        from app.services import InvoiceService

        result = InvoiceService().transition_status(invoice, "cancelled", actor_id=user_id)
        if not result.get("success"):
            raise InvoiceCorrectionError(result.get("message") or "Could not cancel the invoice")

    def _require(self, invoice: Invoice, reason: Optional[str]) -> str:
        if not self.can_correct(invoice):
            raise InvoiceNotCorrectableError(invoice)
        if self.has_payments(invoice):
            raise InvoiceHasPaymentsError(invoice)
        reason = (reason or "").strip()
        if not reason:
            raise CancelReasonRequiredError()
        return reason[:REASON_MAX_LENGTH]

    @staticmethod
    def _time_links(invoice: Invoice) -> Tuple["OrderedDict[int, List[Tuple]]", List[Tuple]]:
        """Active links of the invoice: ``{item_id: [(entry, hours)]}`` and ``[(entry, hours)]`` without a line."""
        lines: "OrderedDict[int, List[Tuple]]" = OrderedDict()
        prepaid: List[Tuple] = []
        links = (
            InvoiceTimeLink.query.filter(
                InvoiceTimeLink.invoice_id == invoice.id, InvoiceTimeLink.released_at.is_(None)
            )
            .order_by(InvoiceTimeLink.id.asc())
            .all()
        )
        for link in links:
            pair = (link.time_entry, Decimal(link.hours))
            if link.invoice_item_id is None:
                prepaid.append(pair)
            else:
                lines.setdefault(link.invoice_item_id, []).append(pair)
        return lines, prepaid

    @staticmethod
    def _next_number(invoice: Invoice) -> str:
        """Next number of the invoice's legal entity (for the same billing period), else the global sequence."""
        entity = invoice.billing_entity
        if entity is not None and (entity.number_format or "").strip():
            from app.utils import billing_entities as billing

            try:
                number = billing.allocate_invoice_number(entity, invoice.issue_date)
            except billing.NumberTaken as taken:
                number = taken.next_free
                if number:
                    billing.claim_number(entity, number, invoice.issue_date)
            if number:
                return number
        return Invoice.generate_invoice_number()

    def _copy_header(self, invoice: Invoice, user_id: Optional[int]) -> Invoice:
        draft = Invoice(
            invoice_number=self._next_number(invoice),
            project_id=invoice.project_id,
            client_name=invoice.client_name,
            due_date=invoice.due_date,
            created_by=user_id or invoice.created_by,
            client_id=invoice.client_id,
            client_email=invoice.client_email,
            client_address=invoice.client_address,
            buyer_reference=invoice.buyer_reference,
            issue_date=invoice.issue_date,
            notes=invoice.notes,
            terms=invoice.terms,
            tax_rate=invoice.tax_rate,
            currency_code=invoice.currency_code,
            template_id=invoice.template_id,
            quote_id=invoice.quote_id,
            vat_category=invoice.vat_category,
            vat_exemption_reason=invoice.vat_exemption_reason,
            vat_exemption_code=invoice.vat_exemption_code,
            cig=invoice.cig,
            cup=invoice.cup,
            discount_percent=invoice.discount_percent,
            discount_amount=invoice.discount_amount,
        )
        draft.status = "draft"
        draft.client_entity_id = invoice.client_entity_id
        draft.buyer_snapshot = invoice.buyer_snapshot
        draft.billing_entity_id = invoice.billing_entity_id
        draft.payment_account_id = invoice.payment_account_id
        draft.seller_snapshot = invoice.seller_snapshot
        draft.payment_details_text = invoice.payment_details_text
        draft.reminder_policy_id = invoice.reminder_policy_id
        return draft

    @staticmethod
    def _copy_extra_goods(invoice: Invoice, draft: Invoice, user_id: Optional[int]) -> None:
        from app.models import ExtraGood

        for good in invoice.extra_goods.all():
            db.session.add(
                ExtraGood(
                    name=good.name,
                    description=good.description,
                    category=good.category,
                    quantity=good.quantity,
                    unit_price=good.unit_price,
                    sku=good.sku,
                    invoice_id=draft.id,
                    created_by=user_id or good.created_by,
                    currency_code=good.currency_code,
                    billable=good.billable,
                    stock_item_id=good.stock_item_id,
                )
            )

    @staticmethod
    def _log_cancel(
        invoice: Invoice,
        previous_status: Optional[str],
        reason: str,
        user_id: Optional[int],
        reissued_as: Optional[Invoice] = None,
    ) -> None:
        from app.models.audit_log import AuditLog

        meta = {"reissued_as_id": reissued_as.id, "reissued_as": reissued_as.invoice_number} if reissued_as else {}
        description = f"Cancelled invoice {invoice.invoice_number}"
        if reissued_as is not None:
            description += f" and reissued it as {reissued_as.invoice_number}"
        AuditLog.log_change(
            user_id=user_id,
            action="updated",
            entity_type=AUDIT_ENTITY,
            entity_id=invoice.id,
            field_name="status",
            old_value=previous_status,
            new_value="cancelled",
            entity_name=invoice.invoice_number,
            change_description=description,
            reason=reason,
            entity_metadata=meta or None,
        )

    @staticmethod
    def _log_reissue(draft: Invoice, invoice: Invoice, reason: str, user_id: Optional[int]) -> None:
        from app.models.audit_log import AuditLog

        AuditLog.log_change(
            user_id=user_id,
            action="created",
            entity_type=AUDIT_ENTITY,
            entity_id=draft.id,
            field_name=REISSUE_FIELD,
            new_value=invoice.invoice_number,
            entity_name=draft.invoice_number,
            change_description=f"Reissue of invoice {invoice.invoice_number}",
            reason=reason,
            entity_metadata={"invoice_id": invoice.id, "invoice_number": invoice.invoice_number},
        )
