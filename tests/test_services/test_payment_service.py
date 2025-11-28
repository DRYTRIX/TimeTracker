"""
Tests for PaymentService.
"""

import pytest
from decimal import Decimal
from datetime import date
from app.services import PaymentService
from app.repositories import PaymentRepository, InvoiceRepository
from app.models import Payment, Invoice


class TestPaymentService:
    """Test cases for PaymentService"""

    def test_create_payment_success(self, db_session, sample_invoice, sample_user):
        """Test successful payment creation"""
        service = PaymentService()

        result = service.create_payment(
            invoice_id=sample_invoice.id,
            amount=Decimal("100.00"),
            payment_date=date.today(),
            currency="EUR",
            method="bank_transfer",
            received_by=sample_user.id,
        )

        assert result["success"] is True
        assert result["payment"] is not None
        assert result["payment"].amount == Decimal("100.00")
        assert result["payment"].invoice_id == sample_invoice.id

    def test_create_payment_invalid_invoice(self, db_session, sample_user):
        """Test payment creation with invalid invoice"""
        service = PaymentService()

        result = service.create_payment(
            invoice_id=99999, amount=Decimal("100.00"), payment_date=date.today(), received_by=sample_user.id
        )

        assert result["success"] is False
        assert result["error"] == "invalid_invoice"

    def test_create_payment_invalid_amount(self, db_session, sample_invoice, sample_user):
        """Test payment creation with invalid amount"""
        service = PaymentService()

        result = service.create_payment(
            invoice_id=sample_invoice.id, amount=Decimal("0.00"), payment_date=date.today(), received_by=sample_user.id
        )

        assert result["success"] is False
        assert result["error"] == "invalid_amount"

    def test_get_invoice_payments(self, db_session, sample_invoice, sample_user):
        """Test getting payments for an invoice"""
        service = PaymentService()

        # Create payments
        service.create_payment(
            invoice_id=sample_invoice.id, amount=Decimal("50.00"), payment_date=date.today(), received_by=sample_user.id
        )

        service.create_payment(
            invoice_id=sample_invoice.id, amount=Decimal("50.00"), payment_date=date.today(), received_by=sample_user.id
        )

        payments = service.get_invoice_payments(sample_invoice.id)

        assert len(payments) == 2
        assert sum(p.amount for p in payments) == Decimal("100.00")

    def test_get_total_paid(self, db_session, sample_invoice, sample_user):
        """Test getting total paid for an invoice"""
        service = PaymentService()

        # Create payments
        service.create_payment(
            invoice_id=sample_invoice.id, amount=Decimal("75.00"), payment_date=date.today(), received_by=sample_user.id
        )

        service.create_payment(
            invoice_id=sample_invoice.id, amount=Decimal("25.00"), payment_date=date.today(), received_by=sample_user.id
        )

        total = service.get_total_paid(sample_invoice.id)

        assert total == Decimal("100.00")
