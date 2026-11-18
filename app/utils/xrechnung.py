"""
XRechnung 3.0 (CIUS-DE) UBL export helpers.

Builds on PEPPOL BIS3 UBL generation and adjusts CustomizationID, mandatory fields,
payment means, and seller contact for German public-sector e-invoicing.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from types import SimpleNamespace
from typing import Any, List, Optional, Tuple

from app.integrations.peppol import PeppolParty, build_peppol_ubl_invoice_xml

XRECHNUNG_30_CUSTOMIZATION_ID = "urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0"
LEITWEG_SCHEME_ID = "0204"
DE_VAT_SCHEME_ID = "9930"

_NS_INVOICE = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
_NS_CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
_NS_CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"

CAC = f"{{{_NS_CAC}}}"
CBC = f"{{{_NS_CBC}}}"


def xrechnung_export_available() -> bool:
    return True


def _strip(v: Any) -> str:
    return (v or "").strip() if v is not None else ""


def effective_buyer_reference(invoice: Any, client: Any) -> str:
    """BT-10: invoice buyer_reference, else client Leitweg-ID."""
    br = _strip(getattr(invoice, "buyer_reference", None))
    if br:
        return br
    if client is not None:
        return _strip(getattr(client, "leitweg_id", None))
    return ""


def validate_xrechnung_ready(invoice: Any, settings: Any, client: Any) -> List[str]:
    """Return human-readable messages for missing mandatory XRechnung fields."""
    issues: List[str] = []

    if not _strip(getattr(settings, "company_name", None)):
        issues.append("Settings: company name is required (seller).")
    if not (_strip(getattr(settings, "company_street", None)) or _strip(getattr(settings, "company_address", None))):
        issues.append("Settings: company street or address is required.")
    if not _strip(getattr(settings, "company_postcode", None)):
        issues.append("Settings: company postcode is required.")
    if not _strip(getattr(settings, "company_city", None)):
        issues.append("Settings: company city is required.")
    if not _strip(getattr(settings, "company_country", None)):
        issues.append("Settings: company country (ISO 2) is required.")
    if not _strip(getattr(settings, "company_tax_id", None)):
        issues.append("Settings: company VAT ID is required.")
    if not _strip(getattr(settings, "company_phone", None)):
        issues.append("Settings: company phone is required (seller contact BG-6).")
    if not _strip(getattr(settings, "company_email", None)):
        issues.append("Settings: company email is required (seller contact BG-6).")
    if not _strip(getattr(settings, "company_iban", None)):
        issues.append("Settings: company IBAN is required (payment means BG-16).")

    if client is None:
        issues.append("Invoice must be linked to a client.")
    else:
        if not _strip(getattr(client, "name", None)):
            issues.append("Client: name is required.")
        if not (_strip(getattr(client, "street", None)) or _strip(getattr(client, "address", None))):
            issues.append("Client: street or address is required.")
        if not _strip(getattr(client, "postcode", None)):
            issues.append("Client: postcode is required.")
        if not _strip(getattr(client, "city", None)):
            issues.append("Client: city is required.")
        if not _strip(getattr(client, "country", None)):
            issues.append("Client: country (ISO 2) is required.")
        vat = _strip(getattr(client, "vat_id", None))
        if not vat and client is not None and hasattr(client, "get_custom_field"):
            vat = _strip(client.get_custom_field("vat_id", "") or client.get_custom_field("tax_id", ""))
        if not vat:
            issues.append("Client: VAT ID is required.")

    if not effective_buyer_reference(invoice, client):
        issues.append("Buyer reference (BT-10) / client Leitweg-ID is required.")

    inv_no = _strip(getattr(invoice, "invoice_number", None))
    if not inv_no:
        issues.append("Invoice number is required.")

    return issues


def _structured_address_line(street: Optional[str], fallback: Optional[str]) -> Optional[str]:
    s = _strip(street) or _strip(fallback)
    return s or None


def build_supplier_party(settings: Any) -> PeppolParty:
    tax_id = _strip(getattr(settings, "company_tax_id", None)) or None
    endpoint_id = _strip(getattr(settings, "peppol_sender_endpoint_id", None))
    scheme_id = _strip(getattr(settings, "peppol_sender_scheme_id", None))
    if not endpoint_id and tax_id:
        endpoint_id = tax_id.replace(" ", "")
        scheme_id = DE_VAT_SCHEME_ID
    if not endpoint_id:
        endpoint_id = tax_id or "SELLER"
        scheme_id = scheme_id or DE_VAT_SCHEME_ID

    country = (
        _strip(getattr(settings, "company_country", None))
        or _strip(getattr(settings, "peppol_sender_country", None))
        or None
    )

    return PeppolParty(
        endpoint_id=endpoint_id,
        endpoint_scheme_id=scheme_id or DE_VAT_SCHEME_ID,
        name=_strip(getattr(settings, "company_name", None)) or "Company",
        tax_id=tax_id,
        address_line=_structured_address_line(
            getattr(settings, "company_street", None), getattr(settings, "company_address", None)
        ),
        country_code=country,
        email=_strip(getattr(settings, "company_email", None)) or None,
        phone=_strip(getattr(settings, "company_phone", None)) or None,
    )


def build_customer_party(invoice: Any, client: Any, leitweg_id: str) -> PeppolParty:
    vat = _strip(getattr(client, "vat_id", None))
    if not vat and hasattr(client, "get_custom_field"):
        vat = _strip(client.get_custom_field("vat_id", "") or client.get_custom_field("tax_id", "")) or None

    return PeppolParty(
        endpoint_id=leitweg_id,
        endpoint_scheme_id=LEITWEG_SCHEME_ID,
        name=_strip(getattr(client, "name", None) or getattr(invoice, "client_name", None)) or "Customer",
        tax_id=vat,
        address_line=_structured_address_line(getattr(client, "street", None), getattr(client, "address", None)),
        country_code=_strip(getattr(client, "country", None)) or None,
        email=_strip(getattr(client, "email", None) or getattr(invoice, "client_email", None)) or None,
        phone=_strip(getattr(client, "phone", None)) or None,
    )


def _invoice_with_buyer_reference(invoice: Any, buyer_reference: str) -> Any:
    """Shallow invoice view with buyer_reference set for UBL generation."""
    if _strip(getattr(invoice, "buyer_reference", None)) == buyer_reference:
        return invoice
    patched = SimpleNamespace()
    for key in (
        "id",
        "invoice_number",
        "issue_date",
        "due_date",
        "currency_code",
        "subtotal",
        "tax_rate",
        "tax_amount",
        "total_amount",
        "notes",
        "items",
        "expenses",
        "extra_goods",
        "project",
    ):
        if hasattr(invoice, key):
            setattr(patched, key, getattr(invoice, key))
    patched.buyer_reference = buyer_reference
    return patched


def _set_text(parent: ET.Element, tag: str, text: str) -> ET.Element:
    el = ET.SubElement(parent, tag)
    el.text = text
    return el


def _ensure_structured_address(party_el: ET.Element, street: str, city: str, postcode: str, country: str) -> None:
    addr = party_el.find(f"{CAC}PostalAddress")
    if addr is None:
        addr = ET.SubElement(party_el, f"{CAC}PostalAddress")
    if street and addr.find(f"{CBC}StreetName") is None:
        _set_text(addr, f"{CBC}StreetName", street)
    if city and addr.find(f"{CBC}CityName") is None:
        _set_text(addr, f"{CBC}CityName", city)
    if postcode and addr.find(f"{CBC}PostalZone") is None:
        _set_text(addr, f"{CBC}PostalZone", postcode)
    if country:
        country_el = addr.find(f"{CAC}Country")
        if country_el is None:
            country_el = ET.SubElement(addr, f"{CAC}Country")
        if country_el.find(f"{CBC}IdentificationCode") is None:
            _set_text(country_el, f"{CBC}IdentificationCode", country)


def _ensure_supplier_contact(supplier_party: ET.Element, contact_name: str) -> None:
    contact = supplier_party.find(f"{CAC}Contact")
    if contact is None:
        contact = ET.SubElement(supplier_party, f"{CAC}Contact")
    name_el = contact.find(f"{CBC}Name")
    if name_el is None and contact_name:
        contact.insert(0, _set_text(contact, f"{CBC}Name", contact_name))


def _insert_payment_means(root: ET.Element, *, iban: str, bic: Optional[str], payment_id: Optional[str]) -> None:
    if root.find(f"{CAC}PaymentMeans") is not None:
        return
    pm = ET.Element(f"{CAC}PaymentMeans")
    _set_text(pm, f"{CBC}PaymentMeansCode", "30")
    if payment_id:
        _set_text(pm, f"{CBC}PaymentID", payment_id)
    account = ET.SubElement(pm, f"{CAC}PayeeFinancialAccount")
    _set_text(account, f"{CBC}ID", iban.replace(" ", ""))
    if bic:
        branch = ET.SubElement(account, f"{CAC}FinancialInstitutionBranch")
        fin = ET.SubElement(branch, f"{CAC}FinancialInstitution")
        _set_text(fin, f"{CBC}ID", bic.replace(" ", ""))

    insert_at = 0
    children = list(root)
    for i, child in enumerate(children):
        if child.tag == f"{CAC}AccountingCustomerParty":
            insert_at = i + 1
            break
    root.insert(insert_at, pm)


def _insert_payment_terms(root: ET.Element, invoice: Any, settings: Any) -> None:
    if root.find(f"{CAC}PaymentTerms") is not None:
        return
    note = _strip(getattr(invoice, "payment_terms", None))
    if not note:
        note = _strip(getattr(settings, "invoice_terms", None))
    due = getattr(invoice, "due_date", None)
    if not note and not due:
        return
    pt = ET.Element(f"{CAC}PaymentTerms")
    if note:
        _set_text(pt, f"{CBC}Note", note)
    insert_at = len(list(root))
    for i, child in enumerate(list(root)):
        if child.tag == f"{CAC}PaymentMeans":
            insert_at = i + 1
            break
        if child.tag == f"{CAC}AccountingCustomerParty":
            insert_at = i + 1
    root.insert(insert_at, pt)


def _patch_xrechnung_ubl(
    xml: str,
    *,
    invoice: Any,
    settings: Any,
    client: Any,
    buyer_reference: str,
) -> str:
    root = ET.fromstring(xml.encode("utf-8"))

    cust = root.find(f"{CBC}CustomizationID")
    if cust is not None:
        cust.text = XRECHNUNG_30_CUSTOMIZATION_ID

    buyer_ref = root.find(f"{CBC}BuyerReference")
    if buyer_ref is None:
        buyer_ref = ET.SubElement(root, f"{CBC}BuyerReference")
    buyer_ref.text = buyer_reference

    supplier_root = root.find(f"{CAC}AccountingSupplierParty")
    if supplier_root is not None:
        supplier_party = supplier_root.find(f"{CAC}Party")
        if supplier_party is not None:
            _ensure_structured_address(
                supplier_party,
                _strip(getattr(settings, "company_street", None)),
                _strip(getattr(settings, "company_city", None)),
                _strip(getattr(settings, "company_postcode", None)),
                _strip(getattr(settings, "company_country", None)),
            )
            _ensure_supplier_contact(supplier_party, _strip(getattr(settings, "company_name", None)))

    customer_root = root.find(f"{CAC}AccountingCustomerParty")
    if customer_root is not None and client is not None:
        customer_party = customer_root.find(f"{CAC}Party")
        if customer_party is not None:
            _ensure_structured_address(
                customer_party,
                _strip(getattr(client, "street", None)) or _strip(getattr(client, "address", None)),
                _strip(getattr(client, "city", None)),
                _strip(getattr(client, "postcode", None)),
                _strip(getattr(client, "country", None)),
            )

    iban = _strip(getattr(settings, "company_iban", None))
    bic = _strip(getattr(settings, "company_bic", None)) or None
    if iban:
        _insert_payment_means(
            root,
            iban=iban,
            bic=bic,
            payment_id=_strip(getattr(invoice, "invoice_number", None)) or None,
        )

    _insert_payment_terms(root, invoice, settings)

    return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")


def build_xrechnung_ubl_invoice_xml(
    invoice: Any,
    settings: Any,
    client: Any,
) -> Tuple[str, str]:
    """
    Build XRechnung 3.0 UBL XML and return (xml_string, sha256_hex).
    Call validate_xrechnung_ready first in routes.
    """
    buyer_reference = effective_buyer_reference(invoice, client)
    supplier = build_supplier_party(settings)
    customer = build_customer_party(invoice, client, buyer_reference)
    inv = _invoice_with_buyer_reference(invoice, buyer_reference)

    xml, sha = build_peppol_ubl_invoice_xml(invoice=inv, supplier=supplier, customer=customer, attachments=None)
    xml = _patch_xrechnung_ubl(xml, invoice=invoice, settings=settings, client=client, buyer_reference=buyer_reference)
    import hashlib

    sha256_hex = hashlib.sha256(xml.encode("utf-8")).hexdigest()
    return xml, sha256_hex


# Backwards compatibility for smoke tests / docs
def build_minimal_xrechnung_xml(invoice: Any, *, seller_name: str, buyer_name: str, currency: str = "EUR") -> str:
    settings = SimpleNamespace(
        company_name=seller_name,
        company_street="Street 1",
        company_postcode="10115",
        company_city="Berlin",
        company_country="DE",
        company_tax_id="DE123456789",
        company_phone="+49 30 123456",
        company_email="seller@example.com",
        company_iban="DE89370400440532013000",
        company_bic="COBADEFFXXX",
        company_address="Street 1",
        peppol_sender_endpoint_id="",
        peppol_sender_scheme_id="",
        peppol_sender_country="DE",
        invoice_terms="Payable within 30 days.",
    )
    client = SimpleNamespace(
        name=buyer_name,
        street="Buyer St 2",
        postcode="80331",
        city="Munich",
        country="DE",
        vat_id="DE987654321",
        address="Buyer St 2",
        email="buyer@example.com",
        phone="+49 89 123456",
        leitweg_id="993-470090002-90",
    )
    inv = SimpleNamespace(
        invoice_number=getattr(invoice, "invoice_number", None) or getattr(invoice, "id", "1"),
        issue_date=getattr(invoice, "issue_date", None),
        due_date=getattr(invoice, "due_date", None),
        currency_code=currency,
        subtotal=getattr(invoice, "subtotal", getattr(invoice, "total_amount", 0)),
        tax_rate=getattr(invoice, "tax_rate", 0),
        tax_amount=getattr(invoice, "tax_amount", 0),
        total_amount=getattr(invoice, "total_amount", getattr(invoice, "total", 0)),
        buyer_reference=effective_buyer_reference(invoice, client),
        notes=getattr(invoice, "notes", None),
        items=getattr(invoice, "items", []) or [],
        expenses=[],
        extra_goods=[],
        client_name=buyer_name,
    )
    xml, _ = build_xrechnung_ubl_invoice_xml(inv, settings, client)
    return xml


def build_xrechnung_ubl_credit_note_xml(credit_note, invoice, settings, client) -> Tuple[str, str]:
    """Build XRechnung-flavoured UBL CreditNote (type 381) from Peppol credit note XML."""
    import hashlib

    from app.integrations.peppol import build_peppol_ubl_credit_note_xml

    buyer_reference = effective_buyer_reference(invoice, client)
    supplier = build_supplier_party(settings)
    customer = build_customer_party(invoice, client, buyer_reference)
    xml, _doc_id = build_peppol_ubl_credit_note_xml(credit_note, invoice, supplier, customer)
    # Patch CustomizationID to XRechnung 3.0
    try:
        root = ET.fromstring(xml.encode("utf-8"))
        for el in root.iter():
            if el.tag.endswith("CustomizationID"):
                el.text = XRECHNUNG_30_CUSTOMIZATION_ID
                break
        xml = ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")
    except Exception:
        pass
    return xml, hashlib.sha256(xml.encode("utf-8")).hexdigest()
