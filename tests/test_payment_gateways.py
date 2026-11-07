"""Tests for payment provider registry."""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from app.payments.registry import PROVIDERS
from app.payments.stripe_provider import StripeProvider
from app.utils.stripe_integration import StripeIntegration


def test_provider_registry_includes_stripe_and_paypal():
    assert "stripe" in PROVIDERS
    assert "paypal" in PROVIDERS
    assert PROVIDERS["stripe"] is StripeProvider


def test_stripe_checkout_requires_api_key():
    provider = StripeProvider({"publishable_key": "pk_test"}, is_test_mode=True)
    result = provider.create_checkout_session(
        invoice_id=1,
        amount=100,
        currency="EUR",
        success_url="https://example.com/success",
        cancel_url="https://example.com/cancel",
    )
    assert result.success is False
    assert "API key" in (result.message or "")


def test_parse_gateway_config_plain_json(app):
    from app.models.payment_gateway import PaymentGateway
    from app.payments.registry import parse_gateway_config

    with app.app_context():
        gateway = PaymentGateway(
            name="test-stripe",
            provider="stripe",
            config='{"api_key": "sk_test"}',
            is_active=True,
        )
        parsed = parse_gateway_config(gateway)
        assert parsed.get("api_key") == "sk_test"


def _create_stripe_checkout(currency, amount):
    provider = StripeProvider({"api_key": "sk_test"}, is_test_mode=True)
    session = SimpleNamespace(id="cs_test_1", url="https://checkout.stripe.test/cs_test_1")
    with patch("stripe.checkout.Session.create", return_value=session) as create:
        result = provider.create_checkout_session(
            invoice_id=1,
            amount=Decimal(amount),
            currency=currency,
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
        )
    assert result.success is True
    return create.call_args.kwargs["line_items"][0]["price_data"]["unit_amount"]


def test_stripe_checkout_amount_in_cents_for_two_decimal_currency():
    assert _create_stripe_checkout("EUR", "19.99") == 1999


def test_stripe_checkout_amount_for_zero_decimal_currency():
    # Stripe takes JPY (and other zero-decimal currencies) in whole units.
    assert _create_stripe_checkout("JPY", "10000.00") == 10000


def test_stripe_checkout_rounds_fractional_zero_decimal_amount_half_up():
    # Invoice totals are stored with two decimals, so a JPY balance can be fractional.
    assert _create_stripe_checkout("JPY", "12345.67") == 12346
    assert _create_stripe_checkout("JPY", "12345.49") == 12345


def test_stripe_checkout_amount_for_three_decimal_currency():
    assert _create_stripe_checkout("KWD", "12.50") == 12500


def _stripe_webhook_amount(currency, amount_total):
    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "payment_intent": "pi_test_1",
                "metadata": {"invoice_id": "1"},
                "amount_total": amount_total,
                "currency": currency,
            }
        },
    }
    provider = StripeProvider({"api_key": "sk_test", "webhook_secret": "whsec_test"}, is_test_mode=True)
    with patch.object(StripeIntegration, "verify_webhook", return_value=event):
        result = provider.verify_webhook(b"{}", {"Stripe-Signature": "t=1,v1=x"})
    assert result.valid is True
    return result.amount


def test_stripe_webhook_amount_for_two_decimal_currency():
    assert _stripe_webhook_amount("eur", 1999) == Decimal("19.99")


def test_stripe_webhook_amount_for_zero_decimal_currency():
    assert _stripe_webhook_amount("jpy", 10000) == Decimal("10000")


def test_stripe_webhook_amount_for_three_decimal_currency():
    assert _stripe_webhook_amount("kwd", 12500) == Decimal("12.5")


def test_stripe_payment_intent_amount_for_zero_decimal_currency():
    intent = SimpleNamespace(client_secret="pi_test_1_secret")
    with patch("stripe.PaymentIntent.create", return_value=intent) as create:
        result = StripeIntegration("sk_test").create_payment_intent(
            amount=Decimal("10000.00"), currency="JPY", invoice_id=1
        )
    assert result["success"] is True
    assert create.call_args.kwargs["amount"] == 10000
