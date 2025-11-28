"""
Stripe payment gateway integration utilities.
"""

import logging
from typing import Optional, Dict, Any
from decimal import Decimal
import stripe
from flask import current_app

logger = logging.getLogger(__name__)


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
            # Convert amount to cents
            amount_cents = int(amount * 100)

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
            amount_cents = int(amount * 100)

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
