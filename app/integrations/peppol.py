"""
Peppol e-invoicing integration (BIS Billing 3.0 / UBL Invoice 2.1).

This module provides:
- UBL XML generation for an Invoice in a Peppol-friendly shape
- A provider-agnostic "access point" sender (HTTP JSON) driven by environment variables

Important:
- Real Peppol delivery requires an access point (AP). This project ships with a generic
  HTTP adapter so you can plug in your AP provider without changing business logic.
- Validation against EN16931/Peppol schematrons is provider-specific and is not performed
  in-app here.
"""

from __future__ import annotations

import base64
import hashlib
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Dict, Optional, Sequence, Tuple

import requests

PEPPOL_BIS3_CUSTOMIZATION_ID = "urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0"
PEPPOL_BIS3_PROFILE_ID = "urn:fdc:peppol.eu:2017:poacc:billing:01:1.0"


def _bool_env(name: str, default: bool = False) -> bool:
    val = (os.getenv(name, "true" if default else "false") or "").strip().lower()
    return val in {"1", "true", "yes", "y", "on"}


def peppol_enabled() -> bool:
    """
    Return whether Peppol sending is enabled.

    Priority:
    1) Database Settings.peppol_enabled when explicitly set (True/False)
    2) Environment variable PEPPOL_ENABLED otherwise
    """
    try:
        # Local import to avoid hard dependency / circular imports during bootstrap.
        from app.models import Settings

        settings = Settings.get_settings()
        if settings is not None and hasattr(settings, "peppol_enabled"):
            if settings.peppol_enabled is True:
                return True
            if settings.peppol_enabled is False:
                return False
    except Exception:
        pass
    return _bool_env("PEPPOL_ENABLED", default=False)


@dataclass(frozen=True)
class PeppolParty:
    """Minimal party info needed to create a usable UBL invoice and route it over Peppol."""

    endpoint_id: str
    endpoint_scheme_id: str
    name: str
    tax_id: Optional[str] = None
    address_line: Optional[str] = None
    country_code: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


@dataclass(frozen=True)
class PeppolAttachment:
    """A supporting document to embed in the invoice (BG-24 / BT-125).

    Typically the human-readable PDF of the invoice, so the recipient gets both the
    structured data and something a person can read.

    - ``document_id`` is BT-122, required by BR-52.
    - ``filename`` must be unique case-insensitively across attachments (DE-R-022).
    - ``mime_code`` must be on the EN 16931 mime code list (e.g. ``application/pdf``).
    """

    document_id: str
    filename: str
    mime_code: str
    content: bytes
    description: Optional[str] = None


def _money(v: Any) -> str:
    """Format money/decimals with 2 decimals, using dot as decimal separator."""
    try:
        d = v if isinstance(v, Decimal) else Decimal(str(v))
    except Exception:
        d = Decimal("0")
    return f"{d.quantize(Decimal('0.01'))}"


def _qty(v: Any) -> str:
    try:
        d = v if isinstance(v, Decimal) else Decimal(str(v))
    except Exception:
        d = Decimal("0")
    return f"{d.quantize(Decimal('0.01'))}"


def _text(parent: ET.Element, tag: str, text: Optional[str]) -> Optional[ET.Element]:
    if text is None:
        return None
    t = str(text).strip()
    if not t:
        return None
    el = ET.SubElement(parent, tag)
    el.text = t
    return el


