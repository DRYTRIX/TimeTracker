"""
Service for invoice business logic.
"""

from typing import Optional, Dict, Any, List
from datetime import date
from decimal import Decimal
from app import db
from app.repositories import InvoiceRepository, ProjectRepository
from app.models import Invoice, InvoiceItem, TimeEntry
from app.constants import InvoiceStatus, PaymentStatus
from app.utils.db import safe_commit
from app.utils.event_bus import emit_event
from app.constants import WebhookEvent


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

        # Create invoice items from time entries
        # Group entries by task for better organization
        grouped_entries = {}
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
            time_entry_ids = ",".join(str(entry.id) for entry in group["entries"])
            
            item = InvoiceItem(
                invoice_id=invoice.id,
                description=group["description"],
                quantity=group["total_hours"],
                unit_price=rate,
                time_entry_ids=time_entry_ids,
            )
            db.session.add(item)

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
        for item in invoice.items:
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
        from sqlalchemy.orm import joinedload
        from datetime import date

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
