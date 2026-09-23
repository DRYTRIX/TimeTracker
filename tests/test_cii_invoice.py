"""Tests for CII (Cross-Industry Invoice) generator for Factur-X / ZUGFeRD."""
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.utils.cii_invoice import CIIParty, build_cii_invoice_xml, FACTURX_GUIDELINE_EN16931
from app.utils.invoice_validators import validate_cii_wellformed, validate_cii_en16931


def _make_invoice(**overrides):
    defaults = dict(
        id=1,
        invoice_number="INV-CII-001",
        issue_date=date(2024, 3, 15),
        due_date=date(2024, 4, 14),
        currency_code="EUR",
        subtotal=Decimal("200.00"),
        tax_rate=Decimal("21.00"),
        tax_amount=Decimal("42.00"),
        total_amount=Decimal("242.00"),
        amount_paid=Decimal("0"),
        notes="Test invoice notes",
        buyer_reference="PO-99",
        vat_category=None,
        vat_exemption_reason=None,
        vat_exemption_code=None,
        project=None,
        client=None,
        client_name="Buyer Inc",
        client_email=None,
        client_address=None,
        items=[
            SimpleNamespace(description="Consulting", quantity=Decimal("2"), unit_price=Decimal("100.00"), total_amount=Decimal("200.00")),
        ],
        expenses=[],
        extra_goods=[],
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_seller(**overrides):
    defaults = dict(
        name="Seller GmbH",
        tax_id="DE123456789",
        address_line="Hauptstr. 1",
        street="Hauptstr. 1",
        city="Berlin",
        postcode="10115",
        country_code="DE",
        email="seller@example.de",
        phone="+49 30 12345",
        endpoint_id="9930:DE123456789",
        endpoint_scheme_id="9930",
        iban=None,
        bic=None,
    )
    defaults.update(overrides)
    return CIIParty(**defaults)


def _make_buyer(**overrides):
    defaults = dict(
        name="Buyer BV",
        tax_id="NL123456789B01",
        address_line="Keizersgracht 1",
        city="Amsterdam",
        postcode="1015 AA",
        country_code="NL",
        email="buyer@example.nl",
    )
    defaults.update(overrides)
    return CIIParty(**defaults)


@pytest.mark.unit
def test_build_cii_produces_valid_xml():
    invoice = _make_invoice()
    seller = _make_seller()
    buyer = _make_buyer()
    xml, sha256 = build_cii_invoice_xml(invoice, seller, buyer)
    assert sha256
    passed, msgs = validate_cii_wellformed(xml)
    assert passed is True, f"CII well-formedness failed: {msgs}"


@pytest.mark.unit
def test_build_cii_passes_en16931_validation():
    invoice = _make_invoice()
    seller = _make_seller()
    buyer = _make_buyer()
    xml, _ = build_cii_invoice_xml(invoice, seller, buyer)
    passed, issues = validate_cii_en16931(xml)
    assert passed is True, f"CII EN 16931 validation failed: {issues}"


@pytest.mark.unit
def test_cii_contains_guideline_id():
    invoice = _make_invoice()
    xml, _ = build_cii_invoice_xml(invoice, _make_seller(), _make_buyer())
    assert FACTURX_GUIDELINE_EN16931 in xml


@pytest.mark.unit
def test_cii_contains_invoice_number():
    invoice = _make_invoice(invoice_number="INV-2024-999")
    xml, _ = build_cii_invoice_xml(invoice, _make_seller(), _make_buyer())
    assert "INV-2024-999" in xml


@pytest.mark.unit
def test_cii_contains_type_code_380():
    xml, _ = build_cii_invoice_xml(_make_invoice(), _make_seller(), _make_buyer())
    assert ">380<" in xml


@pytest.mark.unit
def test_cii_contains_issue_date_format_102():
    invoice = _make_invoice(issue_date=date(2024, 3, 15))
    xml, _ = build_cii_invoice_xml(invoice, _make_seller(), _make_buyer())
    assert "20240315" in xml
    assert 'format="102"' in xml


@pytest.mark.unit
def test_cii_contains_seller_and_buyer():
    xml, _ = build_cii_invoice_xml(
        _make_invoice(),
        _make_seller(name="ACME Corp"),
        _make_buyer(name="Widget Ltd"),
    )
    assert "ACME Corp" in xml
    assert "Widget Ltd" in xml


@pytest.mark.unit
def test_cii_contains_tax_info():
    xml, _ = build_cii_invoice_xml(
        _make_invoice(tax_rate=Decimal("21"), tax_amount=Decimal("42.00")),
        _make_seller(),
        _make_buyer(),
    )
    assert "VAT" in xml
    assert "42.00" in xml
    assert "21.00" in xml


@pytest.mark.unit
def test_cii_contains_monetary_totals():
    invoice = _make_invoice(
        subtotal=Decimal("200.00"),
        tax_amount=Decimal("42.00"),
        total_amount=Decimal("242.00"),
    )
    xml, _ = build_cii_invoice_xml(invoice, _make_seller(), _make_buyer())
    assert "200.00" in xml
    assert "242.00" in xml
    assert "DuePayableAmount" in xml


@pytest.mark.unit
def test_cii_contains_line_items():
    items = [
        SimpleNamespace(description="Design", quantity=Decimal("5"), unit_price=Decimal("80.00"), total_amount=Decimal("400.00")),
        SimpleNamespace(description="Dev", quantity=Decimal("10"), unit_price=Decimal("100.00"), total_amount=Decimal("1000.00")),
    ]
    invoice = _make_invoice(items=items)
    xml, _ = build_cii_invoice_xml(invoice, _make_seller(), _make_buyer())
    assert "Design" in xml
    assert "Dev" in xml
    assert "BilledQuantity" in xml
    assert 'unitCode="C62"' in xml


@pytest.mark.unit
def test_cii_adds_placeholder_line_when_no_items():
    invoice = _make_invoice(items=[], expenses=[], extra_goods=[])
    xml, _ = build_cii_invoice_xml(invoice, _make_seller(), _make_buyer())
    assert "IncludedSupplyChainTradeLineItem" in xml


@pytest.mark.unit
def test_cii_includes_buyer_reference():
    invoice = _make_invoice(buyer_reference="REF-42")
    xml, _ = build_cii_invoice_xml(invoice, _make_seller(), _make_buyer())
    assert "BuyerReference" in xml
    assert "REF-42" in xml


@pytest.mark.unit
def test_cii_includes_notes():
    invoice = _make_invoice(notes="Payment within 14 days")
    xml, _ = build_cii_invoice_xml(invoice, _make_seller(), _make_buyer())
    assert "Payment within 14 days" in xml
    assert "IncludedNote" in xml


@pytest.mark.unit
def test_cii_includes_due_date():
    invoice = _make_invoice(due_date=date(2024, 4, 14))
    xml, _ = build_cii_invoice_xml(invoice, _make_seller(), _make_buyer())
    assert "20240414" in xml
    assert "DueDateDateTime" in xml


@pytest.mark.unit
def test_cii_includes_seller_tax_registration():
    seller = _make_seller(tax_id="BE0123456789")
    xml, _ = build_cii_invoice_xml(_make_invoice(), seller, _make_buyer())
    assert "SpecifiedTaxRegistration" in xml
    assert "BE0123456789" in xml
    assert 'schemeID="VA"' in xml


@pytest.mark.unit
def test_cii_includes_seller_endpoint_as_uri():
    seller = _make_seller(endpoint_id="0088:123456", endpoint_scheme_id="0088")
    xml, _ = build_cii_invoice_xml(_make_invoice(), seller, _make_buyer())
    assert "URIUniversalCommunication" in xml
    assert "0088:123456" in xml
    assert 'schemeID="0088"' in xml
    # Peppol endpoint must NOT be in SpecifiedLegalOrganization
    assert "SpecifiedLegalOrganization" not in xml


@pytest.mark.unit
def test_cii_sha256_changes_with_content():
    inv1 = _make_invoice(invoice_number="A")
    inv2 = _make_invoice(invoice_number="B")
    _, sha1 = build_cii_invoice_xml(inv1, _make_seller(), _make_buyer())
    _, sha2 = build_cii_invoice_xml(inv2, _make_seller(), _make_buyer())
    assert sha1 != sha2


@pytest.mark.unit
def test_cii_handles_zero_tax_as_exempt():
    """Zero tax_rate without override uses category E with exemption reason (not Z+VATEX-EU-O)."""
    invoice = _make_invoice(tax_rate=Decimal("0"), tax_amount=Decimal("0"))
    settings = SimpleNamespace(
        invoices_default_vat_category="E",
        invoices_default_vat_exemption_reason="Kleinunternehmerregelung §6 Abs. 1 Z 27 UStG",
        invoices_default_vat_exemption_code="VATEX-EU-O",
    )
    xml, _ = build_cii_invoice_xml(invoice, _make_seller(), _make_buyer(), settings=settings)
    assert ">E<" in xml or ">E</" in xml
    assert "ExemptionReason" in xml
    assert "VATEX-EU-O" in xml
    # currencyID only on TaxTotalAmount
    assert 'currencyID="EUR"' in xml
    assert xml.count('currencyID="EUR"') == 1
    passed, issues = validate_cii_en16931(xml)
    assert passed is True, f"Failed: {issues}"


@pytest.mark.unit
def test_cii_zero_rated_z_has_no_exemption():
    invoice = _make_invoice(tax_rate=Decimal("0"), tax_amount=Decimal("0"), vat_category="Z")
    xml, _ = build_cii_invoice_xml(invoice, _make_seller(), _make_buyer())
    assert ">Z<" in xml or ">Z</" in xml
    # Header tax must not include ExemptionReason for Z
    assert "ExemptionReason" not in xml
    passed, issues = validate_cii_en16931(xml)
    assert passed is True, f"Failed: {issues}"


@pytest.mark.unit
def test_cii_reverse_charge_ae():
    invoice = _make_invoice(tax_rate=Decimal("0"), tax_amount=Decimal("0"), vat_category="AE")
    xml, _ = build_cii_invoice_xml(invoice, _make_seller(), _make_buyer())
    assert ">AE<" in xml or ">AE</" in xml
    assert "Reverse charge" in xml
    assert "VATEX-EU-AE" in xml


@pytest.mark.unit
def test_cii_tax_total_has_currency_id_only():
    invoice = _make_invoice(currency_code="USD")
    xml, _ = build_cii_invoice_xml(invoice, _make_seller(), _make_buyer())
    assert 'currencyID="USD"' in xml
    assert xml.count('currencyID="USD"') == 1


@pytest.mark.unit
def test_cii_postal_address_order():
    xml, _ = build_cii_invoice_xml(_make_invoice(), _make_seller(), _make_buyer())
    # PostcodeCode must appear before LineOne in PostalTradeAddress
    idx_pc = xml.find("PostcodeCode")
    idx_lo = xml.find("LineOne")
    assert idx_pc != -1 and idx_lo != -1
    assert idx_pc < idx_lo


@pytest.mark.unit
def test_cii_payment_means_when_iban():
    seller = _make_seller(iban="DE89370400440532013000", bic="COBADEFFXXX")
    xml, _ = build_cii_invoice_xml(_make_invoice(), seller, _make_buyer())
    assert "SpecifiedTradeSettlementPaymentMeans" in xml
    assert "DE89370400440532013000" in xml
    assert "COBADEFFXXX" in xml
    assert ">58<" in xml


@pytest.mark.unit
def test_cii_prepaid_amount():
    invoice = _make_invoice(amount_paid=Decimal("50.00"), total_amount=Decimal("242.00"))
    xml, _ = build_cii_invoice_xml(invoice, _make_seller(), _make_buyer())
    assert "TotalPrepaidAmount" in xml
    assert "50.00" in xml
    assert "192.00" in xml  # due payable


@pytest.mark.unit
def test_cii_address_fallback_to_line_one():
    seller = _make_seller(street=None, address_line="Fallback Street 9", postcode="1010", city="Wien")
    xml, _ = build_cii_invoice_xml(_make_invoice(), seller, _make_buyer())
    assert "Fallback Street 9" in xml


@pytest.mark.unit
def test_cii_lines_before_header_agreement():
    xml, _ = build_cii_invoice_xml(_make_invoice(), _make_seller(), _make_buyer())
    assert xml.find("IncludedSupplyChainTradeLineItem") < xml.find("ApplicableHeaderTradeAgreement")


@pytest.mark.unit
def test_cii_passes_facturx_xsd():
    """Validate generated CII against official Factur-X EN16931 XSD (factur-x package)."""
    pytest.importorskip("facturx")
    from facturx import xml_check_xsd

    invoice = _make_invoice()
    seller = _make_seller(iban="DE89370400440532013000", bic="COBADEFFXXX")
    buyer = _make_buyer()
    xml, _ = build_cii_invoice_xml(invoice, seller, buyer)
    # Raises on failure
    xml_check_xsd(xml.encode("utf-8"), flavor="factur-x", level="en16931")