def _party(parent: ET.Element, kind: str, party: PeppolParty) -> None:
    """
    Create a minimal party structure. `kind` is either 'AccountingSupplierParty' or 'AccountingCustomerParty'.
    """
    cac = "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}"
    cbc = "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}"

    p_root = ET.SubElement(parent, cac + kind)
    party_el = ET.SubElement(p_root, cac + "Party")

    ep = ET.SubElement(party_el, cbc + "EndpointID")
    ep.set("schemeID", party.endpoint_scheme_id)
    ep.text = party.endpoint_id

    # UBL 2.1 Party child order is fixed by the XSD sequence:
    # EndpointID, PartyName, PostalAddress, PartyTaxScheme, PartyLegalEntity, Contact.
    p_name = ET.SubElement(party_el, cac + "PartyName")
    _text(p_name, cbc + "Name", party.name)

    if party.address_line or party.country_code:
        addr = ET.SubElement(party_el, cac + "PostalAddress")
        if party.address_line:
            al = ET.SubElement(addr, cac + "AddressLine")
            _text(al, cbc + "Line", party.address_line)
        if party.country_code:
            country = ET.SubElement(addr, cac + "Country")
            _text(country, cbc + "IdentificationCode", party.country_code)

    if party.tax_id:
        tax_scheme = ET.SubElement(party_el, cac + "PartyTaxScheme")
        _text(tax_scheme, cbc + "CompanyID", party.tax_id)
        ts = ET.SubElement(tax_scheme, cac + "TaxScheme")
        _text(ts, cbc + "ID", "VAT")

    # PartyLegalEntity/RegistrationName carries BT-27/BT-44 (seller/buyer name) —
    # mandatory (BR-06/BR-07); CompanyID (BT-30, ISO 6523 scheme) also satisfies
    # BR-CO-26 for the seller even when no VAT id is configured.
    legal = ET.SubElement(party_el, cac + "PartyLegalEntity")
    _text(legal, cbc + "RegistrationName", party.name)
    scheme = (party.endpoint_scheme_id or "").strip()
    if scheme.isdigit() and len(scheme) == 4 and (party.endpoint_id or "").strip():
        company_id = ET.SubElement(legal, cbc + "CompanyID")
        company_id.set("schemeID", scheme)
        company_id.text = party.endpoint_id.strip()

    if party.email or party.phone:
        contact = ET.SubElement(party_el, cac + "Contact")
        # Contact child order per XSD: Name, Telephone, ElectronicMail.
        if party.phone:
            _text(contact, cbc + "Telephone", party.phone)
        _text(contact, cbc + "ElectronicMail", party.email)


