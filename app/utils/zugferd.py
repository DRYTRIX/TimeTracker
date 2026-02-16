"""
ZugFerd / Factur-X: embed EN 16931 UBL XML into invoice PDFs.

When enabled, exported invoice PDFs contain an embedded XML file (ZUGFeRD-invoice.xml)
so the file is both human-readable (PDF) and machine-readable (EN 16931). The same
UBL used for Peppol is reused; embedding is done with pikepdf.
"""

from __future__ import annotations

import io
import os
from typing import Any, Optional, Tuple

from app.integrations.peppol import PeppolParty, build_peppol_ubl_invoice_xml


# Standard embedded filename for ZUGFeRD/Factur-X (EN 16931)
ZUGFERD_EMBEDDED_FILENAME = "ZUGFeRD-invoice.xml"


def _get_sender_party_for_zugferd(settings: Any) -> PeppolParty:
    """Build supplier party from Settings (best-effort; placeholders if missing)."""
    sender_endpoint_id = (
        (getattr(settings, "peppol_sender_endpoint_id", "") or os.getenv("PEPPOL_SENDER_ENDPOINT_ID") or "").strip()
        or "unknown"
    )
    sender_scheme_id = (
        (getattr(settings, "peppol_sender_scheme_id", "") or os.getenv("PEPPOL_SENDER_SCHEME_ID") or "").strip()
        or "0000"
    )
    sender_country = (
        (getattr(settings, "peppol_sender_country", "") or os.getenv("PEPPOL_SENDER_COUNTRY") or "").strip()
        or None
    )
    return PeppolParty(
        endpoint_id=sender_endpoint_id,
        endpoint_scheme_id=sender_scheme_id,
        name=(getattr(settings, "company_name", None) or "Company").strip(),
        tax_id=(getattr(settings, "company_tax_id", None) or "").strip() or None,
        address_line=(getattr(settings, "company_address", None) or "").strip() or None,
        country_code=sender_country,
        email=(getattr(settings, "company_email", None) or "").strip() or None,
        phone=(getattr(settings, "company_phone", None) or "").strip() or None,
    )


def _get_customer_party_for_zugferd(invoice: Any) -> PeppolParty:
    """Build customer party from invoice and client (best-effort; placeholders if missing)."""
    client = getattr(invoice, "client", None)
    endpoint_id = "unknown"
    scheme_id = "0000"
    country = None
    name = (getattr(invoice, "client_name", None) or "Customer").strip()
    tax_id = None
    address_line = None
    email = None
    phone = None

    if client:
        endpoint_id = (client.get_custom_field("peppol_endpoint_id", "") or "").strip() or "unknown"
        scheme_id = (client.get_custom_field("peppol_scheme_id", "") or "").strip() or "0000"
        country = (client.get_custom_field("peppol_country", "") or "").strip() or None
        name = (getattr(client, "name", None) or getattr(invoice, "client_name", "") or "Customer").strip()
        tax_id = (client.get_custom_field("vat_id", "") or client.get_custom_field("tax_id", "") or "").strip() or None
        address_line = (getattr(client, "address", None) or getattr(invoice, "client_address", None) or "").strip() or None
        email = (getattr(client, "email", None) or getattr(invoice, "client_email", None) or "").strip() or None
        phone = (getattr(client, "phone", None) or "").strip() or None

    return PeppolParty(
        endpoint_id=endpoint_id,
        endpoint_scheme_id=scheme_id,
        name=name,
        tax_id=tax_id,
        address_line=address_line,
        country_code=country,
        email=email,
        phone=phone,
    )


def embed_zugferd_xml_in_pdf(pdf_bytes: bytes, invoice: Any, settings: Any) -> Tuple[bytes, Optional[str]]:
    """
    Embed EN 16931 UBL XML into the given invoice PDF bytes (ZugFerd/Factur-X).

    Builds supplier/customer from settings and invoice (best-effort), generates UBL,
    attaches it as ZUGFeRD-invoice.xml, and returns the new PDF bytes.

    Returns:
        (new_pdf_bytes, None) on success, or (original_pdf_bytes, error_message) on failure.
    """
    try:
        import pikepdf
        from pikepdf import AttachedFileSpec
    except ImportError as e:
        return pdf_bytes, f"pikepdf not available: {e}"

    try:
        supplier = _get_sender_party_for_zugferd(settings)
        customer = _get_customer_party_for_zugferd(invoice)
        ubl_xml, _ = build_peppol_ubl_invoice_xml(invoice=invoice, supplier=supplier, customer=customer)
    except Exception as e:
        return pdf_bytes, f"Failed to build UBL for ZugFerd: {e}"

    try:
        pdf = pikepdf.open(io.BytesIO(pdf_bytes))
        filespec = AttachedFileSpec(pdf, ubl_xml.encode("utf-8"), mime_type="application/xml")
        pdf.attachments[ZUGFERD_EMBEDDED_FILENAME] = filespec
        out = io.BytesIO()
        pdf.save(out, min_version="1.7")
        pdf.close()
        return out.getvalue(), None
    except Exception as e:
        return pdf_bytes, f"Failed to embed ZugFerd XML in PDF: {e}"
