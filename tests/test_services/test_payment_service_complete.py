"""
Comprehensive tests for PaymentService including update and delete methods.
"""

import pytest
from datetime import date
from decimal import Decimal
from app.services import PaymentService
from app.models import Payment, Invoice


class TestPaymentServiceComplete:
    """Complete tests for PaymentService"""

    def test_update_payment_success(self, app, invoice, payment):
        """Test successful payment update"""
        service = PaymentService()
        
        result = service.update_payment(
            payment_id=payment.id,
            user_id=1,
            amount=Decimal("1500.00"),
            notes="Updated payment"
        )
        
        assert result["success"] is True
        assert result["payment"].amount == Decimal("1500.00")
        assert result["payment"].notes == "Updated payment"

    def test_update_payment_not_found(self, app):
        """Test update with non-existent payment"""
        service = PaymentService()
        
        result = service.update_payment(
            payment_id=99999,
            user_id=1
        )
        
        assert result["success"] is False
        assert result["error"] == "not_found"

    def test_delete_payment_success(self, app, invoice, payment):
        """Test successful payment deletion"""
        service = PaymentService()
        
        result = service.delete_payment(
            payment_id=payment.id,
            user_id=1
        )
        
        assert result["success"] is True

    def test_delete_payment_updates_invoice_status(self, app, invoice, payment):
        """Test that deleting payment updates invoice payment status"""
        service = PaymentService()
        
        # Set invoice amount_paid
        invoice.amount_paid = payment.amount
        invoice.payment_status = "fully_paid"
        from app import db
        db.session.commit()
        
        result = service.delete_payment(
            payment_id=payment.id,
            user_id=1
        )
        
        assert result["success"] is True
        
        # Verify invoice status updated
        from app import db
        db.session.refresh(invoice)
        assert invoice.payment_status == "unpaid"

