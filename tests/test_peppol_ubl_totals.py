"""Peppol BIS Billing 3.0 document totals (BG-22).

BR-CO-16: PayableAmount (BT-115) = TaxInclusiveAmount (BT-112) - PrepaidAmount (BT-113)
+ PayableRoundingAmount (BT-114). Payments already recorded on the invoice are the
prepaid amount, the same way the Factur-X/ZUGFeRD (CII) export reports them.
"""

import xml.etree.ElementTree as ET
from datetime import date
from decimal import Decimal

from app.integrations.peppol import PeppolParty, build_peppol_ubl_invoice_xml

CBC = "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}"
CAC = "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}"


class _Item:
    description = "Consulting"
    quantity = Decimal("2")
    unit_price = Decimal("100.00")
    total_amount = Decimal("200.00")


class _Invoice:
    id = 1
    invoice_number = "INV-2026-0002"
    issue_date = date(2026, 1, 31)
    due_date = date(2026, 3, 2)
    notes = None
    currency_code = "EUR"
    buyer_reference = "PO-43"
    project = None
    subtotal = Decimal("200.00")
    tax_rate = Decimal("21")
    tax_amount = Decimal("42.00")
    total_amount = Decimal("242.00")
    expenses = None
    extra_goods = None

    def __init__(self, amount_paid=None):
        self.amount_paid = amount_paid
        self.items = [_Item()]


PARTY = PeppolParty(
    endpoint_id="0000000000",
    endpoint_scheme_id="0208",
    name="Seller BV",
    tax_id="BE0000000000",
    address_line="Street 1",
    country_code="BE",
)


def _totals(amount_paid):
    xml, _ = build_peppol_ubl_invoice_xml(invoice=_Invoice(amount_paid), supplier=PARTY, customer=PARTY)
    return ET.fromstring(xml.encode("utf-8")).find(CAC + "LegalMonetaryTotal")


def _amount(totals, name):
    el = totals.find(CBC + name)
    return None if el is None else Decimal(el.text)


def test_unpaid_invoice_payable_is_the_total_without_prepaid():
    totals = _totals(Decimal("0"))
    assert _amount(totals, "TaxInclusiveAmount") == Decimal("242.00")
    assert totals.find(CBC + "PrepaidAmount") is None
    assert _amount(totals, "PayableAmount") == Decimal("242.00")


def test_missing_amount_paid_is_treated_as_unpaid():
    totals = _totals(None)
    assert totals.find(CBC + "PrepaidAmount") is None
    assert _amount(totals, "PayableAmount") == Decimal("242.00")


def test_partially_paid_invoice_reports_prepaid_and_the_balance():
    totals = _totals(Decimal("50.00"))
    assert _amount(totals, "TaxInclusiveAmount") == Decimal("242.00")
    assert _amount(totals, "PrepaidAmount") == Decimal("50.00")
    assert _amount(totals, "PayableAmount") == Decimal("192.00")


def test_prepaid_amount_precedes_payable_amount():
    """UBL 2.1 sequence: ... TaxInclusiveAmount, ..., PrepaidAmount, PayableRoundingAmount, PayableAmount."""
    tags = [child.tag for child in _totals(Decimal("50.00"))]
    assert tags.index(CBC + "TaxInclusiveAmount") < tags.index(CBC + "PrepaidAmount")
    assert tags.index(CBC + "PrepaidAmount") < tags.index(CBC + "PayableAmount")


def test_fully_paid_invoice_has_nothing_payable():
    totals = _totals(Decimal("242.00"))
    assert _amount(totals, "PrepaidAmount") == Decimal("242.00")
    assert _amount(totals, "PayableAmount") == Decimal("0.00")


def test_overpaid_invoice_has_nothing_payable_and_stays_balanced():
    """Prepaid is capped at the total so PayableAmount is not negative; BR-CO-16 still holds."""
    totals = _totals(Decimal("300.00"))
    assert _amount(totals, "PrepaidAmount") == Decimal("242.00")
    assert _amount(totals, "PayableAmount") == Decimal("0.00")
    assert _amount(totals, "TaxInclusiveAmount") - _amount(totals, "PrepaidAmount") == _amount(totals, "PayableAmount")
