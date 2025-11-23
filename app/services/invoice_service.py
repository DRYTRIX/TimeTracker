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
        issue_date: Optional[date] = None,
        due_date: Optional[date] = None,
        created_by: int,
        include_expenses: bool = False
    ) -> Dict[str, Any]:
        """
        Create an invoice from time entries.
        
        Returns:
            dict with 'success', 'message', and 'invoice' keys
        """
        # Validate project
        project = self.project_repo.get_by_id(project_id)
        if not project:
            return {
                'success': False,
                'message': 'Invalid project',
                'error': 'invalid_project'
            }
        
        # Get time entries
        entries = TimeEntry.query.filter(
            TimeEntry.id.in_(time_entry_ids),
            TimeEntry.project_id == project_id,
            TimeEntry.billable == True
        ).all()
        
        if not entries:
            return {
                'success': False,
                'message': 'No billable time entries found',
                'error': 'no_entries'
            }
        
        # Generate invoice number
        invoice_number = self.invoice_repo.generate_invoice_number()
        
        # Calculate totals
        subtotal = Decimal('0.00')
        for entry in entries:
            if entry.duration_seconds:
                hours = Decimal(str(entry.duration_seconds / 3600))
                rate = project.hourly_rate or Decimal('0.00')
                subtotal += hours * rate
        
        # Get tax rate (from project or default)
        tax_rate = Decimal('0.00')  # Should come from project/client settings
        tax_amount = subtotal * (tax_rate / 100)
        total_amount = subtotal + tax_amount
        
        # Create invoice
        invoice = self.invoice_repo.create(
            invoice_number=invoice_number,
            project_id=project_id,
            client_id=project.client_id,
            client_name=project.client.name if project.client else '',
            issue_date=issue_date or date.today(),
            due_date=due_date or date.today(),
            status=InvoiceStatus.DRAFT.value,
            subtotal=subtotal,
            tax_rate=tax_rate,
            tax_amount=tax_amount,
            total_amount=total_amount,
            currency_code='EUR',  # Should come from project/client
            created_by=created_by
        )
        
        # Create invoice items from time entries
        for entry in entries:
            if entry.duration_seconds:
                hours = Decimal(str(entry.duration_seconds / 3600))
                rate = project.hourly_rate or Decimal('0.00')
                amount = hours * rate
                
                item = InvoiceItem(
                    invoice_id=invoice.id,
                    description=f"Time entry: {entry.notes or 'No description'}",
                    quantity=hours,
                    unit_price=rate,
                    amount=amount
                )
                db.session.add(item)
        
        if not safe_commit('create_invoice', {'project_id': project_id, 'created_by': created_by}):
            return {
                'success': False,
                'message': 'Could not create invoice due to a database error',
                'error': 'database_error'
            }
        
        # Emit domain event
        emit_event(WebhookEvent.INVOICE_CREATED.value, {
            'invoice_id': invoice.id,
            'project_id': project_id,
            'client_id': project.client_id
        })
        
        return {
            'success': True,
            'message': 'Invoice created successfully',
            'invoice': invoice
        }
    
    def mark_as_sent(self, invoice_id: int) -> Dict[str, Any]:
        """Mark an invoice as sent"""
        invoice = self.invoice_repo.mark_as_sent(invoice_id)
        
        if not invoice:
            return {
                'success': False,
                'message': 'Invoice not found',
                'error': 'not_found'
            }
        
        if not safe_commit('mark_invoice_sent', {'invoice_id': invoice_id}):
            return {
                'success': False,
                'message': 'Could not update invoice due to a database error',
                'error': 'database_error'
            }
        
        return {
            'success': True,
            'message': 'Invoice marked as sent',
            'invoice': invoice
        }
    
    def mark_as_paid(
        self,
        invoice_id: int,
        payment_date: Optional[date] = None,
        payment_method: Optional[str] = None,
        payment_reference: Optional[str] = None
    ) -> Dict[str, Any]:
        """Mark an invoice as paid"""
        invoice = self.invoice_repo.mark_as_paid(
            invoice_id=invoice_id,
            payment_date=payment_date,
            payment_method=payment_method,
            payment_reference=payment_reference
        )
        
        if not invoice:
            return {
                'success': False,
                'message': 'Invoice not found',
                'error': 'not_found'
            }
        
        if not safe_commit('mark_invoice_paid', {'invoice_id': invoice_id}):
            return {
                'success': False,
                'message': 'Could not update invoice due to a database error',
                'error': 'database_error'
            }
        
        return {
            'success': True,
            'message': 'Invoice marked as paid',
            'invoice': invoice
        }

