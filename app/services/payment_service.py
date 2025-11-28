"""
Service for payment business logic.
"""

from typing import Optional, Dict, Any, List
from datetime import date
from decimal import Decimal
from app import db
from app.repositories import PaymentRepository, InvoiceRepository
from app.models import Payment, Invoice
from app.utils.db import safe_commit
from app.utils.event_bus import emit_event
from app.constants import WebhookEvent


class PaymentService:
    """Service for payment operations"""

    def __init__(self):
        self.payment_repo = PaymentRepository()
        self.invoice_repo = InvoiceRepository()

    def create_payment(
        self,
        invoice_id: int,
        amount: Decimal,
        payment_date: date,
        received_by: int,
        currency: Optional[str] = None,
        method: Optional[str] = None,
        reference: Optional[str] = None,
        notes: Optional[str] = None,
        status: str = "completed",
        gateway_transaction_id: Optional[str] = None,
        gateway_fee: Optional[Decimal] = None,
    ) -> Dict[str, Any]:
        """
        Create a new payment.

        Returns:
            dict with 'success', 'message', and 'payment' keys
        """
        # Validate invoice
        invoice = self.invoice_repo.get_by_id(invoice_id)
        if not invoice:
            return {"success": False, "message": "Invoice not found", "error": "invalid_invoice"}

        # Validate amount
        if amount <= 0:
            return {"success": False, "message": "Amount must be greater than zero", "error": "invalid_amount"}

        # Get currency from invoice if not provided
        if not currency:
            currency = invoice.currency_code

        # Create payment
        payment = self.payment_repo.create(
            invoice_id=invoice_id,
            amount=amount,
            currency=currency,
            payment_date=payment_date,
            method=method,
            reference=reference,
            notes=notes,
            status=status,
            received_by=received_by,
            gateway_transaction_id=gateway_transaction_id,
            gateway_fee=gateway_fee,
        )

        # Calculate net amount
        payment.calculate_net_amount()

        # Update invoice payment status if payment is completed
        if status == "completed":
            total_payments = self.payment_repo.get_total_for_invoice(invoice_id)
            invoice.amount_paid = total_payments + amount

            # Update payment status
            if invoice.amount_paid >= invoice.total_amount:
                invoice.payment_status = "fully_paid"
            elif invoice.amount_paid > 0:
                invoice.payment_status = "partially_paid"
            else:
                invoice.payment_status = "unpaid"

        if not safe_commit("create_payment", {"invoice_id": invoice_id, "received_by": received_by}):
            return {
                "success": False,
                "message": "Could not create payment due to a database error",
                "error": "database_error",
            }

        # Emit domain event
        emit_event("payment.created", {"payment_id": payment.id, "invoice_id": invoice_id, "amount": float(amount)})

        return {"success": True, "message": "Payment created successfully", "payment": payment}

    def get_invoice_payments(self, invoice_id: int) -> List[Payment]:
        """Get all payments for an invoice"""
        return self.payment_repo.get_by_invoice(invoice_id, include_relations=True)

    def get_total_paid(self, invoice_id: int) -> Decimal:
        """Get total amount paid for an invoice"""
        return self.payment_repo.get_total_for_invoice(invoice_id)
