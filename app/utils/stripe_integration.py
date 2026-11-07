"""
Stripe payment gateway integration utilities.
"""

import logging
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, Optional

import stripe
from flask import current_app

logger = logging.getLogger(__name__)

# Stripe takes amounts in the currency's smallest unit. Most currencies have
# two decimals (cents), but these have none or three:
# https://docs.stripe.com/currencies#zero-decimal
# ISK, UGX, HUF and TWD are listed there as special cases: Stripe takes them
# in the two-decimal form, so they are intentionally not in these sets.
ZERO_DECIMAL_CURRENCIES = frozenset(
    {"BIF", "CLP", "DJF", "GNF", "JPY", "KMF", "KRW", "MGA", "PYG", "RWF", "VND", "VUV", "XAF", "XOF", "XPF"}
)
THREE_DECIMAL_CURRENCIES = frozenset({"BHD", "JOD", "KWD", "OMR", "TND"})


def _minor_unit_factor(currency: str) -> int:
    code = (currency or "").upper()
    if code in ZERO_DECIMAL_CURRENCIES:
        return 1
    if code in THREE_DECIMAL_CURRENCIES:
        return 1000
    return 100


def to_stripe_amount(amount, currency: str) -> int:
    """Convert an amount in major units (e.g. 19.99 EUR) to Stripe's integer amount."""
    factor = _minor_unit_factor(currency)
    return int((Decimal(str(amount)) * factor).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def from_stripe_amount(stripe_amount, currency: str) -> Decimal:
    """Convert Stripe's integer amount back to major units."""
    return Decimal(str(stripe_amount)) / _minor_unit_factor(currency)


class StripeIntegration:
    """
    Stripe payment gateway integration.
    """

    def __init__(self, api_key: str):
        """
        Initialize Stripe integration.

        Args:
            api_key: Stripe API key (secret key)
        """
        self.api_key = api_key
        stripe.api_key = api_key

    def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        invoice_id: int,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a Stripe PaymentIntent.

        Returns:
            dict with 'success', 'client_secret', and 'payment_intent' keys
        """
        try:
            amount_cents = to_stripe_amount(amount, currency)

            payment_intent_data = {
                "amount": amount_cents,
                "currency": currency.lower(),
                "metadata": {"invoice_id": str(invoice_id), **(metadata or {})},
            }

            if description:
                payment_intent_data["description"] = description

            payment_intent = stripe.PaymentIntent.create(**payment_intent_data)

            return {"success": True, "client_secret": payment_intent.client_secret, "payment_intent": payment_intent}
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating payment intent: {e}")
            return {"success": False, "message": str(e), "error_code": e.code if hasattr(e, "code") else None}
        except Exception as e:
            logger.error(f"Error creating payment intent: {e}")
            return {"success": False, "message": f"Error creating payment intent: {str(e)}"}

    def verify_webhook(self, payload: bytes, signature: str, webhook_secret: str) -> Optional[stripe.Event]:
        """
        Verify and parse a Stripe webhook.

        Returns:
            Stripe Event object if valid, None otherwise
        """
        try:
            event = stripe.Webhook.construct_event(payload, signature, webhook_secret)
            return event
        except ValueError as e:
            logger.error(f"Invalid payload: {e}")
            return None
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid signature: {e}")
            return None

    def get_payment_intent(self, payment_intent_id: str) -> Optional[stripe.PaymentIntent]:
        """Retrieve a PaymentIntent from Stripe"""
        try:
            return stripe.PaymentIntent.retrieve(payment_intent_id)
        except stripe.error.StripeError as e:
            logger.error(f"Error retrieving payment intent: {e}")
            return None

    def create_checkout_session(
        self,
        invoice_id: int,
        amount: Decimal,
        currency: str,
        success_url: str,
        cancel_url: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a Stripe Checkout Session.

        Returns:
            dict with 'success', 'session_id', and 'url' keys
        """
        try:
            amount_cents = to_stripe_amount(amount, currency)

            session_data = {
                "payment_method_types": ["card"],
                "line_items": [
                    {
                        "price_data": {
                            "currency": currency.lower(),
                            "product_data": {
                                "name": description or f"Invoice #{invoice_id}",
                            },
                            "unit_amount": amount_cents,
                        },
                        "quantity": 1,
                    }
                ],
                "mode": "payment",
                "success_url": success_url,
                "cancel_url": cancel_url,
                "metadata": {"invoice_id": str(invoice_id)},
            }

            session = stripe.checkout.Session.create(**session_data)

            return {"success": True, "session_id": session.id, "url": session.url}
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout session: {e}")
            return {"success": False, "message": str(e), "error_code": e.code if hasattr(e, "code") else None}
        except Exception as e:
            logger.error(f"Error creating checkout session: {e}")
            return {"success": False, "message": f"Error creating checkout session: {str(e)}"}
