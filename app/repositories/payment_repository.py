"""
Repository for payment data access operations.
"""

from typing import List, Optional
from datetime import date
from decimal import Decimal
from sqlalchemy.orm import joinedload
from sqlalchemy import func
from app import db
from app.models import Payment, Invoice
from app.repositories.base_repository import BaseRepository


class PaymentRepository(BaseRepository[Payment]):
    """Repository for payment operations"""
    
    def __init__(self):
        super().__init__(Payment)
    
    def get_by_invoice(
        self,
        invoice_id: int,
        include_relations: bool = False
    ) -> List[Payment]:
        """Get payments for an invoice"""
        query = self.model.query.filter_by(invoice_id=invoice_id)
        
        if include_relations:
            query = query.options(joinedload(Payment.receiver))
        
        return query.order_by(Payment.payment_date.desc()).all()
    
    def get_by_date_range(
        self,
        start_date: date,
        end_date: date,
        include_relations: bool = False
    ) -> List[Payment]:
        """Get payments within a date range"""
        query = self.model.query.filter(
            Payment.payment_date >= start_date,
            Payment.payment_date <= end_date
        )
        
        if include_relations:
            query = query.options(
                joinedload(Payment.receiver),
                joinedload(Payment.invoice) if hasattr(Payment, 'invoice') else query
            )
        
        return query.order_by(Payment.payment_date.desc()).all()
    
    def get_by_status(
        self,
        status: str,
        include_relations: bool = False
    ) -> List[Payment]:
        """Get payments by status"""
        query = self.model.query.filter_by(status=status)
        
        if include_relations:
            query = query.options(joinedload(Payment.receiver))
        
        return query.order_by(Payment.payment_date.desc()).all()
    
    def get_total_amount(
        self,
        invoice_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[str] = None
    ) -> Decimal:
        """Get total payment amount"""
        query = db.session.query(func.sum(Payment.amount))
        
        if invoice_id:
            query = query.filter_by(invoice_id=invoice_id)
        
        if start_date:
            query = query.filter(Payment.payment_date >= start_date)
        
        if end_date:
            query = query.filter(Payment.payment_date <= end_date)
        
        if status:
            query = query.filter_by(status=status)
        
        result = query.scalar()
        return Decimal(result) if result else Decimal('0.00')
    
    def get_total_for_invoice(self, invoice_id: int) -> Decimal:
        """Get total payments for an invoice"""
        return self.get_total_amount(invoice_id=invoice_id, status='completed')

