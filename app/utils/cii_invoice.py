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
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Optional, Tuple

NS_RSM = "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
NS_RAM = "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
NS_UDT = "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100"
NS_QDT = "urn:un:unece:uncefact:data:standard:QualifiedDataType:100"

FACTURX_GUIDELINE_EN16931 = "urn:cen.eu:en16931:2017#compliant#urn:factur-x.eu:1p0:en16931"

# VAT categories that require exemption reason (header ApplicableTradeTax only)
_EXEMPTION_CATEGORIES = frozenset({"E", "AE", "K", "G", "O"})
# Valid EN 16931 VAT category codes
VAT_CATEGORIES = frozenset({"S", "Z", "E", "AE", "K", "G", "O", "L", "M"})

# Common exemption presets (code, reason)
VAT_EXEMPTION_PRESETS = {
    "at_kleinunternehmer": (
        "VATEX-EU-O",
        "Kleinunternehmerregelung §6 Abs. 1 Z 27 UStG",
    ),
    "de_kleinunternehmer": (
        "VATEX-EU-O",
        "Steuerfreie Kleinunternehmerleistung gemäß §19 UStG",
    ),
    "reverse_charge": (
        "VATEX-EU-AE",
        "Reverse charge",
    ),
}


@dataclass(frozen=True)
class CIIParty:
    name: str
    tax_id: Optional[str] = None
    address_line: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    postcode: Optional[str] = None
    country_code: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    endpoint_id: Optional[str] = None
    endpoint_scheme_id: Optional[str] = None
    iban: Optional[str] = None
    bic: Optional[str] = None


def _money(v: Any) -> str:
    try:
        d = v if isinstance(v, Decimal) else Decimal(str(v))
    except Exception:
        d = Decimal("0")
    return f"{d.quantize(Decimal('0.01'))}"


def _money4(v: Any) -> str:
    """Unit price with up to 4 decimal places (strip trailing zeros beyond 2)."""
    try:
        d = v if isinstance(v, Decimal) else Decimal(str(v))
    except Exception:
        d = Decimal("0")
    q = d.quantize(Decimal("0.0001"))
    # Prefer 2 decimals when exact, else keep up to 4
    if q == q.quantize(Decimal("0.01")):
        return f"{q.quantize(Decimal('0.01'))}"
    return f"{q}".rstrip("0").rstrip(".") if "." in f"{q}" else f"{q}"


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


def _money_el(
    parent: ET.Element,
    tag: str,
    value: Any,
    currency: Optional[str] = None,
    *,
    decimals: int = 2,
) -> Optional[ET.Element]:
    """Monetary element; currencyID only when currency is provided (TaxTotalAmount)."""
    text = _money4(value) if decimals == 4 else _money(value)
    el = _text_el(parent, tag, text)
    if el is not None and currency:
        el.set("currencyID", currency)
    return el


def _date_el(parent: ET.Element, d: Any) -> None:
    """Add a DateTimeString child with format 102."""
    udt = f"{{{NS_UDT}}}"
    dts = _sub(parent, udt + "DateTimeString")
    dts.set("format", "102")
    dts.text = _date_102(d)


def resolve_vat_category(
    invoice: Any,
    settings: Any = None,
) -> Tuple[str, Decimal, Optional[str], Optional[str]]:
    """
    Resolve VAT category, rate, exemption reason and code.

    Priority: invoice override → settings default → infer from tax_rate
    (S if rate > 0, else E with settings exemption or a generic reason).
    """
    tax_rate = Decimal(str(getattr(invoice, "tax_rate", 0) or 0))

    inv_cat = (getattr(invoice, "vat_category", None) or "").strip().upper() or None
    inv_reason = (getattr(invoice, "vat_exemption_reason", None) or "").strip() or None
    inv_code = (getattr(invoice, "vat_exemption_code", None) or "").strip() or None

    def_cat = None
    def_reason = None
    def_code = None
    if settings is not None:
        def_cat = (getattr(settings, "invoices_default_vat_category", None) or "").strip().upper() or None
        def_reason = (getattr(settings, "invoices_default_vat_exemption_reason", None) or "").strip() or None
        def_code = (getattr(settings, "invoices_default_vat_exemption_code", None) or "").strip() or None

    category = inv_cat or def_cat
    if not category:
        category = "S" if tax_rate > 0 else "E"
    if category not in VAT_CATEGORIES:
        category = "S" if tax_rate > 0 else "E"

    reason = inv_reason or def_reason
    code = inv_code or def_code

    if category in _EXEMPTION_CATEGORIES:
        if not reason:
            if category == "AE":
                reason = "Reverse charge"
                code = code or "VATEX-EU-AE"
            elif category == "K":
                reason = "Intra-Community supply"
                code = code or "VATEX-EU-IC"
            elif category == "G":
                reason = "Export outside the EU"
                code = code or "VATEX-EU-G"
            elif category == "O":
                reason = "Not subject to VAT"
                code = code or "VATEX-EU-O"
            else:  # E
                reason = "VAT exempt"
                code = code or "VATEX-EU-O"
        # Zero rate for exemption categories
        tax_rate = Decimal("0")
    elif category == "Z":
        # Zero-rated goods — no exemption reason (BR-Z-10)
        reason = None
        code = None
        tax_rate = Decimal("0")
    else:
        # S, L, M — no exemption
        reason = None
        code = None

    return category, tax_rate, reason, code


