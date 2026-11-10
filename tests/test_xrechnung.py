"""XRechnung 3.0 export tests."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.utils.xrechnung import (
    XRECHNUNG_30_CUSTOMIZATION_ID,
    build_xrechnung_ubl_invoice_xml,
    effective_buyer_reference,
    validate_xrechnung_ready,
)


def _settings(**kwargs):
    base = dict(
        company_name="Acme GmbH",
        company_street="Musterstraße 1",
        company_postcode="10115",
        company_city="Berlin",
        company_country="DE",
        company_tax_id="DE123456789",
        company_phone="+49 30 123456",
        company_email="billing@acme.de",
        company_iban="DE89370400440532013000",
        company_bic="COBADEFFXXX",
        company_address="Musterstraße 1, Berlin",
        peppol_sender_endpoint_id="",
        peppol_sender_scheme_id="",
        peppol_sender_country="DE",
        invoice_terms="Zahlbar innerhalb 30 Tagen.",
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def _client(**kwargs):
    base = dict(
        name="Behörde",
        street="Amtstraße 2",
        postcode="80331",
        city="München",
        country="DE",
        vat_id="DE987654321",
        address="Amtstraße 2",
        email="einkauf@behoerde.de",
        phone="+49 89 123456",
        leitweg_id="993-470090002-90",
    )
    base.update(kwargs)
    ns = SimpleNamespace(**base)
    ns.get_custom_field = lambda key, default="": default
    return ns


def _invoice(**kwargs):
    price = Decimal("100.00")
    item = SimpleNamespace(description="Beratung", quantity=1, unit_price=price, total_amount=price)
    base = dict(
        id=1,
        invoice_number="INV-2026-1",
        issue_date=date(2026, 11, 7),
        due_date=date(2026, 12, 7),
        currency_code="EUR",
        subtotal=price,
        tax_rate=Decimal("19"),
        tax_amount=Decimal("19.00"),
        total_amount=Decimal("119.00"),
        buyer_reference=None,
        notes=None,
        items=[item],
        expenses=[],
        extra_goods=[],
        client_name="Behörde",
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_effective_buyer_reference_uses_leitweg_id():
    inv = _invoice(buyer_reference=None)
    client = _client(leitweg_id="993-123-00")
    assert effective_buyer_reference(inv, client) == "993-123-00"


def test_validate_fails_without_leitweg_id():
    inv = _invoice(buyer_reference=None)
    client = _client(leitweg_id=None)
    issues = validate_xrechnung_ready(inv, _settings(), client)
    assert any("Leitweg" in msg or "BT-10" in msg for msg in issues)


def test_build_xml_contains_customization_and_buyer_reference():
    inv = _invoice()
    settings = _settings()
    client = _client()
    xml, _sha = build_xrechnung_ubl_invoice_xml(inv, settings, client)
    assert XRECHNUNG_30_CUSTOMIZATION_ID in xml
    assert "<cbc:BuyerReference>993-470090002-90</cbc:BuyerReference>" in xml
    assert "DE89370400440532013000" in xml
    assert "PaymentMeans" in xml
