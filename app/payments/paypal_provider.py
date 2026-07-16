"""PayPal Orders v2 payment provider."""

import base64
import json
import logging
from decimal import Decimal
from typing import Dict, Optional
from urllib.parse import urlencode

import requests

from app.payments.base import CheckoutResult, PaymentProvider, WebhookResult

logger = logging.getLogger(__name__)


class PayPalProvider(PaymentProvider):
    provider_name = "paypal"

    def _api_base(self) -> str:
        if self.is_test_mode or self.config.get("sandbox", True):
            return "https://api-m.sandbox.paypal.com"
        return "https://api-m.paypal.com"

    def _get_access_token(self) -> Optional[str]:
        client_id = self.config.get("client_id")
        client_secret = self.config.get("client_secret")
        if not client_id or not client_secret:
            return None

        auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        resp = requests.post(
            f"{self._api_base()}/v1/oauth2/token",
            headers={
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials"},
            timeout=30,
        )
        if not resp.ok:
            logger.error("PayPal token error: %s", resp.text)
            return None
        return resp.json().get("access_token")

    def create_checkout_session(
        self,
        invoice_id: int,
        amount: Decimal,
        currency: str,
        success_url: str,
        cancel_url: str,
        description: Optional[str] = None,
    ) -> CheckoutResult:
        token = self._get_access_token()
        if not token:
            return CheckoutResult(success=False, message="PayPal credentials not configured")

        order_payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": str(invoice_id),
                    "description": description or f"Invoice #{invoice_id}",
                    "custom_id": str(invoice_id),
                    "amount": {
                        "currency_code": currency.upper(),
                        "value": f"{amount:.2f}",
                    },
                }
            ],
            "application_context": {
                "return_url": success_url,
                "cancel_url": cancel_url,
                "brand_name": "TimeTracker",
                "user_action": "PAY_NOW",
            },
        }

        resp = requests.post(
            f"{self._api_base()}/v2/checkout/orders",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=order_payload,
            timeout=30,
        )
        if not resp.ok:
            logger.error("PayPal order error: %s", resp.text)
            return CheckoutResult(success=False, message="Failed to create PayPal order", raw=resp.json())

        data = resp.json()
        approve_url = next(
            (link.get("href") for link in data.get("links", []) if link.get("rel") == "approve"),
            None,
        )
        if not approve_url:
            return CheckoutResult(success=False, message="PayPal approval URL missing", raw=data)

        return CheckoutResult(success=True, url=approve_url, session_id=data.get("id"), raw=data)

    def capture_order(self, order_id: str) -> Dict:
        token = self._get_access_token()
        if not token:
            return {"success": False, "message": "PayPal credentials not configured"}
        resp = requests.post(
            f"{self._api_base()}/v2/checkout/orders/{order_id}/capture",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        if not resp.ok:
            return {"success": False, "message": resp.text}
        return {"success": True, "data": resp.json()}

    def verify_webhook(self, payload: bytes, headers: Dict[str, str]) -> WebhookResult:
        try:
            event = json.loads(payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return WebhookResult(valid=False, message="Invalid PayPal webhook payload")

        event_type = event.get("event_type")
        resource = event.get("resource") or {}

        invoice_id = None
        amount = Decimal("0")
        currency = "EUR"
        transaction_id = resource.get("id")

        if event_type == "CHECKOUT.ORDER.APPROVED":
            custom_id = resource.get("purchase_units", [{}])[0].get("custom_id")
            try:
                invoice_id = int(custom_id) if custom_id else None
            except (TypeError, ValueError):
                invoice_id = None
        elif event_type == "PAYMENT.CAPTURE.COMPLETED":
            custom_id = resource.get("custom_id") or resource.get("invoice_id")
            try:
                invoice_id = int(custom_id) if custom_id else None
            except (TypeError, ValueError):
                invoice_id = None
            amt = resource.get("amount") or {}
            try:
                amount = Decimal(str(amt.get("value") or "0"))
            except Exception:
                amount = Decimal("0")
            currency = (amt.get("currency_code") or "EUR").upper()
            transaction_id = resource.get("id") or transaction_id

        return WebhookResult(
            valid=True,
            event_type=event_type,
            transaction_id=transaction_id,
            invoice_id=invoice_id,
            amount=amount,
            currency=currency,
            raw=event,
        )
