"""Mollie payment provider (skeleton + live checkout when API key is configured)."""

from decimal import Decimal
from typing import Dict, Optional

import requests

from app.payments.base import CheckoutResult, PaymentProvider, WebhookResult


class MollieProvider(PaymentProvider):
    provider_name = "mollie"

    def _api_base(self) -> str:
        return "https://api.mollie.com/v2"

    def _headers(self) -> Optional[Dict[str, str]]:
        api_key = self.config.get("api_key")
        if not api_key:
            return None
        return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    def create_checkout_session(
        self,
        invoice_id: int,
        amount: Decimal,
        currency: str,
        success_url: str,
        cancel_url: str,
        description: Optional[str] = None,
    ) -> CheckoutResult:
        headers = self._headers()
        if not headers:
            return CheckoutResult(success=False, message="Mollie API key not configured")

        payload = {
            "amount": {"currency": currency.upper(), "value": f"{amount:.2f}"},
            "description": description or f"Invoice #{invoice_id}",
            "redirectUrl": success_url,
            "cancelUrl": cancel_url,
            "metadata": {"invoice_id": str(invoice_id)},
        }
        try:
            resp = requests.post(f"{self._api_base()}/payments", headers=headers, json=payload, timeout=30)
        except requests.RequestException as exc:
            return CheckoutResult(success=False, message=f"Mollie request failed: {exc}")

        if resp.status_code not in (200, 201):
            return CheckoutResult(
                success=False,
                message=f"Mollie error ({resp.status_code}): {resp.text[:200]}",
                raw={"status_code": resp.status_code, "body": resp.text},
            )

        data = resp.json()
        checkout_url = (data.get("_links") or {}).get("checkout", {}).get("href")
        if not checkout_url:
            return CheckoutResult(success=False, message="Mollie did not return a checkout URL", raw=data)

        return CheckoutResult(success=True, url=checkout_url, session_id=data.get("id"), raw=data)

    def verify_webhook(self, payload: bytes, headers: Dict[str, str]) -> WebhookResult:
        api_key = self.config.get("api_key")
        if not api_key:
            return WebhookResult(valid=False, message="Mollie API key not configured")

        try:
            body = payload.decode("utf-8") if payload else ""
        except Exception:
            body = ""

        payment_id = None
        if body.startswith("id="):
            payment_id = body.split("=", 1)[1].strip()
        if not payment_id:
            return WebhookResult(valid=False, message="Missing Mollie payment id in webhook body")

        try:
            resp = requests.get(
                f"{self._api_base()}/payments/{payment_id}",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=30,
            )
        except requests.RequestException as exc:
            return WebhookResult(valid=False, message=f"Mollie webhook verify failed: {exc}")

        if resp.status_code != 200:
            return WebhookResult(valid=False, message=f"Mollie payment lookup failed ({resp.status_code})")

        data = resp.json()
        metadata = data.get("metadata") or {}
        try:
            invoice_id = int(metadata.get("invoice_id") or 0)
        except (TypeError, ValueError):
            invoice_id = 0

        amount_obj = data.get("amount") or {}
        try:
            amount = Decimal(str(amount_obj.get("value") or "0"))
        except Exception:
            amount = Decimal("0")

        return WebhookResult(
            valid=True,
            event_type=data.get("status"),
            transaction_id=data.get("id"),
            invoice_id=invoice_id or None,
            amount=amount,
            currency=(amount_obj.get("currency") or "EUR").upper(),
            raw=data,
        )
