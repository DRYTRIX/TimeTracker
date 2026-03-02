"""
ZugFerd / Factur-X: embed EN 16931 UBL XML into invoice PDFs.

When enabled, exported invoice PDFs contain an embedded XML file (ZUGFeRD-invoice.xml)
so the file is both human-readable (PDF) and machine-readable (EN 16931). The same
UBL used for Peppol is reused; embedding is done with pikepdf.
The attachment is added as an Associated File with relationship "Alternative" and
ZUGFeRD XMP RDF is written so validators recognize the document.
"""

from __future__ import annotations

import io
import os
import tempfile
from typing import Any, Optional, Tuple

from app.integrations.peppol import PeppolParty, build_peppol_ubl_invoice_xml


# Standard embedded filename for ZUGFeRD/Factur-X (EN 16931)
ZUGFERD_EMBEDDED_FILENAME = "ZUGFeRD-invoice.xml"

# ZUGFeRD/Factur-X XMP namespace (PDF/A-3 Associated Files)
ZUGFERD_XMP_NS = "urn:ferd:pdfa:CrossIndustryDocument:invoice:1p0#"


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


# Minimal XMP with rdf:RDF for ZUGFeRD extension (PDF/A-3 style)
_ZUGFERD_XMP_TEMPLATE = """<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    {rdf_description}
  </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>"""


def _ensure_metadata_stream(pdf: Any) -> None:
    """Ensure PDF has a Root/Metadata stream; create minimal XMP if missing."""
    if not hasattr(pdf, "Root"):
        return
    if hasattr(pdf.Root, "Metadata") and pdf.Root.Metadata is not None:
        return
    try:
        minimal_xmp = _ZUGFERD_XMP_TEMPLATE.format(
            rdf_description=(
                f'<rdf:Description rdf:about="" xmlns:zf="{ZUGFERD_XMP_NS}">'
                "<zf:DocumentType>INVOICE</zf:DocumentType>"
                f"<zf:DocumentFileName>{ZUGFERD_EMBEDDED_FILENAME}</zf:DocumentFileName>"
                "<zf:Version>2.1</zf:Version>"
                "<zf:ConformanceLevel>EN 16931</zf:ConformanceLevel>"
                "</rdf:Description>"
            )
        )
        pdf.Root.Metadata = pdf.make_stream(minimal_xmp.encode("utf-8"))
    except Exception:
        pass


def _add_zugferd_xmp(pdf: Any) -> None:
    """Add or ensure ZUGFeRD/Factur-X XMP RDF so validators recognize the embedded invoice XML."""
    zugferd_rdf = (
        f'<rdf:Description rdf:about="" xmlns:zf="{ZUGFERD_XMP_NS}">'
        "<zf:DocumentType>INVOICE</zf:DocumentType>"
        f"<zf:DocumentFileName>{ZUGFERD_EMBEDDED_FILENAME}</zf:DocumentFileName>"
        "<zf:Version>2.1</zf:Version>"
        "<zf:ConformanceLevel>EN 16931</zf:ConformanceLevel>"
        "</rdf:Description>"
    )
    _ensure_metadata_stream(pdf)
    if not hasattr(pdf, "Root") or not hasattr(pdf.Root, "Metadata"):
        return
    try:
        xmp_bytes = pdf.Root.Metadata.read_bytes()
    except Exception:
        return
    xmp_str = xmp_bytes.decode("utf-8", errors="replace")
    if "zf:DocumentType" in xmp_str:
        return
    marker = "</rdf:RDF>"
    if marker in xmp_str:
        try:
            insert_pos = xmp_str.rfind(marker)
            new_xmp = xmp_str[:insert_pos] + zugferd_rdf + "\n    " + xmp_str[insert_pos:]
            pdf.Root.Metadata = pdf.make_stream(new_xmp.encode("utf-8"))
        except Exception:
            pass
    else:
        try:
            minimal_xmp = _ZUGFERD_XMP_TEMPLATE.format(rdf_description=zugferd_rdf)
            pdf.Root.Metadata = pdf.make_stream(minimal_xmp.encode("utf-8"))
        except Exception:
            pass


def embed_zugferd_xml_in_pdf(pdf_bytes: bytes, invoice: Any, settings: Any) -> Tuple[bytes, Optional[str]]:
    """
    Embed EN 16931 UBL XML into the given invoice PDF bytes (ZugFerd/Factur-X).

    Builds supplier/customer from settings and invoice (best-effort), generates UBL,
    attaches it as ZUGFeRD-invoice.xml with AF relationship "Alternative", adds
    ZUGFeRD XMP RDF, and returns the new PDF bytes.

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
        ubl_bytes = ubl_xml.encode("utf-8")
        # AttachedFileSpec(pdf, data, ...) - relationship must be Name for ZUGFeRD /Alternative
        try:
            from pikepdf import Name
            relationship = Name("/Alternative")
        except ImportError:
            relationship = "/Alternative"
        try:
            filespec = AttachedFileSpec(
                pdf,
                ubl_bytes,
                filename=ZUGFERD_EMBEDDED_FILENAME,
                mime_type="application/xml",
                relationship=relationship,
            )
        except TypeError:
            # Older pikepdf: from_filepath(path, relationship=...) or different constructor
            with tempfile.NamedTemporaryFile(
                mode="wb", suffix=".xml", delete=False, prefix="zugferd_"
            ) as tmp:
                tmp.write(ubl_bytes)
                tmp_path = tmp.name
            try:
                filespec = AttachedFileSpec.from_filepath(pdf, tmp_path, relationship="/Alternative")
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
        pdf.attachments[ZUGFERD_EMBEDDED_FILENAME] = filespec
        _add_zugferd_xmp(pdf)
        out = io.BytesIO()
        # pikepdf may require version as (str, int) for PDF 1.7
        try:
            pdf.save(out, min_version=("1", 7))
        except TypeError:
            pdf.save(out, min_version="1.7")
        pdf.close()
        return out.getvalue(), None
    except Exception as e:
        return pdf_bytes, f"Failed to embed ZugFerd XML in PDF: {e}"
