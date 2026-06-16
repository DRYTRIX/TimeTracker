"""Shared invoice checkout service for staff and client portal."""

from datetime import date
from decimal import Decimal
from typing import Optional

from flask import url_for

from app import db
from app.models import Invoice, Payment
from app.payments.registry import get_provider
from app.services.payment_gateway_service import PaymentGatewayService
from app.utils.db import safe_commit


class CheckoutService:
    def __init__(self):
        self.gateway_service = PaymentGatewayService()

    def get_checkout_gateway(self, provider: Optional[str] = None):
        return self.gateway_service.get_active_gateway(provider=provider)

    def start_checkout(
        self,
        invoice: Invoice,
        success_endpoint: str,
        cancel_endpoint: str,
        success_values: Optional[dict] = None,
        cancel_values: Optional[dict] = None,
        provider: Optional[str] = None,
    ):
        gateway = self.get_checkout_gateway(provider=provider)
        if not gateway:
            return {"success": False, "message": "No payment gateway configured"}

        outstanding = getattr(invoice, "outstanding_amount", None)
        amount = Decimal(str(outstanding if outstanding is not None else invoice.total_amount or 0))
        if amount <= 0:
            return {"success": False, "message": "Invoice has no outstanding balance"}

        provider_impl = get_provider(gateway)
        success_url = url_for(success_endpoint, _external=True, **(success_values or {"invoice_id": invoice.id}))
        cancel_url = url_for(cancel_endpoint, _external=True, **(cancel_values or {"invoice_id": invoice.id}))

        result = provider_impl.create_checkout_session(
            invoice_id=invoice.id,
            amount=amount,
            currency=invoice.currency_code or "EUR",
            success_url=success_url,
            cancel_url=cancel_url,
            description=f"Invoice {invoice.invoice_number}",
        )
        if result.success:
            return {"success": True, "url": result.url, "gateway": gateway, "session_id": result.session_id}
        return {"success": False, "message": result.message or "Checkout failed"}

    def complete_webhook(self, gateway, payload: bytes, headers: dict):
        from app.payments.paypal_provider import PayPalProvider
        from app.payments.registry import get_provider

        provider_impl = get_provider(gateway)
        webhook = provider_impl.verify_webhook(payload, headers)
        if not webhook.valid:
            return {"success": False, "message": webhook.message or "Invalid webhook", "status": 400}

        if webhook.event_type not in (
            "payment_intent.succeeded",
            "checkout.session.completed",
            "PAYMENT.CAPTURE.COMPLETED",
        ):
            return {"success": True, "message": "ignored", "status": 200}

        if not webhook.transaction_id or not webhook.invoice_id:
            return {"success": True, "message": "ignored", "status": 200}

        self._ensure_transaction(gateway, webhook)
        self.gateway_service.update_transaction_status(
            transaction_id=webhook.transaction_id,
            status="completed",
            gateway_response=webhook.raw,
        )
        self._ensure_payment_ledger(webhook, gateway)
        return {"success": True, "status": 200}

    def capture_paypal_return(self, gateway, order_id: str, invoice_id: int):
        from app.payments.paypal_provider import PayPalProvider
        from app.payments.registry import get_provider

        provider_impl = get_provider(gateway)
        if not isinstance(provider_impl, PayPalProvider):
            return {"success": False, "message": "Not a PayPal gateway"}

        capture = provider_impl.capture_order(order_id)
        if not capture.get("success"):
            return capture

        data = capture.get("data") or {}
        purchase_unit = (data.get("purchase_units") or [{}])[0]
        capture_info = (purchase_unit.get("payments") or {}).get("captures") or [{}]
        capture_row = capture_info[0] if capture_info else {}
        amount_value = ((capture_row.get("amount") or {}).get("value")) or "0"
        currency = ((capture_row.get("amount") or {}).get("currency_code")) or "EUR"
        transaction_id = capture_row.get("id") or order_id

        from app.payments.base import WebhookResult

        webhook = WebhookResult(
            valid=True,
            event_type="PAYMENT.CAPTURE.COMPLETED",
            transaction_id=transaction_id,
            invoice_id=invoice_id,
            amount=Decimal(str(amount_value)),
            currency=currency,
            raw=data,
        )
        self._ensure_transaction(gateway, webhook)
        self.gateway_service.update_transaction_status(
            transaction_id=transaction_id,
            status="completed",
            gateway_response=data,
        )
        self._ensure_payment_ledger(webhook, gateway)
        return {"success": True}

    def _ensure_transaction(self, gateway, webhook):
        from app.models import PaymentTransaction

        tx = PaymentTransaction.query.filter_by(transaction_id=webhook.transaction_id).first()
        if tx:
            return tx
        tx = PaymentTransaction(
            invoice_id=webhook.invoice_id,
            gateway_id=gateway.id,
            transaction_id=webhook.transaction_id,
            amount=webhook.amount or Decimal("0"),
            currency=(webhook.currency or "EUR").upper(),
            status="processing",
            payment_method=gateway.provider,
            gateway_response=webhook.raw,
        )
        db.session.add(tx)
        safe_commit("checkout_ensure_transaction", {"transaction_id": webhook.transaction_id})
        return tx

    def _ensure_payment_ledger(self, webhook, gateway):
        existing = Payment.query.filter_by(gateway_transaction_id=webhook.transaction_id).first()
        if existing:
            return existing

        invoice = Invoice.query.get(webhook.invoice_id)
        if not invoice:
            return None

        payment = Payment(
            invoice_id=webhook.invoice_id,
            amount=webhook.amount or Decimal("0"),
            currency=(webhook.currency or invoice.currency_code or "EUR").upper(),
            payment_date=date.today(),
            method=gateway.provider,
            reference=webhook.transaction_id,
            status="completed",
            received_by=invoice.created_by,
            gateway_transaction_id=webhook.transaction_id,
        )
        db.session.add(payment)
        safe_commit("checkout_payment_ledger", {"invoice_id": webhook.invoice_id})
        return payment
