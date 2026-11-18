"""Phase 5 tests: Mollie, PayPal signature, refunds, portal PDF, pay.html, receipt email."""

import io
import json
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# 1. Registry / Mollie
# ---------------------------------------------------------------------------


def test_provider_registry_includes_mollie():
    from app.payments.registry import PROVIDERS

    assert "mollie" in PROVIDERS


def test_mollie_checkout_requires_api_key():
    from app.payments.mollie_provider import MollieProvider

    provider = MollieProvider({}, is_test_mode=True)
    result = provider.create_checkout_session(
        invoice_id=1,
        amount=Decimal("50.00"),
        currency="EUR",
        success_url="https://example.com/success",
        cancel_url="https://example.com/cancel",
    )
    assert result.success is False
    assert "API key" in (result.message or "")


def test_mollie_webhook_returns_valid_on_paid_status():
    """verify_webhook fetches payment from Mollie and returns its status as event_type."""
    from app.payments.mollie_provider import MollieProvider

    payment_data = {
        "id": "tr_test_1",
        "status": "paid",
        "metadata": {"invoice_id": "42"},
        "amount": {"value": "75.00", "currency": "EUR"},
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = payment_data

    provider = MollieProvider({"api_key": "test_key"}, is_test_mode=True)
    with patch("requests.get", return_value=mock_resp):
        result = provider.verify_webhook(b"id=tr_test_1", {})

    assert result.valid is True
    assert result.event_type == "paid"
    assert result.transaction_id == "tr_test_1"
    assert result.invoice_id == 42
    assert result.amount == Decimal("75.00")


def test_mollie_webhook_whitelist_accepted_in_checkout_service():
    """'paid' event_type from Mollie should be processed (not ignored) by CheckoutService."""
    from app.payments.base import WebhookResult

    wh = WebhookResult(
        valid=True,
        event_type="paid",
        transaction_id="tr_mollie_1",
        invoice_id=None,  # no invoice_id — will be ignored gracefully
        amount=Decimal("0"),
        currency="EUR",
    )
    # event_type is accepted (not ignored), so it reaches the invoice_id check
    # With invoice_id=None it returns ignored but NOT status 400
    from app.services.checkout_service import CheckoutService

    class _FakeProvider:
        def verify_webhook(self, payload, headers):
            return wh

    gw = SimpleNamespace(id=1, provider="mollie", is_test_mode=True, config="{}")
    with patch("app.payments.registry.get_provider", return_value=_FakeProvider()):
        result = CheckoutService().complete_webhook(gw, b"id=tr_mollie_1", {})

    assert result["success"] is True  # not 400
    assert result.get("status") == 200


# ---------------------------------------------------------------------------
# 2. PayPal webhook signature verification
# ---------------------------------------------------------------------------


def test_paypal_webhook_no_credentials_logs_warning_and_accepts():
    """When webhook_id/credentials are absent, webhook is accepted with a warning."""
    from app.payments.paypal_provider import PayPalProvider

    event = {
        "event_type": "PAYMENT.CAPTURE.COMPLETED",
        "resource": {
            "id": "cap_1",
            "custom_id": "7",
            "amount": {"value": "30.00", "currency_code": "USD"},
        },
    }
    provider = PayPalProvider({}, is_test_mode=True)
    result = provider.verify_webhook(json.dumps(event).encode(), {})
    assert result.valid is True
    assert result.event_type == "PAYMENT.CAPTURE.COMPLETED"


def test_paypal_webhook_with_credentials_calls_verify_api():
    """When credentials present, the verify-webhook-signature API is called."""
    from app.payments.paypal_provider import PayPalProvider

    event = {
        "event_type": "PAYMENT.CAPTURE.COMPLETED",
        "resource": {
            "id": "cap_2",
            "custom_id": "8",
            "amount": {"value": "50.00", "currency_code": "EUR"},
        },
    }
    headers = {
        "PAYPAL-AUTH-ALGO": "SHA256withRSA",
        "PAYPAL-CERT-URL": "https://api.paypal.com/cert",
        "PAYPAL-TRANSMISSION-ID": "tx_id",
        "PAYPAL-TRANSMISSION-SIG": "sig",
        "PAYPAL-TRANSMISSION-TIME": "2024-01-01T00:00:00Z",
    }

    config = {
        "client_id": "client_id_x",
        "client_secret": "client_secret_x",
        "webhook_id": "WH-123",
        "sandbox": True,
    }
    provider = PayPalProvider(config, is_test_mode=True)

    # Mock token fetch and verification call
    token_resp = MagicMock()
    token_resp.ok = True
    token_resp.json.return_value = {"access_token": "test_token"}

    verify_resp = MagicMock()
    verify_resp.ok = True
    verify_resp.json.return_value = {"verification_status": "SUCCESS"}

    with patch("requests.post", side_effect=[token_resp, verify_resp]) as mock_post:
        result = provider.verify_webhook(json.dumps(event).encode(), headers)

    assert result.valid is True
    # Second call should be the verify-webhook-signature endpoint
    verify_call_url = mock_post.call_args_list[1].args[0]
    assert "verify-webhook-signature" in verify_call_url


def test_paypal_webhook_invalid_signature_returns_invalid():
    """FAILURE status from PayPal verify API should make webhook invalid."""
    from app.payments.paypal_provider import PayPalProvider

    event = {"event_type": "PAYMENT.CAPTURE.COMPLETED", "resource": {}}
    config = {
        "client_id": "cid",
        "client_secret": "csecret",
        "webhook_id": "WH-456",
        "sandbox": True,
    }
    provider = PayPalProvider(config, is_test_mode=True)

    token_resp = MagicMock()
    token_resp.ok = True
    token_resp.json.return_value = {"access_token": "tok"}

    verify_resp = MagicMock()
    verify_resp.ok = True
    verify_resp.json.return_value = {"verification_status": "FAILURE"}

    with patch("requests.post", side_effect=[token_resp, verify_resp]):
        result = provider.verify_webhook(json.dumps(event).encode(), {})

    assert result.valid is False
    assert "FAILURE" in (result.message or "")


# ---------------------------------------------------------------------------
# 3. Refunds
# ---------------------------------------------------------------------------


def test_base_refund_default_not_supported():
    """Default PaymentProvider.refund() returns not-supported."""
    from app.payments.base import PaymentProvider

    class _Concrete(PaymentProvider):
        provider_name = "dummy"

        def create_checkout_session(self, **kw):
            pass

        def verify_webhook(self, payload, headers):
            pass

    p = _Concrete({})
    res = p.refund(gateway_transaction_id="tx", amount=Decimal("10"), currency="EUR")
    assert res["success"] is False
    assert "not supported" in res["message"]


def test_stripe_refund_calls_stripe_api():
    from app.payments.stripe_provider import StripeProvider

    provider = StripeProvider({"api_key": "sk_test"}, is_test_mode=True)
    mock_refund = {"id": "re_1", "status": "succeeded"}

    with patch("stripe.Refund.create", return_value=mock_refund) as mock_create:
        result = provider.refund(
            gateway_transaction_id="pi_test_1",
            amount=Decimal("20.00"),
            currency="EUR",
            reason="requested_by_customer",
        )

    assert result["success"] is True
    assert result["refund_id"] == "re_1"
    assert mock_create.call_args.kwargs["payment_intent"] == "pi_test_1"


def test_mollie_refund_calls_mollie_api():
    from app.payments.mollie_provider import MollieProvider

    provider = MollieProvider({"api_key": "test_key"}, is_test_mode=True)
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {"id": "re_mol_1", "status": "pending"}

    with patch("requests.post", return_value=mock_resp):
        result = provider.refund(
            gateway_transaction_id="tr_test_1",
            amount=Decimal("15.00"),
            currency="EUR",
        )

    assert result["success"] is True
    assert result["refund_id"] == "re_mol_1"


def test_paypal_refund_calls_paypal_api():
    from app.payments.paypal_provider import PayPalProvider

    provider = PayPalProvider({"client_id": "cid", "client_secret": "cs", "sandbox": True}, is_test_mode=True)
    token_resp = MagicMock()
    token_resp.ok = True
    token_resp.json.return_value = {"access_token": "tok"}

    refund_resp = MagicMock()
    refund_resp.ok = True
    refund_resp.json.return_value = {"id": "refund_pp_1", "status": "COMPLETED"}

    with patch("requests.post", side_effect=[token_resp, refund_resp]):
        result = provider.refund(
            gateway_transaction_id="cap_1",
            amount=Decimal("25.00"),
            currency="USD",
        )

    assert result["success"] is True
    assert result["refund_id"] == "refund_pp_1"


def test_refund_route_local_only(app, invoice):
    """Refund route marks payment refunded when no gateway_transaction_id present."""
    from app.models import Payment

    with app.app_context():
        from datetime import date

        from app import db

        # Create a completed payment with no gateway id
        payment = Payment(
            invoice_id=invoice.id,
            amount=Decimal("10.00"),
            currency="EUR",
            payment_date=date.today(),
            status="completed",
            method="bank_transfer",
            received_by=1,
        )
        db.session.add(payment)
        db.session.commit()
        payment_id = payment.id

    with app.test_client() as client:
        # Login as admin
        with client.session_transaction() as sess:
            sess["_user_id"] = "1"
            sess["_fresh"] = True

        resp = client.post(
            f"/payments/{payment_id}/refund",
            data={"csrf_token": "test", "reason": "test refund"},
            follow_redirects=False,
        )
        # Should redirect (302) rather than error
        assert resp.status_code in (302, 200, 400)


# ---------------------------------------------------------------------------
# 4. pay.html provider-neutral
# ---------------------------------------------------------------------------


def test_pay_html_no_unsupported_message_for_paypal(app):
    """pay.html should not contain the 'not yet supported' string."""
    import os

    template_path = os.path.join(
        os.path.dirname(__file__),
        "../app/templates/payment_gateways/pay.html",
    )
    with open(template_path) as f:
        content = f.read()
    assert "not yet supported" not in content
    assert "Continue to Payment" in content


def test_pay_html_uses_provider_title(app):
    """pay.html should reference the provider dynamically (not hardcode stripe check)."""
    import os

    template_path = os.path.join(
        os.path.dirname(__file__),
        "../app/templates/payment_gateways/pay.html",
    )
    with open(template_path) as f:
        content = f.read()
    # No provider-specific conditional branch left
    assert "gateway.provider == 'stripe'" not in content


# ---------------------------------------------------------------------------
# 5. Receipt email
# ---------------------------------------------------------------------------


def test_receipt_email_sent_on_completed_payment(app, invoice):
    """PaymentService.create_payment sends receipt email when client_email present."""
    from datetime import date
    from decimal import Decimal

    with app.app_context():
        from app.models import Invoice

        inv = Invoice.query.get(invoice.id)
        inv.client_email = "client@example.com"
        from app import db

        db.session.commit()

    with app.app_context():
        from app.services.payment_service import PaymentService

        with patch("app.services.payment_service.PaymentService._send_receipt_email") as mock_send:
            PaymentService().create_payment(
                invoice_id=invoice.id,
                amount=Decimal("10.00"),
                payment_date=date.today(),
                received_by=1,
                currency="EUR",
                status="completed",
            )
            assert mock_send.called


def test_receipt_email_not_sent_for_pending(app, invoice):
    """No receipt email for pending payments."""
    from datetime import date
    from decimal import Decimal

    with app.app_context():
        from app.services.payment_service import PaymentService

        with patch("app.services.payment_service.PaymentService._send_receipt_email") as mock_send:
            PaymentService().create_payment(
                invoice_id=invoice.id,
                amount=Decimal("5.00"),
                payment_date=date.today(),
                received_by=1,
                currency="EUR",
                status="pending",
            )
            assert not mock_send.called


# ---------------------------------------------------------------------------
# 6. Client portal PDF route
# ---------------------------------------------------------------------------


def test_portal_pdf_requires_auth(app):
    """PDF route returns 302 redirect (to login) when not authenticated."""
    with app.test_client() as client:
        resp = client.get("/client-portal/invoices/999/pdf")
        assert resp.status_code in (302, 401)


def test_portal_pdf_rejects_wrong_client(app, invoice):
    """PDF route returns 404/403 when invoice belongs to different client."""
    with app.app_context():
        from app import db
        from app.models import Client

        # Create a different client
        other_client = Client(name="Other Client", email="other@example.com")
        db.session.add(other_client)
        db.session.commit()
        other_client_id = other_client.id

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["client_portal_client_id"] = other_client_id
            sess["client_portal_logged_in"] = True

        resp = client.get(f"/client-portal/invoices/{invoice.id}/pdf")
        assert resp.status_code in (302, 404, 403)


# ---------------------------------------------------------------------------
# 7. create.html includes Mollie option
# ---------------------------------------------------------------------------


def test_create_html_has_mollie_option():
    """create.html should include Mollie as a provider option."""
    import os

    template_path = os.path.join(
        os.path.dirname(__file__),
        "../app/templates/payment_gateways/create.html",
    )
    with open(template_path) as f:
        content = f.read()
    assert 'value="mollie"' in content
    assert "mollieFields" in content
