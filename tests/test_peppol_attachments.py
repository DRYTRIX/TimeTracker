"""Peppol BIS Billing 3.0 attachment rules (BG-24 / BT-125).

The invoice PDF is embedded in the UBL itself, so these assertions guard the rules an
access point validates asynchronously — a wrong element order or a missing mandatory
attribute is accepted at POST time and only fails later, out of band.
"""
import base64
import xml.etree.ElementTree as ET
from datetime import date
from decimal import Decimal

from app.integrations.peppol import (
    PeppolAttachment,
    PeppolParty,
    build_peppol_ubl_invoice_xml,
)

CBC = "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}"
CAC = "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}"

# EN 16931 mime code list — the values allowed on BT-125.
ALLOWED_MIME_CODES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "text/csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.oasis.opendocument.spreadsheet",
}

FAKE_PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


class _Item:
    description = "Consulting"
    quantity = Decimal("1")
    unit_price = Decimal("100.00")
    total_amount = Decimal("100.00")


class _Invoice:
    id = 1
    invoice_number = "INV-2026-0001"
    issue_date = date(2026, 1, 31)
    due_date = date(2026, 3, 2)
    notes = None
    currency_code = "EUR"
    buyer_reference = "PO-42"
    project = None
    subtotal = Decimal("100.00")
    tax_rate = Decimal("21")
    tax_amount = Decimal("21.00")
    total_amount = Decimal("121.00")
    items = [_Item()]
    expenses = None
    extra_goods = None


SUPPLIER = PeppolParty(
    endpoint_id="0000000000", endpoint_scheme_id="0208", name="Seller BV",
    tax_id="BE0000000000", address_line="Street 1", country_code="BE",
)
CUSTOMER = PeppolParty(
    endpoint_id="1111111111", endpoint_scheme_id="0208", name="Buyer BV",
    tax_id="BE1111111111", address_line="Street 2", country_code="BE",
)

PDF = PeppolAttachment(
    document_id="INV-2026-0001", filename="INV-2026-0001.pdf",
    mime_code="application/pdf", content=FAKE_PDF,
    description="Commercial invoice (PDF)",
)


def _build(attachments=None):
    xml, _ = build_peppol_ubl_invoice_xml(
        invoice=_Invoice(), supplier=SUPPLIER, customer=CUSTOMER, attachments=attachments
    )
    return ET.fromstring(xml.encode("utf-8"))


def _adrs(root):
    return root.findall(CAC + "AdditionalDocumentReference")


def _binary(adr):
    return adr.find(CAC + "Attachment/" + CBC + "EmbeddedDocumentBinaryObject")


def test_attachment_precedes_the_supplier_party():
    """UBL 2.1 is a sequence: AdditionalDocumentReference comes before the parties."""
    tags = [c.tag for c in _build([PDF])]
    assert CAC + "AdditionalDocumentReference" in tags
    assert tags.index(CAC + "AdditionalDocumentReference") < tags.index(
        CAC + "AccountingSupplierParty"
    )


def test_pdf_round_trips():
    binary = _binary(_adrs(_build([PDF]))[0])
    assert base64.b64decode(binary.text) == FAKE_PDF


def test_mandatory_attributes_present_and_on_the_code_list():
    binary = _binary(_adrs(_build([PDF]))[0])
    assert binary.get("filename") == "INV-2026-0001.pdf"
    assert binary.get("mimeCode") in ALLOWED_MIME_CODES


def test_document_reference_id_present():
    """BR-52: each additional supporting document shall contain a document reference."""
    adr = _adrs(_build([PDF]))[0]
    assert (adr.find(CBC + "ID").text or "").strip() == "INV-2026-0001"


def test_no_document_type_code_emitted():
    """DocumentTypeCode 130 marks an invoiced object identifier (BT-18), which has no
    association to BG-24 and must not carry an attachment — so none is emitted."""
    adr = _adrs(_build([PDF]))[0]
    assert adr.find(CBC + "DocumentTypeCode") is None


def test_duplicate_filenames_are_not_emitted_twice():
    """DE-R-022: attachment filenames are unique, case-insensitively."""
    dupe = PeppolAttachment(
        document_id="X", filename="inv-2026-0001.PDF", mime_code="application/pdf",
        content=FAKE_PDF,
    )
    names = [_binary(a).get("filename", "").lower() for a in _adrs(_build([PDF, dupe]))]
    assert len(names) == len(set(names))


def test_no_attachments_emits_no_element():
    for arg in (None, []):
        assert not _adrs(_build(arg))


def test_empty_or_unnamed_attachments_are_skipped():
    empty = PeppolAttachment(document_id="X", filename="a.pdf",
                             mime_code="application/pdf", content=b"")
    unnamed = PeppolAttachment(document_id="X", filename="  ",
                               mime_code="application/pdf", content=FAKE_PDF)
    assert not _adrs(_build([empty]))
    assert not _adrs(_build([unnamed]))
