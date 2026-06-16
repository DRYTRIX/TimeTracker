"""Tests for payment provider registry."""

from app.payments.registry import PROVIDERS
from app.payments.stripe_provider import StripeProvider


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
