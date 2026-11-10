"""Bank reconciliation CSV parse, match suggestions, and confirm → Payment."""

from datetime import date
from decimal import Decimal

import pytest

from app import db
from app.models import Payment
from app.models.bank_transaction import BankTransaction
from app.services.bank_reconciliation_service import BankReconciliationService


@pytest.fixture
def open_invoice(app, invoice):
    invoice.status = "sent"
    invoice.payment_status = "unpaid"
    invoice.total_amount = Decimal("150.00")
    invoice.amount_paid = Decimal("0.00")
    invoice.invoice_number = "INV-RECON-001"
    db.session.commit()
    db.session.refresh(invoice)
    return invoice


def test_parse_csv_basic():
    csv_body = (
        "date,amount,reference,counterparty\n"
        "2024-06-01,150.00,Payment INV-RECON-001,Acme Corp\n"
        "2024-06-02,20.50,Fee,Bank\n"
    )
    rows = BankReconciliationService().parse_csv(csv_body, account_label="Main")
    assert len(rows) == 2
    assert rows[0]["booking_date"] == date(2024, 6, 1)
    assert rows[0]["amount"] == Decimal("150.00")
    assert "INV-RECON-001" in (rows[0]["reference"] or "")
    assert rows[0]["counterparty"] == "Acme Corp"
    assert rows[0]["account_label"] == "Main"


def test_suggest_matches_by_amount_and_reference(app, open_invoice):
    service = BankReconciliationService()
    parsed = service.parse_csv(
        "date,amount,reference,counterparty\n"
        f"2024-06-01,{open_invoice.total_amount},Payment {open_invoice.invoice_number},Client\n"
    )
    created = service.import_rows(parsed)
    txn = created[0]
    suggestions = service.suggest_matches(txn)
    assert suggestions
    assert suggestions[0]["invoice_id"] == open_invoice.id
    assert suggestions[0]["score"] >= 5.0


def test_confirm_match_creates_payment(app, open_invoice, admin_user):
    service = BankReconciliationService()
    parsed = service.parse_csv(
        "date,amount,reference,counterparty\n"
        f"{date.today().isoformat()},{open_invoice.total_amount},{open_invoice.invoice_number},Client\n"
    )
    txn = service.import_rows(parsed)[0]

    result = service.confirm_match(txn.id, open_invoice.id, received_by=admin_user.id)
    assert result["success"] is True

    db.session.refresh(txn)
    assert txn.match_status == BankTransaction.MATCH_MATCHED
    assert txn.matched_invoice_id == open_invoice.id
    assert txn.matched_payment_id is not None

    payment = Payment.query.get(txn.matched_payment_id)
    assert payment is not None
    assert payment.invoice_id == open_invoice.id
    assert Decimal(payment.amount) == abs(Decimal(txn.amount))

    db.session.refresh(open_invoice)
    assert open_invoice.payment_status in ("fully_paid", "partially_paid", "overpaid")
