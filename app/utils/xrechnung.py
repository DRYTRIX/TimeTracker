"""
XRechnung (Germany) export helper — experimental minimal skeleton.

Full CIUS-DE / EN 16931 compliance is TODO; this module produces a minimal UBL 2.1
Invoice XML shell suitable for pipeline wiring and validator smoke tests.

For production German e-invoicing, extend with complete BT/BG mappings and
embed via the Factur-X / Peppol paths where applicable.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date
from decimal import Decimal
from typing import Any, Optional
from xml.dom import minidom

UBL_NS = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
CBC_NS = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
CAC_NS = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"

ET.register_namespace("", UBL_NS)
ET.register_namespace("cbc", CBC_NS)
ET.register_namespace("cac", CAC_NS)


def build_minimal_xrechnung_xml(
    invoice: Any,
    *,
    seller_name: str,
    buyer_name: str,
    currency: str = "EUR",
) -> str:
    """
    Build a minimal UBL Invoice XML document for an invoice model instance.

    TODO: Map full XRechnung / CIUS-DE mandatory fields (seller/buyer address,
    VAT IDs, payment means, line-level tax categories, etc.).
    """
    root = ET.Element(f"{{{UBL_NS}}}Invoice")
    inv_id = str(getattr(invoice, "invoice_number", None) or getattr(invoice, "id", ""))
    issue = getattr(invoice, "issue_date", None) or date.today()
    if hasattr(issue, "isoformat"):
        issue_str = issue.isoformat()
    else:
        issue_str = str(issue)

    ET.SubElement(root, f"{{{CBC_NS}}}CustomizationID").text = (
        "urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:standard:xrechnung_2.0"
    )
    ET.SubElement(root, f"{{{CBC_NS}}}ProfileID").text = "urn:fdc:peppol.eu:2017:poacc:billing:01:1.0"
    ET.SubElement(root, f"{{{CBC_NS}}}ID").text = inv_id
    ET.SubElement(root, f"{{{CBC_NS}}}IssueDate").text = issue_str
    ET.SubElement(root, f"{{{CBC_NS}}}InvoiceTypeCode").text = "380"
    ET.SubElement(root, f"{{{CBC_NS}}}DocumentCurrencyCode").text = currency.upper()

    supplier = ET.SubElement(root, f"{{{CAC_NS}}}AccountingSupplierParty")
    sp = ET.SubElement(supplier, f"{{{CAC_NS}}}Party")
    spn = ET.SubElement(sp, f"{{{CAC_NS}}}PartyName")
    ET.SubElement(spn, f"{{{CBC_NS}}}Name").text = seller_name or "Seller"

    customer = ET.SubElement(root, f"{{{CAC_NS}}}AccountingCustomerParty")
    cp = ET.SubElement(customer, f"{{{CAC_NS}}}Party")
    cpn = ET.SubElement(cp, f"{{{CAC_NS}}}PartyName")
    ET.SubElement(cpn, f"{{{CBC_NS}}}Name").text = buyer_name or "Buyer"

    total = Decimal(str(getattr(invoice, "total_amount", None) or getattr(invoice, "total", 0) or 0))
    monetary = ET.SubElement(root, f"{{{CAC_NS}}}LegalMonetaryTotal")
    ET.SubElement(monetary, f"{{{CBC_NS}}}PayableAmount", currencyID=currency.upper()).text = f"{total:.2f}"

    rough = ET.tostring(root, encoding="unicode")
    parsed = minidom.parseString(rough)
    return parsed.toprettyxml(indent="  ")


def xrechnung_export_available() -> bool:
    """Feature flag helper: XRechnung export is experimental until full CIUS mapping ships."""
    return True
