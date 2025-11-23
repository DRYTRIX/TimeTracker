"""
Repository for invoice data access operations.
"""

from typing import List, Optional
from datetime import datetime, date
from sqlalchemy.orm import joinedload
from app import db
from app.models import Invoice, Project, Client
from app.repositories.base_repository import BaseRepository
from app.constants import InvoiceStatus, PaymentStatus


class InvoiceRepository(BaseRepository[Invoice]):
    """Repository for invoice operations"""
    
    def __init__(self):
        super().__init__(Invoice)
    
    def get_by_project(
        self,
        project_id: int,
        include_relations: bool = False
    ) -> List[Invoice]:
        """Get invoices for a project"""
        query = self.model.query.filter_by(project_id=project_id)
        
        if include_relations:
            query = query.options(
                joinedload(Invoice.project),
                joinedload(Invoice.client)
            )
        
        return query.order_by(Invoice.issue_date.desc()).all()
    
    def get_by_client(
        self,
        client_id: int,
        status: Optional[str] = None,
        include_relations: bool = False
    ) -> List[Invoice]:
        """Get invoices for a client"""
        query = self.model.query.filter_by(client_id=client_id)
        
        if status:
            query = query.filter_by(status=status)
        
        if include_relations:
            query = query.options(
                joinedload(Invoice.project),
                joinedload(Invoice.client)
            )
        
        return query.order_by(Invoice.issue_date.desc()).all()
    
    def get_by_status(
        self,
        status: str,
        include_relations: bool = False
    ) -> List[Invoice]:
        """Get invoices by status"""
        query = self.model.query.filter_by(status=status)
        
        if include_relations:
            query = query.options(
                joinedload(Invoice.project),
                joinedload(Invoice.client)
            )
        
        return query.order_by(Invoice.issue_date.desc()).all()
    
    def get_overdue(self, include_relations: bool = False) -> List[Invoice]:
        """Get overdue invoices"""
        today = date.today()
        query = self.model.query.filter(
            Invoice.due_date < today,
            Invoice.status.in_([InvoiceStatus.SENT.value, InvoiceStatus.PARTIALLY_PAID.value])
        )
        
        if include_relations:
            query = query.options(
                joinedload(Invoice.project),
                joinedload(Invoice.client)
            )
        
        return query.order_by(Invoice.due_date).all()
    
    def get_with_relations(self, invoice_id: int) -> Optional[Invoice]:
        """Get invoice with all relations loaded"""
        return self.model.query.options(
            joinedload(Invoice.project),
            joinedload(Invoice.client)
        ).get(invoice_id)
    
    def generate_invoice_number(self) -> str:
        """Generate a unique invoice number"""
        from datetime import datetime
        
        # Format: INV-YYYYMMDD-XXXX
        today = datetime.now().strftime('%Y%m%d')
        prefix = f"INV-{today}-"
        
        # Find the highest number for today
        last_invoice = self.model.query.filter(
            Invoice.invoice_number.like(f"{prefix}%")
        ).order_by(Invoice.invoice_number.desc()).first()
        
        if last_invoice:
            try:
                last_num = int(last_invoice.invoice_number.split('-')[-1])
                next_num = last_num + 1
            except (ValueError, IndexError):
                next_num = 1
        else:
            next_num = 1
        
        return f"{prefix}{next_num:04d}"
    
    def mark_as_sent(self, invoice_id: int) -> Optional[Invoice]:
        """Mark an invoice as sent"""
        invoice = self.get_by_id(invoice_id)
        if invoice:
            invoice.status = InvoiceStatus.SENT.value
            return invoice
        return None
    
    def mark_as_paid(
        self,
        invoice_id: int,
        payment_date: Optional[date] = None,
        payment_method: Optional[str] = None,
        payment_reference: Optional[str] = None
    ) -> Optional[Invoice]:
        """Mark an invoice as paid"""
        invoice = self.get_by_id(invoice_id)
        if invoice:
            invoice.status = InvoiceStatus.PAID.value
            invoice.payment_status = PaymentStatus.FULLY_PAID.value
            invoice.payment_date = payment_date or date.today()
            invoice.payment_method = payment_method
            invoice.payment_reference = payment_reference
            invoice.amount_paid = invoice.total_amount
            return invoice
        return None

