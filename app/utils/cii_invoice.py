"""
CII (Cross-Industry Invoice) generator for Factur-X / ZUGFeRD.

Generates UN/CEFACT CII XML (EN 16931 profile) suitable for embedding
in PDF/A-3 as required by Factur-X 1.0 / ZUGFeRD 2.x.

This is the correct payload format for ZUGFeRD/Factur-X hybrid invoices.
Peppol uses UBL (see app/integrations/peppol.py); this module is for
the embedded-in-PDF use case only.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Optional, Tuple

import xml.etree.ElementTree as ET


NS_RSM = "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
NS_RAM = "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
NS_UDT = "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100"
NS_QDT = "urn:un:unece:uncefact:data:standard:QualifiedDataType:100"

FACTURX_GUIDELINE_EN16931 = (
    "urn:cen.eu:en16931:2017#compliant#urn:factur-x.eu:1p0:en16931"
)


@dataclass(frozen=True)
class CIIParty:
    name: str
    tax_id: Optional[str] = None
    address_line: Optional[str] = None
    city: Optional[str] = None
    postcode: Optional[str] = None
    country_code: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    endpoint_id: Optional[str] = None
    endpoint_scheme_id: Optional[str] = None


def _money(v: Any) -> str:
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


def _date_102(d: Any) -> str:
    """Format date as YYYYMMDD (format code 102 per UN/CEFACT)."""
    if hasattr(d, "strftime"):
        return d.strftime("%Y%m%d")
    return str(d).replace("-", "")


def _sub(parent: ET.Element, tag: str) -> ET.Element:
    return ET.SubElement(parent, tag)


def _text_el(parent: ET.Element, tag: str, text: Optional[str]) -> Optional[ET.Element]:
    if text is None:
        return None
    t = str(text).strip()
    if not t:
        return None
    el = ET.SubElement(parent, tag)
    el.text = t
    return el


def _date_el(parent: ET.Element, d: Any) -> None:
    """Add a DateTimeString child with format 102."""
    udt = f"{{{NS_UDT}}}"
    dts = _sub(parent, udt + "DateTimeString")
    dts.set("format", "102")
    dts.text = _date_102(d)


def _build_party(parent: ET.Element, tag: str, party: CIIParty) -> None:
    ram = f"{{{NS_RAM}}}"
    p = _sub(parent, ram + tag)
    _text_el(p, ram + "Name", party.name)

    if party.endpoint_id and party.endpoint_scheme_id:
        org = _sub(p, ram + "SpecifiedLegalOrganization")
        org_id = _text_el(org, ram + "ID", party.endpoint_id)
        if org_id is not None:
            org_id.set("schemeID", party.endpoint_scheme_id)

    if party.address_line or party.country_code:
        addr = _sub(p, ram + "PostalTradeAddress")
        _text_el(addr, ram + "LineOne", party.address_line)
        _text_el(addr, ram + "CityName", party.city)
        _text_el(addr, ram + "PostcodeCode", party.postcode)
        _text_el(addr, ram + "CountryID", party.country_code)

    if party.email:
        uri_comm = _sub(p, ram + "URIUniversalCommunication")
        uri_id = _text_el(uri_comm, ram + "URIID", party.email)
        if uri_id is not None:
            uri_id.set("schemeID", "EM")

    if party.tax_id:
        tax_reg = _sub(p, ram + "SpecifiedTaxRegistration")
        tax_reg_id = _text_el(tax_reg, ram + "ID", party.tax_id)
        if tax_reg_id is not None:
            tax_reg_id.set("schemeID", "VA")


def build_cii_invoice_xml(
    invoice: Any,
    seller: CIIParty,
    buyer: CIIParty,
    guideline_id: str = FACTURX_GUIDELINE_EN16931,
) -> Tuple[str, str]:
    """
    Build a CII CrossIndustryInvoice XML for Factur-X / ZUGFeRD.

    Returns:
        (xml_string_utf8, sha256_hex)
    """
    ET.register_namespace("rsm", NS_RSM)
    ET.register_namespace("ram", NS_RAM)
    ET.register_namespace("udt", NS_UDT)
    ET.register_namespace("qdt", NS_QDT)

    rsm = f"{{{NS_RSM}}}"
    ram = f"{{{NS_RAM}}}"

    root = ET.Element(rsm + "CrossIndustryInvoice")

    # --- ExchangedDocumentContext ---
    ctx = _sub(root, rsm + "ExchangedDocumentContext")
    guideline = _sub(ctx, ram + "GuidelineSpecifiedDocumentContextParameter")
    _text_el(guideline, ram + "ID", guideline_id)

    # --- ExchangedDocument ---
    doc = _sub(root, rsm + "ExchangedDocument")
    _text_el(
        doc,
        ram + "ID",
        getattr(invoice, "invoice_number", None) or str(getattr(invoice, "id", "")),
    )
    _text_el(doc, ram + "TypeCode", "380")

    issue_date = getattr(invoice, "issue_date", None) or date.today()
    issue_dt = _sub(doc, ram + "IssueDateTime")
    _date_el(issue_dt, issue_date)

    notes = getattr(invoice, "notes", None)
    if notes and str(notes).strip():
        note_el = _sub(doc, ram + "IncludedNote")
        _text_el(note_el, ram + "Content", notes)

    # --- SupplyChainTradeTransaction ---
    txn = _sub(root, rsm + "SupplyChainTradeTransaction")

    currency = getattr(invoice, "currency_code", None) or "EUR"
    tax_rate = Decimal(str(getattr(invoice, "tax_rate", 0) or 0))
    tax_category = "S" if tax_rate > 0 else "Z"

    # --- Header Trade Agreement ---
    agreement = _sub(txn, ram + "ApplicableHeaderTradeAgreement")

    buyer_ref = (
        (getattr(invoice, "buyer_reference", None) or "").strip()
        or (getattr(getattr(invoice, "project", None), "name", None) or "").strip()
        or (getattr(invoice, "invoice_number", None) or "").strip()
        or str(getattr(invoice, "id", ""))
    )
    if buyer_ref:
        _text_el(agreement, ram + "BuyerReference", buyer_ref)

    _build_party(agreement, "SellerTradeParty", seller)
    _build_party(agreement, "BuyerTradeParty", buyer)

    # --- Header Trade Delivery ---
    _sub(txn, ram + "ApplicableHeaderTradeDelivery")

    # --- Header Trade Settlement ---
    settlement = _sub(txn, ram + "ApplicableHeaderTradeSettlement")
    _text_el(settlement, ram + "InvoiceCurrencyCode", currency)

    # Tax summary
    tax_el = _sub(settlement, ram + "ApplicableTradeTax")
    calc_amt = _text_el(tax_el, ram + "CalculatedAmount", _money(getattr(invoice, "tax_amount", 0)))
    _text_el(tax_el, ram + "TypeCode", "VAT")
    basis_amt = _text_el(tax_el, ram + "BasisAmount", _money(getattr(invoice, "subtotal", 0)))
    _text_el(tax_el, ram + "CategoryCode", tax_category)
    _text_el(tax_el, ram + "RateApplicablePercent", _money(tax_rate))

    # Payment terms (due date)
    due_date = getattr(invoice, "due_date", None)
    if due_date:
        terms = _sub(settlement, ram + "SpecifiedTradePaymentTerms")
        due_dt = _sub(terms, ram + "DueDateDateTime")
        _date_el(due_dt, due_date)

    # Monetary summation
    totals = _sub(settlement, ram + "SpecifiedTradeSettlementHeaderMonetarySummation")
    _text_el(totals, ram + "LineTotalAmount", _money(getattr(invoice, "subtotal", 0)))
    _text_el(totals, ram + "TaxBasisTotalAmount", _money(getattr(invoice, "subtotal", 0)))
    tax_total_el = _text_el(totals, ram + "TaxTotalAmount", _money(getattr(invoice, "tax_amount", 0)))
    if tax_total_el is not None:
        tax_total_el.set("currencyID", currency)
    _text_el(totals, ram + "GrandTotalAmount", _money(getattr(invoice, "total_amount", 0)))
    _text_el(totals, ram + "DuePayableAmount", _money(getattr(invoice, "total_amount", 0)))

    # --- Line Items ---
    line_id = 1

    def _add_line(description: str, quantity: Any, unit_price: Any, line_total: Any) -> None:
        nonlocal line_id
        li = _sub(txn, ram + "IncludedSupplyChainTradeLineItem")

        line_doc = _sub(li, ram + "AssociatedDocumentLineDocument")
        _text_el(line_doc, ram + "LineID", str(line_id))

        product = _sub(li, ram + "SpecifiedTradeProduct")
        _text_el(product, ram + "Name", str(description)[:200])

        line_agreement = _sub(li, ram + "SpecifiedLineTradeAgreement")
        net_price = _sub(line_agreement, ram + "NetPriceProductTradePrice")
        _text_el(net_price, ram + "ChargeAmount", _money(unit_price))

        line_delivery = _sub(li, ram + "SpecifiedLineTradeDelivery")
        qty_el = _text_el(line_delivery, ram + "BilledQuantity", _qty(quantity))
        if qty_el is not None:
            qty_el.set("unitCode", "C62")

        line_settle = _sub(li, ram + "SpecifiedLineTradeSettlement")
        line_tax = _sub(line_settle, ram + "ApplicableTradeTax")
        _text_el(line_tax, ram + "TypeCode", "VAT")
        _text_el(line_tax, ram + "CategoryCode", tax_category)
        _text_el(line_tax, ram + "RateApplicablePercent", _money(tax_rate))

        line_totals = _sub(line_settle, ram + "SpecifiedTradeSettlementLineMonetarySummation")
        _text_el(line_totals, ram + "LineTotalAmount", _money(line_total))

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

    # Expenses
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

    # Extra goods
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

    # If no lines were added, add a single placeholder line (CII requires at least one)
    if line_id == 1:
        _add_line(description="Invoice", quantity=1, unit_price=getattr(invoice, "total_amount", 0), line_total=getattr(invoice, "total_amount", 0))

    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    sha256_hex = hashlib.sha256(xml_bytes).hexdigest()
    return xml_bytes.decode("utf-8"), sha256_hex
