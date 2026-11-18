"""Phase 3 credit note tests."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from factories import ClientFactory, InvoiceFactory, InvoiceItemFactory


@pytest.fixture
def sent_invoice(app, user, project):
    from app import db

    client = ClientFactory(name="CN Client")
    db.session.commit()
    inv = InvoiceFactory(
        project_id=project.id,
        client_id=client.id,
        client_name=client.name,
        created_by=user.id,
        due_date=date.today() + timedelta(days=14),
        tax_rate=Decimal("20.00"),
    )
    inv.status = "sent"
    inv.tax_rate = Decimal("20.00")
    db.session.commit()
    InvoiceItemFactory(
        invoice_id=inv.id,
        description="Consulting",
        quantity=Decimal("10.00"),
        unit_price=Decimal("100.00"),
    )
    db.session.commit()
    inv.calculate_totals()
    db.session.commit()
    return inv


def test_full_credit_cancels_invoice_and_covers_outstanding(app, user, sent_invoice):
    from app import db
    from app.services.credit_note_service import CreditNoteService

    inv = sent_invoice
    assert inv.outstanding_amount > 0
    cn = CreditNoteService.create_full_credit(inv, user.id, reason="Full cancel")
    db.session.refresh(inv)
    db.session.refresh(cn)
    assert cn.status == "issued"
    assert cn.total_amount == inv.total_amount or cn.amount == inv.total_amount
    assert inv.status == "cancelled"
    assert inv.outstanding_amount <= Decimal("0.01")


def test_amount_credit_reduces_outstanding(app, user, sent_invoice):
    from app import db
    from app.services.credit_note_service import CreditNoteService

    inv = sent_invoice
    before = inv.outstanding_amount
    cn = CreditNoteService.create_amount_credit(
        inv, user.id, Decimal("50.00"), reason="Partial", description="Partial credit", auto_issue=True
    )
    db.session.refresh(inv)
    assert cn.status == "issued"
    assert inv.outstanding_amount == before - Decimal("50.00")
    assert inv.status != "cancelled"


def test_credit_note_pdf_endpoint(app, client, user, sent_invoice):
    from app.services.credit_note_service import CreditNoteService

    cn = CreditNoteService.create_amount_credit(
        sent_invoice, user.id, Decimal("25.00"), reason="PDF test", auto_issue=True
    )
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
        sess["_fresh"] = True
    resp = client.get(f"/credit-notes/{cn.id}/pdf")
    assert resp.status_code == 200
    assert resp.mimetype == "application/pdf"
    assert resp.data[:4] == b"%PDF"


def test_ubl_credit_note_contains_381(app, user, sent_invoice):
    from app.integrations.peppol import PeppolParty, build_peppol_ubl_credit_note_xml
    from app.services.credit_note_service import CreditNoteService

    cn = CreditNoteService.create_full_credit(sent_invoice, user.id, reason="UBL", auto_issue=True)
    supplier = PeppolParty(endpoint_id="123", endpoint_scheme_id="0088", name="Supplier")
    customer = PeppolParty(endpoint_id="456", endpoint_scheme_id="0088", name="Customer")
    xml, doc_id = build_peppol_ubl_credit_note_xml(cn, sent_invoice, supplier, customer)
    assert "381" in xml
    assert "CreditNote" in xml
    assert sent_invoice.invoice_number in xml
    assert doc_id == cn.credit_number


def test_fatturapa_credit_note_td04(app, user, sent_invoice):
    from app.models import Settings
    from app.services.credit_note_service import CreditNoteService
    from app.utils.fatturapa import build_fatturapa_credit_note_xml

    cn = CreditNoteService.create_amount_credit(sent_invoice, user.id, Decimal("10.00"), reason="TD04", auto_issue=True)
    settings = Settings.get_settings()
    xml_bytes, filename = build_fatturapa_credit_note_xml(cn, sent_invoice, settings, client=None)
    xml = xml_bytes.decode("utf-8") if isinstance(xml_bytes, (bytes, bytearray)) else xml_bytes
    assert "TD04" in xml
    assert "DatiFattureCollegate" in xml or sent_invoice.invoice_number in xml