def _build_party(parent: ET.Element, tag: str, party: CIIParty, *, is_seller: bool = False) -> None:
    ram = f"{{{NS_RAM}}}"
    p = _sub(parent, ram + tag)
    _text_el(p, ram + "Name", party.name)

    # XSD order: Name, DefinedTradeContact*, PostalTradeAddress?,
    # URIUniversalCommunication*, SpecifiedTaxRegistration*
    if is_seller and (party.email or party.phone):
        contact = _sub(p, ram + "DefinedTradeContact")
        if party.phone:
            phone_comm = _sub(contact, ram + "TelephoneUniversalCommunication")
            _text_el(phone_comm, ram + "CompleteNumber", party.phone)
        if party.email:
            email_comm = _sub(contact, ram + "EmailURIUniversalCommunication")
            _text_el(email_comm, ram + "URIID", party.email)

    # PostalTradeAddress order: PostcodeCode, LineOne, CityName, CountryID
    line_one = party.street or party.address_line
    if line_one or party.city or party.postcode or party.country_code:
        addr = _sub(p, ram + "PostalTradeAddress")
        _text_el(addr, ram + "PostcodeCode", party.postcode)
        _text_el(addr, ram + "LineOne", line_one)
        _text_el(addr, ram + "CityName", party.city)
        _text_el(addr, ram + "CountryID", party.country_code)

    # Electronic address / Peppol endpoint (BT-34 / BT-49)
    if party.endpoint_id and party.endpoint_scheme_id:
        uri_comm = _sub(p, ram + "URIUniversalCommunication")
        uri_id = _text_el(uri_comm, ram + "URIID", party.endpoint_id)
        if uri_id is not None:
            uri_id.set("schemeID", party.endpoint_scheme_id)

    if party.tax_id:
        tax_reg = _sub(p, ram + "SpecifiedTaxRegistration")
        tax_reg_id = _text_el(tax_reg, ram + "ID", party.tax_id)
        if tax_reg_id is not None:
            tax_reg_id.set("schemeID", "VA")


def _unit_code_for_line(item: Any, description: str) -> str:
    """Return UNECE unit code; HUR for time-based lines, else C62 (one)."""
    explicit = getattr(item, "unit_code", None) or getattr(item, "unit", None)
    if explicit:
        u = str(explicit).strip().upper()
        if u in ("HUR", "H", "HR", "HOUR", "HOURS"):
            return "HUR"
        if len(u) == 3:
            return u
    desc = (description or "").lower()
    if any(k in desc for k in ("hour", "stunden", "uur", "heure")):
        return "HUR"
    # InvoiceItem from time entries often has time_entry_id
    if getattr(item, "time_entry_id", None):
        return "HUR"
    return "C62"


