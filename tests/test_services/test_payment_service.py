"""
Tests for PaymentService.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.models import Invoice, Payment
from app.repositories import InvoiceRepository, PaymentRepository
from app.services import PaymentService


class TestPaymentService:
    """Test cases for PaymentService"""

    def test_create_payment_success(self, db_session, invoice, user):
        """Test successful payment creation"""
        service = PaymentService()

        result = service.create_payment(
            invoice_id=invoice.id,
            amount=Decimal("100.00"),
            payment_date=date.today(),
            currency="EUR",
            method="bank_transfer",
            received_by=user.id,
        )

        assert result["success"] is True
        assert result["payment"] is not None
        assert result["payment"].amount == Decimal("100.00")
        assert result["payment"].invoice_id == invoice.id

    def test_create_payment_invalid_invoice(self, db_session, user):
        """Test payment creation with invalid invoice"""
        service = PaymentService()

        result = service.create_payment(
            invoice_id=99999, amount=Decimal("100.00"), payment_date=date.today(), received_by=user.id
        )

        assert result["success"] is False
        assert result["error"] == "invalid_invoice"

    def test_create_payment_invalid_amount(self, db_session, invoice, user):
        """Test payment creation with invalid amount"""
        service = PaymentService()

        result = service.create_payment(
            invoice_id=invoice.id, amount=Decimal("0.00"), payment_date=date.today(), received_by=user.id
        )

        assert result["success"] is False
        assert result["error"] == "invalid_amount"

    def test_get_invoice_payments(self, db_session, invoice, user):
        """Test getting payments for an invoice"""
        service = PaymentService()

        # Create payments
        service.create_payment(
            invoice_id=invoice.id, amount=Decimal("50.00"), payment_date=date.today(), received_by=user.id
        )

        service.create_payment(
            invoice_id=invoice.id, amount=Decimal("50.00"), payment_date=date.today(), received_by=user.id
        )

        payments = service.get_invoice_payments(invoice.id)

        assert len(payments) == 2
        assert sum(p.amount for p in payments) == Decimal("100.00")

    def test_get_total_paid(self, db_session, invoice, user):
        """Test getting total paid for an invoice"""
        service = PaymentService()

        # Create payments
        service.create_payment(
            invoice_id=invoice.id, amount=Decimal("75.00"), payment_date=date.today(), received_by=user.id
        )

        service.create_payment(
            invoice_id=invoice.id, amount=Decimal("25.00"), payment_date=date.today(), received_by=user.id
        )

        total = service.get_total_paid(invoice.id)

        assert total == Decimal("100.00")


def test_create_payment_sets_overpaid_status(db_session, invoice, user):
    """Overpaying an invoice sets payment_status to overpaid and returns a warning."""
    invoice.total_amount = Decimal("100.00")
    invoice.amount_paid = Decimal("0")
    invoice.payment_status = "unpaid"
    db_session.commit()

    service = PaymentService()
    result = service.create_payment(
        invoice_id=invoice.id,
        amount=Decimal("150.00"),
        payment_date=date.today(),
        received_by=user.id,
    )

    assert result["success"] is True
    assert result.get("overpayment") is True
    assert "warning" in result
    db_session.refresh(invoice)
    assert invoice.payment_status == "overpaid"
    assert invoice.amount_paid == Decimal("150.00")
    assert invoice.status == "paid"
