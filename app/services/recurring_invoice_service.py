"""
Service for recurring invoice business logic (generation from template, list, get).
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app import db
from app.models import Invoice, InvoiceItem, RecurringInvoice, Settings, TimeEntry
from app.repositories.recurring_invoice_repository import RecurringInvoiceRepository


class RecurringInvoiceService:
    """Service for recurring invoice operations."""

    def __init__(self):
        self.repo = RecurringInvoiceRepository()

    def list_recurring_invoices(
        self,
        user_id: int,
        is_admin: bool,
        is_active: Optional[bool] = None,
    ) -> List[RecurringInvoice]:
        """List recurring invoices for the user (or all if admin)."""
        return self.repo.list_for_user(
            created_by=user_id,
            is_admin=is_admin,
            is_active=is_active,
        )

    def get_by_id(self, recurring_invoice_id: int) -> Optional[RecurringInvoice]:
        """Get a recurring invoice by id."""
        return self.repo.get_by_id(recurring_invoice_id)

    def generate_invoice(self, recurring_invoice):
        """
        Generate an invoice from a recurring invoice template.

        Args:
            recurring_invoice: RecurringInvoice model instance.

        Returns:
            Invoice instance if generated, None if should_generate_today() is False.
        """
        if not recurring_invoice.should_generate_today():
            return None

        settings = Settings.get_settings()
        currency_code = recurring_invoice.currency_code or (settings.currency if settings else "EUR")

        issue_date = datetime.utcnow().date()
        due_date = issue_date + timedelta(days=recurring_invoice.due_date_days)

        invoice_number = Invoice.generate_invoice_number()

        invoice = Invoice(
            invoice_number=invoice_number,
            project_id=recurring_invoice.project_id,
            client_name=recurring_invoice.client_name,
            due_date=due_date,
            created_by=recurring_invoice.created_by,
            client_id=recurring_invoice.client_id,
            client_email=recurring_invoice.client_email,
            client_address=recurring_invoice.client_address,
            tax_rate=recurring_invoice.tax_rate,
            notes=recurring_invoice.notes,
            terms=recurring_invoice.terms,
            currency_code=currency_code,
            template_id=recurring_invoice.template_id,
            issue_date=issue_date,
        )
        invoice.recurring_invoice_id = recurring_invoice.id
        db.session.add(invoice)

        if recurring_invoice.auto_include_time_entries:
            self._add_time_entry_items(recurring_invoice, invoice)

        invoice.calculate_totals()

        recurring_invoice.last_generated_at = datetime.utcnow()
        recurring_invoice.next_run_date = recurring_invoice.calculate_next_run_date(issue_date)

        return invoice

    def _add_time_entry_items(self, recurring_invoice, invoice):
        """Add invoice items from unbilled time entries for the recurring invoice's project."""
        time_entries = (
            TimeEntry.query.filter(
                TimeEntry.project_id == recurring_invoice.project_id,
                TimeEntry.end_time.isnot(None),
                TimeEntry.billable == True,
            )
            .order_by(TimeEntry.start_time.desc())
            .all()
        )

        unbilled_entries = []
        for entry in time_entries:
            already_billed = False
            for other_invoice in recurring_invoice.project.invoices:
                if other_invoice.id != invoice.id:
                    for item in other_invoice.items:
                        if item.time_entry_ids and str(entry.id) in item.time_entry_ids.split(","):
                            already_billed = True
                            break
                if already_billed:
                    break
            if not already_billed:
                unbilled_entries.append(entry)

        if not unbilled_entries:
            return

        from app.models import Settings
        from app.models.rate_override import RateOverride
        from app.utils.invoice_time_entry_items import build_invoice_items_from_entries

        settings = Settings.get_settings()
        group_entries = getattr(settings, "invoice_group_time_entries", True) if settings else True
        hourly_rate = RateOverride.resolve_rate(recurring_invoice.project)
        items = build_invoice_items_from_entries(
            invoice.id,
            unbilled_entries,
            hourly_rate,
            group=group_entries,
            project_name=recurring_invoice.project.name if recurring_invoice.project else None,
        )
        for item in items:
            db.session.add(item)