def build_peppol_ubl_invoice_xml(
    invoice: Any,
    supplier: PeppolParty,
    customer: PeppolParty,
    attachments: Optional[Sequence[PeppolAttachment]] = None,
) -> Tuple[str, str]:
    """
    Build UBL 2.1 Invoice XML shaped for Peppol BIS Billing 3.0.

    Returns:
        (xml_string_utf8, sha256_hex)
    """
    # Namespaces
    ns_invoice = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
    ns_cac = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
    ns_cbc = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"

    ET.register_namespace("", ns_invoice)
    ET.register_namespace("cac", ns_cac)
    ET.register_namespace("cbc", ns_cbc)

    inv_el = ET.Element(f"{{{ns_invoice}}}Invoice")

    cbc = f"{{{ns_cbc}}}"
    cac = f"{{{ns_cac}}}"

    # The cbc header order is fixed by the UBL 2.1 XSD sequence:
    # CustomizationID, ProfileID, ID, IssueDate, DueDate, InvoiceTypeCode, Note,
    # DocumentCurrencyCode, BuyerReference — any other order fails XSD validation
    # at the access point (cvc-complex-type.2.4.a).
    _text(inv_el, cbc + "CustomizationID", PEPPOL_BIS3_CUSTOMIZATION_ID)
    _text(inv_el, cbc + "ProfileID", PEPPOL_BIS3_PROFILE_ID)
    _text(inv_el, cbc + "ID", getattr(invoice, "invoice_number", None) or str(getattr(invoice, "id", "")))

    issue_date = getattr(invoice, "issue_date", None) or date.today()
    if hasattr(issue_date, "isoformat"):
        _text(inv_el, cbc + "IssueDate", issue_date.isoformat())
    due_date = getattr(invoice, "due_date", None)
    if due_date and hasattr(due_date, "isoformat"):
        _text(inv_el, cbc + "DueDate", due_date.isoformat())

    _text(inv_el, cbc + "InvoiceTypeCode", "380")  # 380 = commercial invoice (PEPPOL BT-3)

    notes = getattr(invoice, "notes", None)
    if notes:
        _text(inv_el, cbc + "Note", notes)

    currency = getattr(invoice, "currency_code", None) or "EUR"
    _text(inv_el, cbc + "DocumentCurrencyCode", currency)

    # BuyerReference (BT-10): required by PEPPOL; use buyer_reference, project name, or invoice number
    _buyer_ref = (
        (getattr(invoice, "buyer_reference", None) or "").strip()
        or (getattr(getattr(invoice, "project", None), "name", None) or "").strip()
        or (getattr(invoice, "invoice_number", None) or "").strip()
        or str(getattr(invoice, "id", ""))
    )
    if _buyer_ref:
        _text(inv_el, cbc + "BuyerReference", _buyer_ref)

    # Parties
    # AdditionalDocumentReference (BG-24): supporting documents embedded in the invoice,
    # e.g. the human-readable PDF of this invoice. The UBL 2.1 XSD sequence puts this after
    # the document references and BEFORE Signature/AccountingSupplierParty; emitting it any
    # later is XSD-invalid, and the access point only reports that asynchronously.
    # Deliberately no cbc:DocumentTypeCode: code 130 marks an invoiced object identifier
    # (BT-18), which has no association to BG-24 and must not carry an attachment.
    _seen_filenames = set()
    for att in attachments or []:
        filename = (getattr(att, "filename", "") or "").strip()
        if not att.content or not filename or filename.lower() in _seen_filenames:
            continue  # DE-R-022: attachment filenames must be unique (case-insensitive)
        _seen_filenames.add(filename.lower())
        adr = ET.SubElement(inv_el, cac + "AdditionalDocumentReference")
        _text(adr, cbc + "ID", att.document_id or filename)  # BT-122, required by BR-52
        _text(adr, cbc + "DocumentDescription", att.description)
        attachment_el = ET.SubElement(adr, cac + "Attachment")
        binary_el = ET.SubElement(attachment_el, cbc + "EmbeddedDocumentBinaryObject")
        binary_el.set("mimeCode", att.mime_code or "application/pdf")
        binary_el.set("filename", filename)
        binary_el.text = base64.b64encode(att.content).decode("ascii")

    _party(inv_el, "AccountingSupplierParty", supplier)
    _party(inv_el, "AccountingCustomerParty", customer)

    # Tax total — use tax_breakdown() for multi-rate support, fall back to flat rate
    tax_total = ET.SubElement(inv_el, cac + "TaxTotal")
    tax_amount_el = ET.SubElement(tax_total, cbc + "TaxAmount")
    tax_amount_el.set("currencyID", currency)
    tax_amount_el.text = _money(getattr(invoice, "tax_amount", 0))

    tax_rate = Decimal(str(getattr(invoice, "tax_rate", 0) or 0))
    try:
        breakdown = invoice.tax_breakdown() if hasattr(invoice, "tax_breakdown") else []
    except Exception:
        breakdown = []

    if breakdown:
        for grp in breakdown:
            tax_sub = ET.SubElement(tax_total, cac + "TaxSubtotal")
            taxable_amount_el = ET.SubElement(tax_sub, cbc + "TaxableAmount")
            taxable_amount_el.set("currencyID", currency)
            taxable_amount_el.text = _money(grp["taxable"])
            tax_sub_amount_el = ET.SubElement(tax_sub, cbc + "TaxAmount")
            tax_sub_amount_el.set("currencyID", currency)
            tax_sub_amount_el.text = _money(grp["tax"])
            tax_cat = ET.SubElement(tax_sub, cac + "TaxCategory")
            grp_rate = Decimal(str(grp.get("rate", 0)))
            grp_cat = grp.get("category") or ("S" if grp_rate > 0 else "Z")
            _text(tax_cat, cbc + "ID", grp_cat)
            _text(tax_cat, cbc + "Percent", _money(grp_rate))
            tax_scheme = ET.SubElement(tax_cat, cac + "TaxScheme")
            _text(tax_scheme, cbc + "ID", "VAT")
    else:
        # Fallback: single subtotal
        tax_sub = ET.SubElement(tax_total, cac + "TaxSubtotal")
        taxable_amount_el = ET.SubElement(tax_sub, cbc + "TaxableAmount")
        taxable_amount_el.set("currencyID", currency)
        taxable_amount_el.text = _money(getattr(invoice, "subtotal", 0))
        tax_sub_amount_el = ET.SubElement(tax_sub, cbc + "TaxAmount")
        tax_sub_amount_el.set("currencyID", currency)
        tax_sub_amount_el.text = _money(getattr(invoice, "tax_amount", 0))
        tax_cat = ET.SubElement(tax_sub, cac + "TaxCategory")
        _text(tax_cat, cbc + "ID", "S" if tax_rate > 0 else "Z")
        _text(tax_cat, cbc + "Percent", _money(tax_rate))
        tax_scheme = ET.SubElement(tax_cat, cac + "TaxScheme")
        _text(tax_scheme, cbc + "ID", "VAT")

    # Monetary totals
    legal_total = ET.SubElement(inv_el, cac + "LegalMonetaryTotal")
    line_ext = ET.SubElement(legal_total, cbc + "LineExtensionAmount")
    line_ext.set("currencyID", currency)
    line_ext.text = _money(getattr(invoice, "subtotal", 0))
    tax_excl = ET.SubElement(legal_total, cbc + "TaxExclusiveAmount")
    tax_excl.set("currencyID", currency)
    tax_excl.text = _money(getattr(invoice, "subtotal", 0))
    tax_incl = ET.SubElement(legal_total, cbc + "TaxInclusiveAmount")
    tax_incl.set("currencyID", currency)
    tax_incl.text = _money(getattr(invoice, "total_amount", 0))
    # Payments already recorded on the invoice are the prepaid amount (BT-113) and
    # PayableAmount = TaxInclusiveAmount - PrepaidAmount (BR-CO-16).
    # As in the CII export, the amount due is never negative; here the prepaid amount is
    # capped at the total so BR-CO-16 holds, and an overpayment is not shown in full in BT-113.
    total = Decimal(str(getattr(invoice, "total_amount", 0) or 0))
    paid = Decimal(str(getattr(invoice, "amount_paid", 0) or 0))
    prepaid = min(max(paid, Decimal("0")), max(total, Decimal("0")))
    if prepaid > 0:
        prepaid_el = ET.SubElement(legal_total, cbc + "PrepaidAmount")
        prepaid_el.set("currencyID", currency)
        prepaid_el.text = _money(prepaid)
    payable = ET.SubElement(legal_total, cbc + "PayableAmount")
    payable.set("currencyID", currency)
    payable.text = _money(total - prepaid)

    # Invoice lines (items + expenses + extra goods)
    line_id = 1

    def _add_line(
        description: str,
        quantity: Any,
        unit_price: Any,
        line_total: Any,
        line_tax_rate: Optional[Decimal] = None,
        line_vat_category: Optional[str] = None,
    ) -> None:
        nonlocal line_id
        il = ET.SubElement(inv_el, cac + "InvoiceLine")
        _text(il, cbc + "ID", str(line_id))
        qty_el = ET.SubElement(il, cbc + "InvoicedQuantity")
        qty_el.set("unitCode", "C62")  # C62 = unit/each (UN/ECE Rec 21), required by EN 16931
        qty_el.text = _qty(quantity)
        lea = ET.SubElement(il, cbc + "LineExtensionAmount")
        lea.set("currencyID", currency)
        lea.text = _money(line_total)

        item_el = ET.SubElement(il, cac + "Item")
        _text(item_el, cbc + "Name", description[:200])

        # Each line needs exactly one ClassifiedTaxCategory (BT-151, BR-CO-04/UBL-SR-48)
        eff_rate = line_tax_rate if line_tax_rate is not None else tax_rate
        eff_cat = line_vat_category or ("S" if eff_rate > 0 else "Z")
        line_tax_cat = ET.SubElement(item_el, cac + "ClassifiedTaxCategory")
        _text(line_tax_cat, cbc + "ID", eff_cat)
        _text(line_tax_cat, cbc + "Percent", _money(eff_rate))
        line_tax_scheme = ET.SubElement(line_tax_cat, cac + "TaxScheme")
        _text(line_tax_scheme, cbc + "ID", "VAT")

        price_el = ET.SubElement(il, cac + "Price")
        pa = ET.SubElement(price_el, cbc + "PriceAmount")
        pa.set("currencyID", currency)
        pa.text = _money(unit_price)

        line_id += 1

    # Invoice items
    try:
        for it in list(getattr(invoice, "items", []) or []):
            _it_tax = None
            if getattr(it, "tax_rate", None) is not None:
                _it_tax = Decimal(str(it.tax_rate))
            _it_cat = getattr(it, "vat_category", None) or None
            _line_total = getattr(it, "line_net", None)
            if _line_total is None:
                _line_total = getattr(it, "total_amount", 0)
            _add_line(
                description=getattr(it, "description", "Item"),
                quantity=getattr(it, "quantity", 1),
                unit_price=getattr(it, "unit_price", 0),
                line_total=_line_total,
                line_tax_rate=_it_tax,
                line_vat_category=_it_cat,
            )
    except Exception:
        pass

    # Expenses (linked to invoice)
    try:
        expenses_rel = getattr(invoice, "expenses", None)
        expenses = list(expenses_rel) if expenses_rel is not None else []
        for ex in expenses:
            desc = getattr(ex, "title", "Expense")
            if getattr(ex, "vendor", None):
                desc = f"{desc} ({ex.vendor})"
            _add_line(
                description=desc,
                quantity=1,
                unit_price=getattr(ex, "total_amount", 0),
                line_total=getattr(ex, "total_amount", 0),
            )
    except Exception:
        pass

    # Extra goods (linked to invoice)
    try:
        goods_rel = getattr(invoice, "extra_goods", None)
        goods = list(goods_rel) if goods_rel is not None else []
        for g in goods:
            _add_line(
                description=getattr(g, "name", "Good"),
                quantity=getattr(g, "quantity", 1),
                unit_price=getattr(g, "unit_price", 0),
                line_total=getattr(g, "total_amount", 0),
            )
    except Exception:
        pass

    xml_bytes = ET.tostring(inv_el, encoding="utf-8", xml_declaration=True)
    sha256_hex = hashlib.sha256(xml_bytes).hexdigest()
    return xml_bytes.decode("utf-8"), sha256_hex


