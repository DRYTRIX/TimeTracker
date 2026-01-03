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

import hashlib
import os
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

import requests
import xml.etree.ElementTree as ET


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

    p_name = ET.SubElement(party_el, cac + "PartyName")
    _text(p_name, cbc + "Name", party.name)

    if party.tax_id:
        tax_scheme = ET.SubElement(party_el, cac + "PartyTaxScheme")
        _text(tax_scheme, cbc + "CompanyID", party.tax_id)
        ts = ET.SubElement(tax_scheme, cac + "TaxScheme")
        _text(ts, cbc + "ID", "VAT")

    if party.address_line or party.country_code:
        addr = ET.SubElement(party_el, cac + "PostalAddress")
        if party.address_line:
            al = ET.SubElement(addr, cac + "AddressLine")
            _text(al, cbc + "Line", party.address_line)
        if party.country_code:
            country = ET.SubElement(addr, cac + "Country")
            _text(country, cbc + "IdentificationCode", party.country_code)

    if party.email:
        contact = ET.SubElement(party_el, cac + "Contact")
        _text(contact, cbc + "ElectronicMail", party.email)
        if party.phone:
            _text(contact, cbc + "Telephone", party.phone)


def build_peppol_ubl_invoice_xml(invoice: Any, supplier: PeppolParty, customer: PeppolParty) -> Tuple[str, str]:
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

    _text(inv_el, cbc + "CustomizationID", PEPPOL_BIS3_CUSTOMIZATION_ID)
    _text(inv_el, cbc + "ProfileID", PEPPOL_BIS3_PROFILE_ID)
    _text(inv_el, cbc + "ID", getattr(invoice, "invoice_number", None) or str(getattr(invoice, "id", "")))

    issue_date = getattr(invoice, "issue_date", None) or date.today()
    if hasattr(issue_date, "isoformat"):
        _text(inv_el, cbc + "IssueDate", issue_date.isoformat())
    due_date = getattr(invoice, "due_date", None)
    if due_date and hasattr(due_date, "isoformat"):
        _text(inv_el, cbc + "DueDate", due_date.isoformat())

    currency = getattr(invoice, "currency_code", None) or "EUR"
    _text(inv_el, cbc + "DocumentCurrencyCode", currency)

    notes = getattr(invoice, "notes", None)
    if notes:
        _text(inv_el, cbc + "Note", notes)

    # Parties
    _party(inv_el, "AccountingSupplierParty", supplier)
    _party(inv_el, "AccountingCustomerParty", customer)

    # Tax total (best-effort based on current Invoice model fields)
    tax_total = ET.SubElement(inv_el, cac + "TaxTotal")
    tax_amount_el = ET.SubElement(tax_total, cbc + "TaxAmount")
    tax_amount_el.set("currencyID", currency)
    tax_amount_el.text = _money(getattr(invoice, "tax_amount", 0))

    tax_rate = Decimal(str(getattr(invoice, "tax_rate", 0) or 0))
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
    payable = ET.SubElement(legal_total, cbc + "PayableAmount")
    payable.set("currencyID", currency)
    payable.text = _money(getattr(invoice, "total_amount", 0))

    # Invoice lines (items + expenses + extra goods)
    line_id = 1

    def _add_line(description: str, quantity: Any, unit_price: Any, line_total: Any) -> None:
        nonlocal line_id
        il = ET.SubElement(inv_el, cac + "InvoiceLine")
        _text(il, cbc + "ID", str(line_id))
        qty_el = ET.SubElement(il, cbc + "InvoicedQuantity")
        qty_el.text = _qty(quantity)
        lea = ET.SubElement(il, cbc + "LineExtensionAmount")
        lea.set("currencyID", currency)
        lea.text = _money(line_total)

        item_el = ET.SubElement(il, cac + "Item")
        _text(item_el, cbc + "Name", description[:200])

        price_el = ET.SubElement(il, cac + "Price")
        pa = ET.SubElement(price_el, cbc + "PriceAmount")
        pa.set("currencyID", currency)
        pa.text = _money(unit_price)

        line_id += 1

    # Invoice items
    try:
        for it in list(getattr(invoice, "items", []) or []):
            _add_line(
                description=getattr(it, "description", "Item"),
                quantity=getattr(it, "quantity", 1),
                unit_price=getattr(it, "unit_price", 0),
                line_total=getattr(it, "total_amount", 0),
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
            _add_line(description=desc, quantity=1, unit_price=getattr(ex, "total_amount", 0), line_total=getattr(ex, "total_amount", 0))
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

    token = (access_point_token if access_point_token is not None else os.getenv("PEPPOL_ACCESS_POINT_TOKEN") or "").strip()
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

