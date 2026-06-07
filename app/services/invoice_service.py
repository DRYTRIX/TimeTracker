"""
Service for invoice business logic.
"""

import time
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app import db
from app.constants import InvoiceStatus, PaymentStatus, WebhookEvent
from app.models import Invoice, InvoiceItem, TimeEntry
from app.repositories import InvoiceRepository, ProjectRepository
from app.utils.db import safe_commit
from app.utils.event_bus import emit_event


class InvoiceService:
    """Service for invoice operations"""

    def __init__(self):
        self.invoice_repo = InvoiceRepository()
        self.project_repo = ProjectRepository()

    def create_invoice_from_time_entries(
        self,
        project_id: int,
        time_entry_ids: List[int],
        created_by: int,
        issue_date: Optional[date] = None,
        due_date: Optional[date] = None,
        include_expenses: bool = False,
    ) -> Dict[str, Any]:
        """
        Create an invoice from time entries.

        Returns:
            dict with 'success', 'message', and 'invoice' keys
        """
        t0 = time.monotonic()
        # Validate project
        project = self.project_repo.get_by_id(project_id)
        if not project:
            return {"success": False, "message": "Invalid project", "error": "invalid_project"}

        # Get time entries
        entries = TimeEntry.query.filter(
            TimeEntry.id.in_(time_entry_ids), TimeEntry.project_id == project_id, TimeEntry.billable == True
        ).all()

        if not entries:
            return {"success": False, "message": "No billable time entries found", "error": "no_entries"}

        # Generate invoice number
        invoice_number = self.invoice_repo.generate_invoice_number()

        # Calculate totals
        subtotal = Decimal("0.00")
        for entry in entries:
            if entry.duration_seconds:
                hours = Decimal(str(entry.duration_seconds / 3600))
                rate = project.hourly_rate or Decimal("0.00")
                subtotal += hours * rate

        # Get tax rate (from project or default)
        tax_rate = Decimal("0.00")  # Should come from project/client settings
        tax_amount = subtotal * (tax_rate / 100)
        total_amount = subtotal + tax_amount

        # Create invoice
        invoice = self.invoice_repo.create(
            invoice_number=invoice_number,
            project_id=project_id,
            client_id=project.client_id,
            # Project.client is a string property; relationship is Project.client_obj
            client_name=(project.client_obj.name if getattr(project, "client_obj", None) else project.client) or "",
            issue_date=issue_date or date.today(),
            due_date=due_date or date.today(),
            status=InvoiceStatus.DRAFT.value,
            subtotal=subtotal,
            tax_rate=tax_rate,
            tax_amount=tax_amount,
            total_amount=total_amount,
            currency_code="EUR",  # Should come from project/client
            created_by=created_by,
        )

        # Flush so the invoice receives its primary key before we build the
        # invoice items below — InvoiceItem.invoice_id is NOT NULL, and the
        # repository's create() only adds to the session without flushing.
        db.session.flush()

        # Create invoice items from time entries
        # Group entries by task for better organization
        grouped_entries: Dict[str, Dict[str, Any]] = {}
        for entry in entries:
            if entry.duration_seconds:
                hours = Decimal(str(entry.duration_seconds / 3600))
                if hours <= 0:
                    continue

                # Group by task if available, otherwise by project
                if entry.task_id:
                    key = f"task_{entry.task_id}"
                    description = f"Task: {entry.task.name if entry.task else 'Unknown Task'}"
                else:
                    key = f"project_{entry.project_id}"
                    description = f"Project: {project.name}"

                if key not in grouped_entries:
                    grouped_entries[key] = {
                        "description": description,
                        "entries": [],
                        "total_hours": Decimal("0"),
                    }

                grouped_entries[key]["entries"].append(entry)
                grouped_entries[key]["total_hours"] += hours

        # Create invoice items from grouped entries
        for group in grouped_entries.values():
            rate = project.hourly_rate or Decimal("0.00")

            # Store all time entry IDs as comma-separated string
            time_entry_ids_csv = ",".join(str(entry.id) for entry in group["entries"])

            item = InvoiceItem(
                invoice_id=invoice.id,
                description=group["description"],
                quantity=group["total_hours"],
                unit_price=rate,
                time_entry_ids=time_entry_ids_csv,
            )
            db.session.add(item)

        # Derive subtotal/tax/total from the persisted line items. Invoice.__init__
        # ignores subtotal/tax_amount/total_amount kwargs, so the values passed to
        # invoice_repo.create() above never stick; recompute from the items (whose
        # total_amount auto-computes from quantity * unit_price) as the source of
        # truth. Flush first so invoice.items reflects the rows just added.
        db.session.flush()
        invoice.calculate_totals()

        if not safe_commit("create_invoice", {"project_id": project_id, "created_by": created_by}):
            return {
                "success": False,
                "message": "Could not create invoice due to a database error",
                "error": "database_error",
            }

        # Emit domain event
        emit_event(
            WebhookEvent.INVOICE_CREATED.value,
            {"invoice_id": invoice.id, "project_id": project_id, "client_id": project.client_id},
        )

        from app.telemetry.otel_setup import business_span, record_invoice_created, record_invoice_duration_seconds

        line_item_count = len(grouped_entries)
        with business_span(
            "invoice.create",
            user_id=created_by,
            source="from_entries",
            line_item_count=line_item_count,
            time_entry_count=len(entries),
        ):
            pass
        record_invoice_created()
        record_invoice_duration_seconds(time.monotonic() - t0, "create")

        return {"success": True, "message": "Invoice created successfully", "invoice": invoice}

    def create_invoice(
        self,
        project_id: int,
        client_id: int,
        client_name: str,
        due_date: date,
        created_by: int,
        invoice_number: Optional[str] = None,
        client_email: Optional[str] = None,
        client_address: Optional[str] = None,
        notes: Optional[str] = None,
        terms: Optional[str] = None,
        tax_rate: Optional[float] = None,
        currency_code: Optional[str] = None,
        issue_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Create a new invoice.

        Returns:
            dict with 'success', 'message', and 'invoice' keys
        """
        t0 = time.monotonic()
        # Validate project
        project = self.project_repo.get_by_id(project_id)
        if not project:
            return {"success": False, "message": "Invalid project", "error": "invalid_project"}

        # Generate invoice number if not provided
        if not invoice_number:
            invoice_number = self.invoice_repo.generate_invoice_number()

        # Create invoice
        invoice = self.invoice_repo.create(
            invoice_number=invoice_number,
            project_id=project_id,
            client_id=client_id,
            client_name=client_name,
            due_date=due_date,
            created_by=created_by,
            client_email=client_email,
            client_address=client_address,
            notes=notes,
            terms=terms,
            tax_rate=Decimal(str(tax_rate)) if tax_rate else Decimal("0.00"),
            currency_code=currency_code or "EUR",
            issue_date=issue_date or date.today(),
            status=InvoiceStatus.DRAFT.value,
            subtotal=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            total_amount=Decimal("0.00"),
        )

        if not safe_commit("create_invoice", {"project_id": project_id, "created_by": created_by}):
            return {
                "success": False,
                "message": "Could not create invoice due to a database error",
                "error": "database_error",
            }

        # Emit domain event
        emit_event(
            WebhookEvent.INVOICE_CREATED.value,
            {"invoice_id": invoice.id, "project_id": project_id, "client_id": client_id},
        )

        # Notify client about new invoice
        if client_id:
            try:
                from app.services.client_notification_service import ClientNotificationService

                notification_service = ClientNotificationService()
                notification_service.notify_invoice_created(invoice.id, client_id)
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send client notification for invoice {invoice.id}: {e}", exc_info=True)

        from app.telemetry.otel_setup import business_span, record_invoice_created, record_invoice_duration_seconds

        with business_span(
            "invoice.create",
            user_id=created_by,
            source="api",
            has_tax=float(tax_rate or 0) > 0,
            has_notes=bool(notes),
        ):
            pass
        record_invoice_created()
        record_invoice_duration_seconds(time.monotonic() - t0, "create")

        return {"success": True, "message": "Invoice created successfully", "invoice": invoice}

    def mark_as_sent(self, invoice_id: int) -> Dict[str, Any]:
        """Mark an invoice as sent and mark associated time entries as paid"""
        invoice = self.invoice_repo.mark_as_sent(invoice_id)

        if not invoice:
            return {"success": False, "message": "Invoice not found", "error": "not_found"}

        # Mark associated time entries as paid
        marked_count = self.mark_time_entries_as_paid(invoice)

        if not safe_commit("mark_invoice_sent", {"invoice_id": invoice_id}):
            return {
                "success": False,
                "message": "Could not update invoice due to a database error",
                "error": "database_error",
            }

        message = "Invoice marked as sent"
        if marked_count > 0:
            message += f" ({marked_count} time entr{'y' if marked_count == 1 else 'ies'} marked as paid)"

        return {"success": True, "message": message, "invoice": invoice}

    def mark_as_paid(
        self,
        invoice_id: int,
        payment_date: Optional[date] = None,
        payment_method: Optional[str] = None,
        payment_reference: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Mark an invoice as paid"""
        invoice = self.invoice_repo.mark_as_paid(
            invoice_id=invoice_id,
            payment_date=payment_date,
            payment_method=payment_method,
            payment_reference=payment_reference,
        )

        if not invoice:
            return {"success": False, "message": "Invoice not found", "error": "not_found"}

        if not safe_commit("mark_invoice_paid", {"invoice_id": invoice_id}):
            return {
                "success": False,
                "message": "Could not update invoice due to a database error",
                "error": "database_error",
            }

        return {"success": True, "message": "Invoice marked as paid", "invoice": invoice}

    def mark_time_entries_as_paid(self, invoice: Invoice) -> int:
        """
        Mark all time entries associated with an invoice as paid.

        Args:
            invoice: The Invoice object

        Returns:
            Number of time entries marked as paid
        """
        time_entry_ids = set()

        # Collect all time entry IDs from invoice items
        for item in InvoiceItem.query.filter_by(invoice_id=invoice.id).all():
            if item.time_entry_ids:
                # Parse comma-separated IDs
                ids = [int(id_str.strip()) for id_str in item.time_entry_ids.split(",") if id_str.strip().isdigit()]
                time_entry_ids.update(ids)

        if not time_entry_ids:
            return 0

        # Mark all time entries as paid
        entries = TimeEntry.query.filter(TimeEntry.id.in_(time_entry_ids)).all()
        marked_count = 0

        for entry in entries:
            if not entry.paid:
                entry.paid = True
                entry.invoice_number = invoice.invoice_number
                marked_count += 1

        return marked_count

    def update_invoice(self, invoice_id: int, user_id: int, **kwargs) -> Dict[str, Any]:
        """
        Update an invoice.

        Returns:
            dict with 'success', 'message', and 'invoice' keys
        """
        invoice = self.invoice_repo.get_by_id(invoice_id)
        if not invoice:
            return {"success": False, "message": "Invoice not found", "error": "not_found"}

        # Update fields
        if "client_name" in kwargs:
            invoice.client_name = kwargs["client_name"]
        if "client_email" in kwargs:
            invoice.client_email = kwargs["client_email"]
        if "client_address" in kwargs:
            invoice.client_address = kwargs["client_address"]
        if "due_date" in kwargs:
            invoice.due_date = kwargs["due_date"]
        if "notes" in kwargs:
            invoice.notes = kwargs["notes"]
        if "terms" in kwargs:
            invoice.terms = kwargs["terms"]
        if "tax_rate" in kwargs:
            invoice.tax_rate = Decimal(str(kwargs["tax_rate"]))
        if "currency_code" in kwargs:
            invoice.currency_code = kwargs["currency_code"]
        if "status" in kwargs:
            invoice.status = kwargs["status"]

        if not safe_commit("update_invoice", {"invoice_id": invoice_id, "user_id": user_id}):
            return {
                "success": False,
                "message": "Could not update invoice due to a database error",
                "error": "database_error",
            }

        return {"success": True, "message": "Invoice updated successfully", "invoice": invoice}

    def delete_invoice(self, invoice_id: int, user_id: int) -> Dict[str, Any]:
        """
        Delete (cancel) an invoice.

        Returns:
            dict with 'success' and 'message' keys
        """
        invoice = self.invoice_repo.get_by_id(invoice_id)
        if not invoice:
            return {"success": False, "message": "Invoice not found", "error": "not_found"}

        # Only allow deletion of draft invoices
        if invoice.status != InvoiceStatus.DRAFT.value:
            return {
                "success": False,
                "message": "Only draft invoices can be deleted",
                "error": "invalid_status",
            }

        db.session.delete(invoice)

        if not safe_commit("delete_invoice", {"invoice_id": invoice_id, "user_id": user_id}):
            return {
                "success": False,
                "message": "Could not delete invoice due to a database error",
                "error": "database_error",
            }

        return {"success": True, "message": "Invoice deleted successfully"}

    def list_invoices(
        self,
        status: Optional[str] = None,
        payment_status: Optional[str] = None,
        search: Optional[str] = None,
        user_id: Optional[int] = None,
        is_admin: bool = False,
        page: int = 1,
        per_page: int = 50,
    ) -> Dict[str, Any]:
        """
        List invoices with filtering.
        Uses eager loading to prevent N+1 queries.

        Args:
            status: Filter by invoice status
            payment_status: Filter by payment status
            search: Search in invoice number or client name
            user_id: User ID for filtering (non-admin users)
            is_admin: Whether user is admin

        Returns:
            dict with 'invoices', 'summary' keys
        """
        from datetime import date

        from sqlalchemy.orm import joinedload

        query = self.invoice_repo.query()

        # Eagerly load relations to prevent N+1
        query = query.options(joinedload(Invoice.project), joinedload(Invoice.client))

        # Permission filter - non-admins only see their invoices
        if not is_admin and user_id:
            query = query.filter(Invoice.created_by == user_id)

        # Apply filters
        if status:
            query = query.filter(Invoice.status == status)

        if payment_status:
            query = query.filter(Invoice.payment_status == payment_status)

        if search:
            like = f"%{search}%"
            query = query.filter(db.or_(Invoice.invoice_number.ilike(like), Invoice.client_name.ilike(like)))

        # Order by creation date and paginate
        pagination = query.order_by(Invoice.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
        invoices = pagination.items

        # Calculate overdue status
        today = date.today()
        for invoice in invoices:
            if (
                invoice.due_date
                and invoice.due_date < today
                and invoice.payment_status != "fully_paid"
                and invoice.status != "paid"
            ):
                invoice._is_overdue = True
            else:
                invoice._is_overdue = False

        # Calculate summary statistics
        if is_admin:
            all_invoices = Invoice.query.all()
        else:
            all_invoices = Invoice.query.filter_by(created_by=user_id).all() if user_id else []

        total_invoices = len(all_invoices)
        total_amount = sum(invoice.total_amount for invoice in all_invoices)
        actual_paid_amount = sum(invoice.amount_paid or 0 for invoice in all_invoices)
        fully_paid_amount = sum(
            invoice.total_amount for invoice in all_invoices if invoice.payment_status == "fully_paid"
        )
        partially_paid_amount = sum(
            invoice.amount_paid or 0 for invoice in all_invoices if invoice.payment_status == "partially_paid"
        )
        overdue_amount = sum(invoice.outstanding_amount for invoice in all_invoices if invoice.status == "overdue")

        summary = {
            "total_invoices": total_invoices,
            "total_amount": float(total_amount),
            "paid_amount": float(actual_paid_amount),
            "fully_paid_amount": float(fully_paid_amount),
            "partially_paid_amount": float(partially_paid_amount),
            "overdue_amount": float(overdue_amount),
            "outstanding_amount": float(total_amount - actual_paid_amount),
        }

        return {"invoices": invoices, "summary": summary, "pagination": pagination}

    def get_invoice_with_details(self, invoice_id: int) -> Optional[Invoice]:
        """
        Get invoice with all related data using eager loading.

        Args:
            invoice_id: The invoice ID

        Returns:
            Invoice with eagerly loaded relations, or None if not found
        """
        return self.invoice_repo.get_with_relations(invoice_id)

    def get_unbilled_data_for_invoice(self, invoice: Invoice) -> Dict[str, Any]:
        """
        Get unbilled time entries, costs, expenses, and extra goods for an invoice's project,
        plus grouped time entries and totals. Used by the generate-from-time view.

        Returns:
            dict with time_entries, grouped_time_entries, project_costs, expenses, extra_goods,
            total_available_* totals, prepaid_summary, prepaid_plan_hours, currency.
        """
        from app.models import Expense, ExtraGood, ProjectCost, Settings

        time_entries = (
            TimeEntry.query.filter(
                TimeEntry.project_id == invoice.project_id,
                TimeEntry.end_time.isnot(None),
                TimeEntry.billable == True,
            )
            .order_by(TimeEntry.start_time.asc())
            .all()
        )
        unbilled_entries = []
        for entry in time_entries:
            already_billed = False
            for other_invoice in invoice.project.invoices:
                if other_invoice.id != invoice.id:
                    for item in other_invoice.items:
                        if item.time_entry_ids and str(entry.id) in item.time_entry_ids.split(","):
                            already_billed = True
                            break
                if already_billed:
                    break
            if not already_billed:
                unbilled_entries.append(entry)

        unbilled_costs = ProjectCost.get_uninvoiced_costs(invoice.project_id)
        unbilled_expenses = Expense.get_uninvoiced_expenses(project_id=invoice.project_id)
        project_goods = (
            ExtraGood.query.filter(
                ExtraGood.project_id == invoice.project_id,
                ExtraGood.invoice_id.is_(None),
                ExtraGood.billable == True,
            )
            .order_by(ExtraGood.created_at.desc())
            .all()
        )

        grouped_time_entries = []
        current_date = None
        current_bucket: Optional[Dict[str, Any]] = None
        for entry in unbilled_entries:
            entry_date = entry.start_time.date() if entry.start_time else None
            if entry_date != current_date:
                current_date = entry_date
                current_bucket = {"date": current_date, "entries": [], "total_hours": 0.0}
                grouped_time_entries.append(current_bucket)
            assert current_bucket is not None
            current_bucket["entries"].append(entry)
            current_bucket["total_hours"] += float(entry.duration_hours or 0)

        total_available_hours = sum(entry.duration_hours for entry in unbilled_entries)
        total_available_costs = sum(float(c.amount) for c in unbilled_costs)
        total_available_expenses = sum(float(e.total_amount) for e in unbilled_expenses)
        total_available_goods = sum(float(g.total_amount) for g in project_goods)

        prepaid_summary = []
        prepaid_plan_hours = None
        if invoice.client and getattr(invoice.client, "prepaid_plan_enabled", False):
            from app.utils.prepaid_hours_allocator import PrepaidHoursAllocator

            allocator = PrepaidHoursAllocator(client=invoice.client)
            summaries = allocator.build_summary(unbilled_entries)
            for summary in summaries:
                allocation_month = summary.allocation_month
                prepaid_summary.append(
                    {
                        "allocation_month": allocation_month,
                        "allocation_month_label": allocation_month.strftime("%Y-%m-%d") if allocation_month else "",
                        "plan_hours": float(summary.plan_hours),
                        "consumed_hours": float(summary.consumed_hours),
                        "remaining_hours": float(summary.remaining_hours),
                    }
                )
            prepaid_plan_hours = float(getattr(invoice.client, "prepaid_hours_decimal", 0) or 0)

        settings = Settings.get_settings()
        currency = settings.currency if settings else "USD"

        return {
            "time_entries": unbilled_entries,
            "grouped_time_entries": grouped_time_entries,
            "project_costs": unbilled_costs,
            "expenses": unbilled_expenses,
            "extra_goods": project_goods,
            "total_available_hours": total_available_hours,
            "total_available_costs": total_available_costs,
            "total_available_expenses": total_available_expenses,
            "total_available_goods": total_available_goods,
            "prepaid_summary": prepaid_summary,
            "prepaid_plan_hours": prepaid_plan_hours,
            "currency": currency,
            "prepaid_reset_day": invoice.client.prepaid_reset_day if invoice.client else None,
        }

    def _time_entry_hours_decimal(self, entry: TimeEntry) -> Decimal:
        if not entry.duration_seconds:
            return Decimal("0")
        return Decimal(str(entry.duration_seconds)) / Decimal("3600")

    def _billed_time_entry_ids_for_client(self, client_id: int) -> set:
        """IDs of time entries already linked to any invoice line for this client."""
        from app.models import InvoiceItem

        billed: set = set()
        rows = (
            db.session.query(InvoiceItem.time_entry_ids)
            .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
            .filter(Invoice.client_id == client_id, InvoiceItem.time_entry_ids.isnot(None))
            .all()
        )
        for (tids,) in rows:
            if not tids:
                continue
            for part in tids.split(","):
                p = part.strip()
                if p.isdigit():
                    billed.add(int(p))
        return billed

    def _client_unbilled_invoice_state(self, client_id: int) -> Dict[str, Any]:
        """
        Shared logic for preview and create: candidate entries, unbilled subset, grouping.

        Returns keys: ok (bool), error (optional str), blocked_reason (optional str),
        unbilled_entries (list), groups (dict project_id -> entries), projects_by_id, currency.
        """
        from sqlalchemy import or_

        from app.models import Client, Project, Settings

        client = Client.query.get(client_id)
        if not client:
            return {"ok": False, "error": "not_found"}

        projects = Project.query.filter_by(client_id=client_id).all()
        projects_by_id = {p.id: p for p in projects}
        project_ids = list(projects_by_id.keys())

        conditions = [TimeEntry.client_id == client_id]
        if project_ids:
            conditions.append(TimeEntry.project_id.in_(project_ids))

        candidates = (
            TimeEntry.query.filter(
                or_(*conditions),
                TimeEntry.end_time.isnot(None),
                TimeEntry.billable == True,
            )
            .order_by(TimeEntry.start_time.asc())
            .all()
        )

        billed_ids = self._billed_time_entry_ids_for_client(client_id)
        unbilled = [e for e in candidates if e.id not in billed_ids]

        orphans = [e for e in unbilled if e.project_id is None]
        if orphans:
            return {
                "ok": False,
                "error": "no_project_entries",
                "message": "Unbilled time without a project cannot be invoiced; assign a project first.",
                "unbilled_entries": [],
                "groups": {},
                "projects_by_id": projects_by_id,
                "currency": (Settings.get_settings().currency if Settings.get_settings() else "EUR"),
            }

        invoicable = [e for e in unbilled if e.project_id is not None]
        if not invoicable:
            settings = Settings.get_settings()
            return {
                "ok": False,
                "error": "no_unbilled_entries",
                "message": "No unbilled time entries for this client.",
                "unbilled_entries": [],
                "groups": {},
                "projects_by_id": projects_by_id,
                "currency": settings.currency if settings else "EUR",
            }

        groups: Dict[int, List[TimeEntry]] = {}
        for entry in invoicable:
            pid = entry.project_id
            groups.setdefault(pid, []).append(entry)

        settings = Settings.get_settings()
        currency = settings.currency if settings else "EUR"

        return {
            "ok": True,
            "unbilled_entries": invoicable,
            "groups": groups,
            "projects_by_id": projects_by_id,
            "currency": currency,
        }

    def get_client_unbilled_invoice_preview(self, client_id: int) -> Dict[str, Any]:
        """Summarize unbilled time for one client (matches create eligibility)."""
        state = self._client_unbilled_invoice_state(client_id)
        currency = state.get("currency") or "EUR"

        if state.get("error") == "not_found":
            return {
                "entry_count": 0,
                "total_hours": 0.0,
                "estimated_total": 0.0,
                "currency": currency,
                "blocked_reason": None,
            }

        if not state.get("ok"):
            br = "no_project" if state.get("error") == "no_project_entries" else None
            return {
                "entry_count": 0,
                "total_hours": 0.0,
                "estimated_total": 0.0,
                "currency": currency,
                "blocked_reason": br,
            }

        from app.models import RateOverride

        entries: List[TimeEntry] = state["unbilled_entries"]
        groups: Dict[int, List[TimeEntry]] = state["groups"]
        projects_by_id = state["projects_by_id"]

        total_hours = sum(self._time_entry_hours_decimal(e) for e in entries)
        estimated = Decimal("0")
        for pid, elist in groups.items():
            proj = projects_by_id.get(pid)
            if not proj:
                continue
            hrs = sum(self._time_entry_hours_decimal(e) for e in elist)
            rate = RateOverride.resolve_rate(proj)
            estimated += hrs * rate

        return {
            "entry_count": len(entries),
            "total_hours": float(total_hours),
            "estimated_total": float(estimated.quantize(Decimal("0.01"))),
            "currency": currency,
            "blocked_reason": None,
        }

    def create_client_unbilled_invoice(self, client_id: int, acting_user_id: int) -> Dict[str, Any]:
        """
        Create one draft invoice for all unbilled billable time for a client, grouped by project.

        Returns:
            success + invoice_id, invoice_number, total, item_count; or success False + error/message.
        """
        from app.models import Client, RateOverride, Settings

        state = self._client_unbilled_invoice_state(client_id)
        if state.get("error") == "not_found":
            return {"success": False, "error": "not_found", "message": "Client not found"}

        if not state.get("ok"):
            err = state.get("error", "unknown")
            return {
                "success": False,
                "error": err,
                "message": state.get("message", "Cannot create invoice."),
            }

        groups: Dict[int, List[TimeEntry]] = state["groups"]
        projects_by_id = state["projects_by_id"]
        settings = Settings.get_settings()
        currency = state.get("currency") or (settings.currency if settings else "EUR")

        # Invoice.project_id: project with largest unbilled hours (tie: lowest id)
        best_pid = None
        best_hours = Decimal("-1")
        for pid, elist in groups.items():
            hrs = sum((self._time_entry_hours_decimal(e) for e in elist), start=Decimal(0))
            if hrs > best_hours or (hrs == best_hours and (best_pid is None or pid < best_pid)):
                best_hours = hrs
                best_pid = pid

        if best_pid is None:
            return {
                "success": False,
                "error": "no_unbilled_entries",
                "message": "No unbilled time entries for this client.",
            }

        client = Client.query.get(client_id)
        issue_date = date.today()
        due_date = issue_date + timedelta(days=30)
        invoice_number = self.invoice_repo.generate_invoice_number()

        client_name = client.name
        client_email = getattr(client, "email", None) or None
        client_address = getattr(client, "address", None) or None
        try:
            from app.models import Contact

            primary = Contact.get_primary_contact(client_id)
            if primary and primary.email:
                client_email = primary.email
        except Exception:
            pass

        tax_rate = Decimal("0")
        notes = settings.invoice_notes if settings and settings.invoice_notes else None
        terms = settings.invoice_terms if settings and settings.invoice_terms else None
        template_id = getattr(settings, "default_invoice_template_id", None) if settings else None

        invoice = Invoice(
            invoice_number=invoice_number,
            project_id=best_pid,
            client_name=client_name,
            due_date=due_date,
            created_by=acting_user_id,
            client_id=client_id,
            client_email=client_email,
            client_address=client_address,
            issue_date=issue_date,
            status=InvoiceStatus.DRAFT.value,
            tax_rate=tax_rate,
            currency_code=currency,
            notes=notes,
            terms=terms,
        )
        if template_id:
            invoice.template_id = template_id

        db.session.add(invoice)
        db.session.flush()

        item_count = 0
        for pid in sorted(groups.keys()):
            elist = groups[pid]
            proj = projects_by_id.get(pid)
            if not proj:
                continue
            total_h = sum(self._time_entry_hours_decimal(e) for e in elist)
            if total_h <= 0:
                continue
            rate = RateOverride.resolve_rate(proj)
            desc = f"Project: {proj.name}"
            tids = ",".join(str(e.id) for e in elist)
            item = InvoiceItem(
                invoice_id=invoice.id,
                description=desc,
                quantity=total_h,
                unit_price=rate,
                time_entry_ids=tids,
            )
            db.session.add(item)
            item_count += 1

        invoice.calculate_totals()

        if not safe_commit(
            "create_client_unbilled_invoice", {"client_id": client_id, "acting_user_id": acting_user_id}
        ):
            return {
                "success": False,
                "error": "database_error",
                "message": "Could not create invoice due to a database error.",
            }

        emit_event(
            WebhookEvent.INVOICE_CREATED.value,
            {"invoice_id": invoice.id, "project_id": best_pid, "client_id": client_id, "source": "client_unbilled"},
        )

        return {
            "success": True,
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "total": float(invoice.total_amount),
            "item_count": item_count,
            "invoice": invoice,
        }
