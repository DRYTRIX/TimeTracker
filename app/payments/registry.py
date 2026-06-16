"""Payment provider registry."""

import json
from typing import Dict, Type

from app.models.payment_gateway import PaymentGateway
from app.payments.base import PaymentProvider
from app.payments.paypal_provider import PayPalProvider
from app.payments.stripe_provider import StripeProvider
from app.utils.secret_crypto import decrypt_if_needed

PROVIDERS: Dict[str, Type[PaymentProvider]] = {
    "stripe": StripeProvider,
    "paypal": PayPalProvider,
}


def parse_gateway_config(gateway: PaymentGateway) -> dict:
    raw = gateway.config or ""
    if isinstance(raw, str):
        try:
            decrypted = decrypt_if_needed(raw)
            return json.loads(decrypted)
        except json.JSONDecodeError:
            return {}
    return raw or {}


def get_provider(gateway: PaymentGateway) -> PaymentProvider:
    cls = PROVIDERS.get(gateway.provider)
    if not cls:
        raise ValueError(f"Unsupported payment provider: {gateway.provider}")
    return cls(parse_gateway_config(gateway), is_test_mode=gateway.is_test_mode)