class PeppolAccessPointError(RuntimeError):
    pass


def send_ubl_via_access_point(
    *,
    ubl_xml: str,
    recipient_endpoint_id: str,
    recipient_scheme_id: str,
    sender_endpoint_id: str,
    sender_scheme_id: str,
    document_id: str,
    access_point_url: Optional[str] = None,
    access_point_token: Optional[str] = None,
    access_point_timeout_s: Optional[float] = None,
    process_id: str = PEPPOL_BIS3_PROFILE_ID,
    document_type_id: str = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0::2.1",
) -> Dict[str, Any]:
    """
    Send UBL to an access point via a generic JSON API.

    The expected API contract is:
      POST {PEPPOL_ACCESS_POINT_URL}
      Authorization: Bearer {PEPPOL_ACCESS_POINT_TOKEN}   (optional)
      JSON body:
        {
          "recipient": {"endpoint_id": "...", "scheme_id": "..."},
          "sender": {"endpoint_id": "...", "scheme_id": "..."},
          "document": {"id": "...", "type_id": "...", "process_id": "..."},
          "payload": {"ubl_xml": "<xml...>"}   // UTF-8 string
        }

    Most commercial access points have their own APIs; implement a thin adapter at your AP URL
    to accept this contract if needed.
    """
    url = (access_point_url or os.getenv("PEPPOL_ACCESS_POINT_URL") or "").strip()
    if not url:
        raise PeppolAccessPointError("PEPPOL_ACCESS_POINT_URL is not set")

    token = (
        access_point_token if access_point_token is not None else os.getenv("PEPPOL_ACCESS_POINT_TOKEN") or ""
    ).strip()
    timeout_s = (
        float(access_point_timeout_s)
        if access_point_timeout_s is not None
        else float(os.getenv("PEPPOL_ACCESS_POINT_TIMEOUT", "30") or "30")
    )

    headers: Dict[str, str] = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    body = {
        "recipient": {"endpoint_id": recipient_endpoint_id, "scheme_id": recipient_scheme_id},
        "sender": {"endpoint_id": sender_endpoint_id, "scheme_id": sender_scheme_id},
        "document": {"id": document_id, "type_id": document_type_id, "process_id": process_id},
        "payload": {"ubl_xml": ubl_xml},
    }

    resp = requests.post(url, json=body, headers=headers, timeout=timeout_s)
    content_type = (resp.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        data = resp.json()
    else:
        data = {"raw": resp.text}

    if resp.status_code >= 400:
        raise PeppolAccessPointError(f"Access point returned HTTP {resp.status_code}: {data}")

    return {"status_code": resp.status_code, "data": data}


def build_peppol_ubl_credit_note_xml(
    credit_note,
    invoice,
    supplier: PeppolParty,
    customer: PeppolParty,
) -> Tuple[str, str]:
    """Build a Peppol BIS 3 UBL CreditNote (document type 381) with BillingReference.

    Returns (xml_string, document_id).
    """
    nsmap = {
        "": "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2",
        "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    }
    # ElementTree does not support default nsmap the same way; use Clark notation.
    ubl_ns = "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2"
    cac = "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}"
    cbc = "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}"

    root = ET.Element(f"{{{ubl_ns}}}CreditNote")
    root.set("xmlns", ubl_ns)
    root.set("xmlns:cac", "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2")
    root.set("xmlns:cbc", "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2")

    _text(root, cbc + "CustomizationID", PEPPOL_BIS3_CUSTOMIZATION_ID)
    _text(root, cbc + "ProfileID", PEPPOL_BIS3_PROFILE_ID)
    doc_id = getattr(credit_note, "credit_number", None) or str(getattr(credit_note, "id", ""))
    _text(root, cbc + "ID", doc_id)

    issue_date = getattr(credit_note, "issue_date", None) or date.today()
    if hasattr(issue_date, "isoformat"):
        _text(root, cbc + "IssueDate", issue_date.isoformat())

    _text(root, cbc + "CreditNoteTypeCode", "381")

    notes = getattr(credit_note, "reason", None) or getattr(credit_note, "notes", None)
    if notes:
        _text(root, cbc + "Note", notes)

    currency = getattr(credit_note, "currency_code", None) or getattr(invoice, "currency_code", None) or "EUR"
    _text(root, cbc + "DocumentCurrencyCode", currency)

    # Billing reference to original invoice
    inv_number = getattr(invoice, "invoice_number", None) or str(getattr(invoice, "id", ""))
    billing_ref = ET.SubElement(root, cac + "BillingReference")
    inv_doc_ref = ET.SubElement(billing_ref, cac + "InvoiceDocumentReference")
    _text(inv_doc_ref, cbc + "ID", inv_number)
    inv_issue = getattr(invoice, "issue_date", None)
    if inv_issue and hasattr(inv_issue, "isoformat"):
        _text(inv_doc_ref, cbc + "IssueDate", inv_issue.isoformat())

    _party(root, "AccountingSupplierParty", supplier)
    _party(root, "AccountingCustomerParty", customer)

    tax_total = ET.SubElement(root, cac + "TaxTotal")
    tax_amount_el = ET.SubElement(tax_total, cbc + "TaxAmount")
    tax_amount_el.set("currencyID", currency)
    tax_amount_el.text = _money(getattr(credit_note, "tax_amount", 0) or 0)

    tax_rate = Decimal(str(getattr(credit_note, "tax_rate", 0) or getattr(invoice, "tax_rate", 0) or 0))
    tax_sub = ET.SubElement(tax_total, cac + "TaxSubtotal")
    taxable_amount_el = ET.SubElement(tax_sub, cbc + "TaxableAmount")
    taxable_amount_el.set("currencyID", currency)
    taxable_amount_el.text = _money(getattr(credit_note, "subtotal", 0) or 0)
    tax_sub_amount_el = ET.SubElement(tax_sub, cbc + "TaxAmount")
    tax_sub_amount_el.set("currencyID", currency)
    tax_sub_amount_el.text = _money(getattr(credit_note, "tax_amount", 0) or 0)
    tax_cat = ET.SubElement(tax_sub, cac + "TaxCategory")
    _text(tax_cat, cbc + "ID", "S" if tax_rate > 0 else "Z")
    _text(tax_cat, cbc + "Percent", _money(tax_rate))
    tax_scheme = ET.SubElement(tax_cat, cac + "TaxScheme")
    _text(tax_scheme, cbc + "ID", "VAT")

    legal_total = ET.SubElement(root, cac + "LegalMonetaryTotal")
    for tag, val in (
        ("LineExtensionAmount", getattr(credit_note, "subtotal", 0) or 0),
        ("TaxExclusiveAmount", getattr(credit_note, "subtotal", 0) or 0),
        ("TaxInclusiveAmount", getattr(credit_note, "total_amount", 0) or getattr(credit_note, "amount", 0) or 0),
        ("PayableAmount", getattr(credit_note, "total_amount", 0) or getattr(credit_note, "amount", 0) or 0),
    ):
        el = ET.SubElement(legal_total, cbc + tag)
        el.set("currencyID", currency)
        el.text = _money(val)

    items = credit_note.items.all() if hasattr(credit_note.items, "all") else list(credit_note.items or [])
    items = sorted(items, key=lambda x: getattr(x, "position", 0) or 0)
    for idx, item in enumerate(items, start=1):
        cl = ET.SubElement(root, cac + "CreditNoteLine")
        _text(cl, cbc + "ID", str(idx))
        qty_el = ET.SubElement(cl, cbc + "CreditedQuantity")
        qty_el.set("unitCode", "C62")
        qty_el.text = _qty(getattr(item, "quantity", 1))
        lea = ET.SubElement(cl, cbc + "LineExtensionAmount")
        lea.set("currencyID", currency)
        lea.text = _money(getattr(item, "total_amount", 0))
        item_el = ET.SubElement(cl, cac + "Item")
        _text(item_el, cbc + "Name", getattr(item, "description", "") or f"Line {idx}")
        line_tax_cat = ET.SubElement(item_el, cac + "ClassifiedTaxCategory")
        item_rate = Decimal(str(item.tax_rate if getattr(item, "tax_rate", None) is not None else tax_rate))
        _text(line_tax_cat, cbc + "ID", "S" if item_rate > 0 else "Z")
        _text(line_tax_cat, cbc + "Percent", _money(item_rate))
        ts = ET.SubElement(line_tax_cat, cac + "TaxScheme")
        _text(ts, cbc + "ID", "VAT")
        price = ET.SubElement(cl, cac + "Price")
        pa = ET.SubElement(price, cbc + "PriceAmount")
        pa.set("currencyID", currency)
        pa.text = _money(getattr(item, "unit_price", 0))

    if not items:
        # Amount-only credit: single synthetic line
        cl = ET.SubElement(root, cac + "CreditNoteLine")
        _text(cl, cbc + "ID", "1")
        qty_el = ET.SubElement(cl, cbc + "CreditedQuantity")
        qty_el.set("unitCode", "C62")
        qty_el.text = "1.00"
        lea = ET.SubElement(cl, cbc + "LineExtensionAmount")
        lea.set("currencyID", currency)
        amount = getattr(credit_note, "subtotal", None) or getattr(credit_note, "amount", 0) or 0
        lea.text = _money(amount)
        item_el = ET.SubElement(cl, cac + "Item")
        _text(item_el, cbc + "Name", getattr(credit_note, "reason", None) or "Credit")
        line_tax_cat = ET.SubElement(item_el, cac + "ClassifiedTaxCategory")
        _text(line_tax_cat, cbc + "ID", "S" if tax_rate > 0 else "Z")
        _text(line_tax_cat, cbc + "Percent", _money(tax_rate))
        ts = ET.SubElement(line_tax_cat, cac + "TaxScheme")
        _text(ts, cbc + "ID", "VAT")
        price = ET.SubElement(cl, cac + "Price")
        pa = ET.SubElement(price, cbc + "PriceAmount")
        pa.set("currencyID", currency)
        pa.text = _money(amount)

    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    return xml_bytes.decode("utf-8"), doc_id
