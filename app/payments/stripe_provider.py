"""Stripe payment provider."""

from decimal import Decimal
from typing import Dict, Optional

from app.payments.base import CheckoutResult, PaymentProvider, WebhookResult
from app.utils.stripe_integration import StripeIntegration


class StripeProvider(PaymentProvider):
    provider_name = "stripe"

    def create_checkout_session(
        self,
        invoice_id: int,
        amount: Decimal,
        currency: str,
        success_url: str,
        cancel_url: str,
        description: Optional[str] = None,
    ) -> CheckoutResult:
        api_key = self.config.get("api_key")
        if not api_key:
            return CheckoutResult(success=False, message="Stripe API key not configured")

        integration = StripeIntegration(api_key)
        result = integration.create_checkout_session(
            invoice_id=invoice_id,
            amount=amount,
            currency=currency,
            success_url=success_url,
            cancel_url=cancel_url,
            description=description,
        )
        if result.get("success"):
            return CheckoutResult(
                success=True,
                url=result.get("url"),
                session_id=result.get("session_id"),
                raw=result,
            )
        return CheckoutResult(success=False, message=result.get("message"), raw=result)

    def verify_webhook(self, payload: bytes, headers: Dict[str, str]) -> WebhookResult:
        api_key = self.config.get("api_key")
        webhook_secret = self.config.get("webhook_secret")
        if not api_key or not webhook_secret:
            return WebhookResult(valid=False, message="Stripe webhook not configured")

        sig = headers.get("Stripe-Signature") or headers.get("stripe-signature") or ""
        event = StripeIntegration(api_key).verify_webhook(payload, sig, webhook_secret)
        if not event:
            return WebhookResult(valid=False, message="Invalid Stripe webhook signature")

        event_type = event.get("type")
        data_obj = (event.get("data") or {}).get("object") or {}
        invoice_id = 0
        try:
            invoice_id = int((data_obj.get("metadata") or {}).get("invoice_id") or 0)
        except (TypeError, ValueError):
            invoice_id = 0

        transaction_id = (
            data_obj.get("payment_intent") if event_type == "checkout.session.completed" else data_obj.get("id")
        ) or ""

        amount_cents = data_obj.get("amount_received") or data_obj.get("amount_total") or data_obj.get("amount") or 0
        try:
            amount = (Decimal(str(amount_cents)) / 100) if amount_cents else Decimal("0")
        except Exception:
            amount = Decimal("0")

        return WebhookResult(
            valid=True,
            event_type=event_type,
            transaction_id=transaction_id,
            invoice_id=invoice_id or None,
            amount=amount,
            currency=(data_obj.get("currency") or "EUR").upper(),
            raw=data_obj,
        )
