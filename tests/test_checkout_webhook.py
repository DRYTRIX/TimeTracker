"""Tests for CheckoutService webhook handling (money path).

Focuses on the two cases that matter most for a payment webhook:
  * an invalid provider signature is rejected (no payment recorded), and
  * a valid webhook is idempotent under re-delivery (no duplicate Payment).

The payment provider is faked via app.payments.registry.get_provider so the
verify_webhook result is fully controlled.
"""

from decimal import Decimal
from unittest.mock import patch

import pytest

pytestmark = [pytest.mark.integration]

from app import db
from app.models import Payment
from app.models.payment_gateway import PaymentGateway, PaymentTransaction
from app.payments.base import WebhookResult
from app.services.checkout_service import CheckoutService


class _FakeProvider:
    def __init__(self, webhook: WebhookResult):
        self._webhook = webhook

    def verify_webhook(self, payload, headers):
        return self._webhook


@pytest.fixture
def gateway(app):
    gw = PaymentGateway(
        name="test-stripe",
        provider="stripe",
        config='{"api_key": "sk_test", "webhook_secret": "whsec_test"}',
        is_active=True,
        is_test_mode=True,
    )
    db.session.add(gw)
    db.session.commit()
    return gw


def _valid_webhook(invoice_id):
    return WebhookResult(
        valid=True,
        event_type="payment_intent.succeeded",
        transaction_id="tx_idem_1",
        invoice_id=invoice_id,
        amount=Decimal("100.00"),
        currency="EUR",
        raw={"id": "evt_1"},
    )


def test_invalid_signature_is_rejected(app, gateway, invoice):
    bad = WebhookResult(valid=False, message="Invalid signature")
    with patch("app.payments.registry.get_provider", return_value=_FakeProvider(bad)):
        result = CheckoutService().complete_webhook(gateway, b"{}", {})
    assert result["success"] is False
    assert result["status"] == 400
    assert Payment.query.filter_by(invoice_id=invoice.id).count() == 0


def test_unrelated_event_is_ignored(app, gateway, invoice):
    wh = WebhookResult(valid=True, event_type="customer.created", transaction_id="tx_x", invoice_id=invoice.id)
    with patch("app.payments.registry.get_provider", return_value=_FakeProvider(wh)):
        result = CheckoutService().complete_webhook(gateway, b"{}", {})
    assert result["success"] is True
    assert result["status"] == 200
    assert Payment.query.filter_by(invoice_id=invoice.id).count() == 0


def test_valid_webhook_records_single_payment(app, gateway, invoice):
    wh = _valid_webhook(invoice.id)
    with patch("app.payments.registry.get_provider", return_value=_FakeProvider(wh)):
        result = CheckoutService().complete_webhook(gateway, b"{}", {})
    assert result["status"] == 200
    assert Payment.query.filter_by(gateway_transaction_id="tx_idem_1").count() == 1
    assert PaymentTransaction.query.filter_by(transaction_id="tx_idem_1").count() == 1


def test_replayed_webhook_is_idempotent(app, gateway, invoice):
    wh = _valid_webhook(invoice.id)
    with patch("app.payments.registry.get_provider", return_value=_FakeProvider(wh)):
        service = CheckoutService()
        service.complete_webhook(gateway, b"{}", {})
        # Same transaction redelivered
        service.complete_webhook(gateway, b"{}", {})

    assert Payment.query.filter_by(gateway_transaction_id="tx_idem_1").count() == 1
    assert PaymentTransaction.query.filter_by(transaction_id="tx_idem_1").count() == 1