def build_cii_invoice_xml(
    invoice: Any,
    seller: CIIParty,
    buyer: CIIParty,
    guideline_id: str = FACTURX_GUIDELINE_EN16931,
    settings: Any = None,
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
    tax_category, tax_rate, exemption_reason, exemption_code = resolve_vat_category(invoice, settings)

    # --- Line Items (must appear BEFORE header agreement in CII XSD order) ---
    # Actually in CrossIndustryInvoice the order within SupplyChainTradeTransaction is:
    # IncludedSupplyChainTradeLineItem*, ApplicableHeaderTradeAgreement,
    # ApplicableHeaderTradeDelivery, ApplicableHeaderTradeSettlement
    # So lines come FIRST.

    line_id = 1
    line_items_holder: list = []  # collect then insert — we'll build lines into a temp list of elements

    def _add_line(description: str, quantity: Any, unit_price: Any, line_total: Any, item: Any = None) -> None:
        nonlocal line_id
        li = ET.Element(ram + "IncludedSupplyChainTradeLineItem")

        line_doc = _sub(li, ram + "AssociatedDocumentLineDocument")
        _text_el(line_doc, ram + "LineID", str(line_id))

        product = _sub(li, ram + "SpecifiedTradeProduct")
        _text_el(product, ram + "Name", str(description)[:200])

        line_agreement = _sub(li, ram + "SpecifiedLineTradeAgreement")
        net_price = _sub(line_agreement, ram + "NetPriceProductTradePrice")
        _money_el(net_price, ram + "ChargeAmount", unit_price, decimals=4)

        line_delivery = _sub(li, ram + "SpecifiedLineTradeDelivery")
        qty_el = _text_el(line_delivery, ram + "BilledQuantity", _qty(quantity))
        if qty_el is not None:
            qty_el.set("unitCode", _unit_code_for_line(item, description) if item is not None else "C62")

        line_settle = _sub(li, ram + "SpecifiedLineTradeSettlement")
        line_tax = _sub(line_settle, ram + "ApplicableTradeTax")
        _text_el(line_tax, ram + "TypeCode", "VAT")
        _text_el(line_tax, ram + "CategoryCode", tax_category)
        _text_el(line_tax, ram + "RateApplicablePercent", _money(tax_rate))
        # Line-level tax must NOT carry exemption reasons

        line_totals = _sub(line_settle, ram + "SpecifiedTradeSettlementLineMonetarySummation")
        _money_el(line_totals, ram + "LineTotalAmount", line_total)

        line_items_holder.append(li)
        line_id += 1

    # Invoice items
    try:
        for it in list(getattr(invoice, "items", []) or []):
            _add_line(
                description=getattr(it, "description", "Item"),
                quantity=getattr(it, "quantity", 1),
                unit_price=getattr(it, "unit_price", 0),
                line_total=getattr(it, "total_amount", 0),
                item=it,
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
                item=ex,
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
                item=g,
            )
    except Exception:
        pass

    if line_id == 1:
        _add_line(
            description="Invoice",
            quantity=1,
            unit_price=getattr(invoice, "total_amount", 0),
            line_total=getattr(invoice, "total_amount", 0),
        )

    for li in line_items_holder:
        txn.append(li)

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

    _build_party(agreement, "SellerTradeParty", seller, is_seller=True)
    _build_party(agreement, "BuyerTradeParty", buyer, is_seller=False)

    # --- Header Trade Delivery ---
    _sub(txn, ram + "ApplicableHeaderTradeDelivery")

    # --- Header Trade Settlement ---
    settlement = _sub(txn, ram + "ApplicableHeaderTradeSettlement")
    _text_el(settlement, ram + "InvoiceCurrencyCode", currency)

    # Payment means (BG-16) when IBAN configured
    iban = seller.iban
    bic = seller.bic
    if iban:
        pm = _sub(settlement, ram + "SpecifiedTradeSettlementPaymentMeans")
        _text_el(pm, ram + "TypeCode", "58")  # SEPA credit transfer
        _text_el(pm, ram + "Information", getattr(invoice, "invoice_number", None) or "")
        account = _sub(pm, ram + "PayeePartyCreditorFinancialAccount")
        _text_el(account, ram + "IBANID", iban.replace(" ", ""))
        if bic:
            inst = _sub(pm, ram + "PayeeSpecifiedCreditorFinancialInstitution")
            _text_el(inst, ram + "BICID", bic.replace(" ", ""))

    # Tax summary — element order:
    # CalculatedAmount, TypeCode, ExemptionReason, BasisAmount, CategoryCode,
    # ExemptionReasonCode, RateApplicablePercent
    tax_el = _sub(settlement, ram + "ApplicableTradeTax")
    _money_el(tax_el, ram + "CalculatedAmount", getattr(invoice, "tax_amount", 0))
    _text_el(tax_el, ram + "TypeCode", "VAT")
    if exemption_reason:
        _text_el(tax_el, ram + "ExemptionReason", exemption_reason)
    _money_el(tax_el, ram + "BasisAmount", getattr(invoice, "subtotal", 0))
    _text_el(tax_el, ram + "CategoryCode", tax_category)
    if exemption_code:
        _text_el(tax_el, ram + "ExemptionReasonCode", exemption_code)
    _text_el(tax_el, ram + "RateApplicablePercent", _money(tax_rate))

    # Payment terms (due date)
    due_date = getattr(invoice, "due_date", None)
    if due_date:
        terms = _sub(settlement, ram + "SpecifiedTradePaymentTerms")
        due_dt = _sub(terms, ram + "DueDateDateTime")
        _date_el(due_dt, due_date)

    # Monetary summation — currencyID only on TaxTotalAmount
    prepaid = Decimal(str(getattr(invoice, "amount_paid", 0) or 0))
    total = Decimal(str(getattr(invoice, "total_amount", 0) or 0))
    due_payable = total - prepaid
    if due_payable < 0:
        due_payable = Decimal("0")

    totals = _sub(settlement, ram + "SpecifiedTradeSettlementHeaderMonetarySummation")
    _money_el(totals, ram + "LineTotalAmount", getattr(invoice, "subtotal", 0))
    _money_el(totals, ram + "TaxBasisTotalAmount", getattr(invoice, "subtotal", 0))
    _money_el(totals, ram + "TaxTotalAmount", getattr(invoice, "tax_amount", 0), currency)
    _money_el(totals, ram + "GrandTotalAmount", getattr(invoice, "total_amount", 0))
    if prepaid > 0:
        _money_el(totals, ram + "TotalPrepaidAmount", prepaid)
    _money_el(totals, ram + "DuePayableAmount", due_payable)

    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    sha256_hex = hashlib.sha256(xml_bytes).hexdigest()
    return xml_bytes.decode("utf-8"), sha256_hex
