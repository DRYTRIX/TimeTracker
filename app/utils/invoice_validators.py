"""
Validation gates for invoice PDF, UBL, and CII exports.

Provides:
- UBL well-formedness + basic Peppol BIS 3.0 structure validation
- CII well-formedness + EN 16931 / Factur-X structure validation
- Optional veraPDF CLI invocation for PDF/A compliance
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from typing import List, Optional, Tuple

# ---- UBL Validation ----

_UBL_NS_INVOICE = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
_UBL_NS_CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
_UBL_NS_CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"

_PEPPOL_BIS3_CUSTOMIZATION_ID = "urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0"


def validate_ubl_wellformed(ubl_xml: str) -> Tuple[bool, List[str]]:
    """
    Check UBL XML is well-formed and contains Invoice root.
    Returns (passed, list of message strings).
    """
    messages: List[str] = []
    try:
        root = ET.fromstring(ubl_xml)
        local_tag = root.tag.split("}")[-1] if root.tag else ""
        if local_tag != "Invoice":
            messages.append("Root element is not an Invoice.")
            return False, messages
        return True, []
    except ET.ParseError as e:
        messages.append(f"Invalid XML: {e}")
        return False, messages


def validate_ubl_peppol_bis3(ubl_xml: str) -> Tuple[bool, List[str]]:
    """
    Validate UBL against Peppol BIS Billing 3.0 structural requirements.
    This checks required elements are present (not full Schematron).
    Returns (passed, list of issue strings).
    """
    issues: List[str] = []

    ok, parse_msgs = validate_ubl_wellformed(ubl_xml)
    if not ok:
        return False, parse_msgs

    root = ET.fromstring(ubl_xml)
    ns = {
        "inv": _UBL_NS_INVOICE,
        "cbc": _UBL_NS_CBC,
        "cac": _UBL_NS_CAC,
    }

    def _find_text(path: str) -> Optional[str]:
        el = root.find(path, ns)
        return el.text.strip() if el is not None and el.text else None

    cust_id = _find_text("cbc:CustomizationID")
    if not cust_id:
        issues.append("Missing cbc:CustomizationID (BT-24)")
    elif _PEPPOL_BIS3_CUSTOMIZATION_ID not in cust_id:
        issues.append(f"CustomizationID does not reference Peppol BIS 3.0: {cust_id}")

    if not _find_text("cbc:ProfileID"):
        issues.append("Missing cbc:ProfileID (BT-23)")

    if not _find_text("cbc:ID"):
        issues.append("Missing cbc:ID (BT-1, Invoice number)")

    type_code = _find_text("cbc:InvoiceTypeCode")
    if not type_code:
        issues.append("Missing cbc:InvoiceTypeCode (BT-3)")
    elif type_code not in ("380", "381", "384", "389", "751"):
        issues.append(f"Unusual InvoiceTypeCode: {type_code}")

    if not _find_text("cbc:IssueDate"):
        issues.append("Missing cbc:IssueDate (BT-2)")

    if not _find_text("cbc:DocumentCurrencyCode"):
        issues.append("Missing cbc:DocumentCurrencyCode (BT-5)")

    if not _find_text("cbc:BuyerReference"):
        issues.append("Missing cbc:BuyerReference (BT-10, required by Peppol)")

    supplier = root.find("cac:AccountingSupplierParty", ns)
    if supplier is None:
        issues.append("Missing AccountingSupplierParty")
    else:
        party = supplier.find("cac:Party", ns)
        if party is not None:
            ep = party.find("cbc:EndpointID", ns)
            if ep is None or not (ep.text or "").strip():
                issues.append("Supplier missing EndpointID")
            elif not ep.get("schemeID"):
                issues.append("Supplier EndpointID missing schemeID attribute")

    customer = root.find("cac:AccountingCustomerParty", ns)
    if customer is None:
        issues.append("Missing AccountingCustomerParty")
    else:
        party = customer.find("cac:Party", ns)
        if party is not None:
            ep = party.find("cbc:EndpointID", ns)
            if ep is None or not (ep.text or "").strip():
                issues.append("Customer missing EndpointID")

    lines = root.findall("cac:InvoiceLine", ns)
    if not lines:
        issues.append("No InvoiceLine elements found (at least one required)")
    for i, line in enumerate(lines, 1):
        qty = line.find("cbc:InvoicedQuantity", ns)
        if qty is not None and not qty.get("unitCode"):
            issues.append(f"InvoiceLine {i}: InvoicedQuantity missing unitCode attribute")

    tax_total = root.find("cac:TaxTotal", ns)
    if tax_total is None:
        issues.append("Missing TaxTotal")

    legal_total = root.find("cac:LegalMonetaryTotal", ns)
    if legal_total is None:
        issues.append("Missing LegalMonetaryTotal")
    else:
        if legal_total.find("cbc:PayableAmount", ns) is None:
            issues.append("Missing PayableAmount in LegalMonetaryTotal")

    return len(issues) == 0, issues


# ---- CII / Factur-X Validation ----

_CII_NS_RSM = "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
_CII_NS_RAM = "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
_CII_NS_UDT = "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100"


def validate_cii_wellformed(cii_xml: str) -> Tuple[bool, List[str]]:
    """
    Check CII XML is well-formed and contains CrossIndustryInvoice root.
    Returns (passed, list of message strings).
    """
    messages: List[str] = []
    try:
        root = ET.fromstring(cii_xml)
        local_tag = root.tag.split("}")[-1] if root.tag else ""
        if local_tag != "CrossIndustryInvoice":
            messages.append(f"Root element is '{local_tag}', expected 'CrossIndustryInvoice'.")
            return False, messages
        return True, []
    except ET.ParseError as e:
        messages.append(f"Invalid XML: {e}")
        return False, messages


def validate_cii_en16931(cii_xml: str) -> Tuple[bool, List[str]]:
    """
    Validate CII XML against EN 16931 / Factur-X structural requirements.
    Checks required elements for Factur-X EN 16931 (COMFORT) profile.
    Returns (passed, list of issue strings).
    """
    issues: List[str] = []

    ok, parse_msgs = validate_cii_wellformed(cii_xml)
    if not ok:
        return False, parse_msgs

    root = ET.fromstring(cii_xml)
    ns = {
        "rsm": _CII_NS_RSM,
        "ram": _CII_NS_RAM,
        "udt": _CII_NS_UDT,
    }

    def _find(path: str) -> Optional[ET.Element]:
        return root.find(path, ns)

    def _find_text(path: str) -> Optional[str]:
        el = root.find(path, ns)
        return el.text.strip() if el is not None and el.text else None

    # Context
    ctx = _find("rsm:ExchangedDocumentContext")
    if ctx is None:
        issues.append("Missing ExchangedDocumentContext")
    else:
        guideline = _find_text("rsm:ExchangedDocumentContext/ram:GuidelineSpecifiedDocumentContextParameter/ram:ID")
        if not guideline:
            issues.append("Missing GuidelineSpecifiedDocumentContextParameter/ID")

    # Document
    doc = _find("rsm:ExchangedDocument")
    if doc is None:
        issues.append("Missing ExchangedDocument")
    else:
        if not _find_text("rsm:ExchangedDocument/ram:ID"):
            issues.append("Missing ExchangedDocument/ID (BT-1, Invoice number)")
        if not _find_text("rsm:ExchangedDocument/ram:TypeCode"):
            issues.append("Missing ExchangedDocument/TypeCode (BT-3)")
        if _find("rsm:ExchangedDocument/ram:IssueDateTime") is None:
            issues.append("Missing ExchangedDocument/IssueDateTime (BT-2)")

    # Transaction
    txn = _find("rsm:SupplyChainTradeTransaction")
    if txn is None:
        issues.append("Missing SupplyChainTradeTransaction")
        return False, issues

    # Agreement
    agreement = txn.find("ram:ApplicableHeaderTradeAgreement", ns)
    if agreement is None:
        issues.append("Missing ApplicableHeaderTradeAgreement")
    else:
        seller = agreement.find("ram:SellerTradeParty", ns)
        if seller is None:
            issues.append("Missing SellerTradeParty")
        else:
            seller_name = seller.find("ram:Name", ns)
            if seller_name is None or not (seller_name.text or "").strip():
                issues.append("SellerTradeParty missing Name")

        buyer = agreement.find("ram:BuyerTradeParty", ns)
        if buyer is None:
            issues.append("Missing BuyerTradeParty")
        else:
            buyer_name = buyer.find("ram:Name", ns)
            if buyer_name is None or not (buyer_name.text or "").strip():
                issues.append("BuyerTradeParty missing Name")

    # Settlement
    settlement = txn.find("ram:ApplicableHeaderTradeSettlement", ns)
    if settlement is None:
        issues.append("Missing ApplicableHeaderTradeSettlement")
    else:
        if not settlement.find("ram:InvoiceCurrencyCode", ns) is not None:
            issues.append("Missing InvoiceCurrencyCode (BT-5)")
        summation = settlement.find("ram:SpecifiedTradeSettlementHeaderMonetarySummation", ns)
        if summation is None:
            issues.append("Missing SpecifiedTradeSettlementHeaderMonetarySummation")
        else:
            if summation.find("ram:GrandTotalAmount", ns) is None:
                issues.append("Missing GrandTotalAmount")
            if summation.find("ram:DuePayableAmount", ns) is None:
                issues.append("Missing DuePayableAmount")

    # Line items
    lines = txn.findall("ram:IncludedSupplyChainTradeLineItem", ns)
    if not lines:
        issues.append("No IncludedSupplyChainTradeLineItem (at least one required)")
    for i, line in enumerate(lines, 1):
        product = line.find("ram:SpecifiedTradeProduct", ns)
        if product is None or product.find("ram:Name", ns) is None:
            issues.append(f"Line {i}: missing SpecifiedTradeProduct/Name")
        delivery = line.find("ram:SpecifiedLineTradeDelivery", ns)
        if delivery is not None:
            qty = delivery.find("ram:BilledQuantity", ns)
            if qty is not None and not qty.get("unitCode"):
                issues.append(f"Line {i}: BilledQuantity missing unitCode attribute")

    return len(issues) == 0, issues


# ---- PDF / veraPDF Validation ----


def validate_pdfa_verapdf(
    pdf_bytes: bytes,
    verapdf_path: Optional[str] = None,
    timeout_s: int = 60,
) -> Tuple[bool, List[str]]:
    """
    Run veraPDF CLI on PDF bytes if path is set.
    Returns (passed, list of validator output lines or error messages).
    """
    path = (verapdf_path or os.getenv("INVOICE_VERAPDF_PATH") or "").strip()
    if not path or not os.path.isfile(path):
        return True, []

    messages: List[str] = []
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        try:
            tmp.write(pdf_bytes)
            tmp.flush()
            tmp_path = tmp.name
        except Exception as e:
            return False, [f"Could not write temp PDF: {e}"]

    try:
        result = subprocess.run(
            [path, tmp_path, "--format", "text"],
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        out = (result.stdout or "").strip()
        err = (result.stderr or "").strip()
        if result.returncode != 0:
            messages.append(f"veraPDF exited with code {result.returncode}")
        for line in (out + "\n" + err).splitlines():
            line = line.strip()
            if line and ("failed" in line.lower() or "error" in line.lower() or "invalid" in line.lower()):
                messages.append(line[:500])
        if messages:
            return False, messages[:20]
        if out:
            messages.append("veraPDF reported issues (see full output).")
            for line in out.splitlines()[:10]:
                if line.strip():
                    messages.append(line.strip()[:300])
        return result.returncode == 0, messages[:20]
    except subprocess.TimeoutExpired:
        return False, ["veraPDF validation timed out."]
    except FileNotFoundError:
        return False, [f"veraPDF not found at {path}"]
    except Exception as e:
        return False, [str(e)]
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
