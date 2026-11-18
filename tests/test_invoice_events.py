"""Unit tests for invoice webhook event emission helpers."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.constants import WebhookEvent
from app.utils.invoice_events import emit_credit_note_event, emit_invoice_event, emit_payment_event

pytestmark = [pytest.mark.unit]


def test_emit_invoice_event_builds_payload():
    invoice = SimpleNamespace(
        id=7,
        invoice_number="INV-001",
        status="sent",
        payment_status="unpaid",
        client_id=3,
        project_id=9,
    )
    with patch("app.utils.invoice_events.emit_event") as mock_emit:
        emit_invoice_event(WebhookEvent.INVOICE_SENT.value, invoice, recipient_email="a@b.c")
    mock_emit.assert_called_once()
    event_name, payload = mock_emit.call_args[0]
    assert event_name == "invoice.sent"
    assert payload["invoice_id"] == 7
    assert payload["invoice_number"] == "INV-001"
    assert payload["recipient_email"] == "a@b.c"


def test_emit_invoice_paid_via_payment_service_path():
    """Smoke: PaymentService emits invoice.paid when fully paid (mocked commit)."""
    from decimal import Decimal
    from unittest.mock import MagicMock, patch

    from app.services.payment_service import PaymentService

    invoice = MagicMock()
    invoice.id = 1
    invoice.currency_code = "EUR"
    invoice.outstanding_amount = Decimal("100")
    invoice.payment_status = "fully_paid"
    invoice.client_id = None
    invoice.client_email = None

    payment = MagicMock()
    payment.id = 11
    payment.amount = Decimal("100")

    svc = PaymentService()
    svc.invoice_repo = MagicMock()
    svc.invoice_repo.get_by_id.return_value = invoice
    svc.payment_repo = MagicMock()
    svc.payment_repo.create.return_value = payment
    svc.payment_repo.get_total_for_invoice.return_value = Decimal("100")

    with (
        patch("app.services.payment_service.safe_commit", return_value=True),
        patch("app.services.payment_service.db.session.flush"),
        patch("app.services.payment_service.emit_event"),
        patch("app.utils.workflow_bridge.fire_invoice_paid_workflow"),
        patch("app.utils.invoice_events.emit_event") as mock_emit,
    ):
        from datetime import date

        result = svc.create_payment(
            invoice_id=1,
            amount=Decimal("100"),
            payment_date=date.today(),
            received_by=1,
            status="completed",
        )
    assert result["success"] is True
    paid_calls = [c for c in mock_emit.call_args_list if c[0][0] == WebhookEvent.INVOICE_PAID.value]
    assert paid_calls, "expected invoice.paid emit"


def test_emit_credit_note_and_payment_helpers():
    cn = SimpleNamespace(id=2, credit_number="CN-1", invoice_id=1, amount=10, status="draft")
    payment = SimpleNamespace(id=5, invoice_id=1, amount=20, status="refunded")
    with patch("app.utils.invoice_events.emit_event") as mock_emit:
        emit_credit_note_event(WebhookEvent.CREDIT_NOTE_CREATED.value, cn)
        emit_payment_event(WebhookEvent.PAYMENT_REFUNDED.value, payment)
    assert mock_emit.call_count == 2
    assert mock_emit.call_args_list[0][0][0] == "credit_note.created"
    assert mock_emit.call_args_list[1][0][0] == "payment.refunded"
