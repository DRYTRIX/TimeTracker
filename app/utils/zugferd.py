"""
Factur-X / ZUGFeRD: embed CII XML into invoice PDFs.

When enabled, exported invoice PDFs contain an embedded CII (Cross-Industry
Invoice) XML file so the document is both human-readable (PDF) and
machine-readable (EN 16931). Embedding is done with pikepdf.

Standards compliance:
- The embedded XML uses UN/CEFACT CII format (NOT UBL). This is the
  correct payload format for Factur-X 1.0 / ZUGFeRD 2.x.
- Peppol transport uses UBL (see app/integrations/peppol.py).
- The file is attached as an Associated File with relationship "Alternative"
  and Factur-X XMP metadata is written so validators recognize the document.
"""

from __future__ import annotations

import io
import os
import tempfile
from typing import Any, Optional, Tuple

from app.utils.cii_invoice import CIIParty, build_cii_invoice_xml

# Standard embedded filename per Factur-X specification
FACTURX_EMBEDDED_FILENAME = "factur-x.xml"
# Legacy alias kept for backwards compatibility in tests
ZUGFERD_EMBEDDED_FILENAME = FACTURX_EMBEDDED_FILENAME

# Factur-X XMP namespace (PDF/A-3 Associated Files)
FACTURX_XMP_NS = "urn:factur-x:pdfa:CrossIndustryDocument:invoice:1p0#"


def _get_seller_party(settings: Any) -> CIIParty:
    """Build seller party from Settings (best-effort; placeholders if missing)."""
    return CIIParty(
        name=(getattr(settings, "company_name", None) or "Company").strip(),
        tax_id=(getattr(settings, "company_tax_id", None) or "").strip() or None,
        address_line=(getattr(settings, "company_address", None) or "").strip() or None,
        country_code=(
            (getattr(settings, "peppol_sender_country", "") or os.getenv("PEPPOL_SENDER_COUNTRY") or "").strip() or None
        ),
        email=(getattr(settings, "company_email", None) or "").strip() or None,
        phone=(getattr(settings, "company_phone", None) or "").strip() or None,
        endpoint_id=(
            (getattr(settings, "peppol_sender_endpoint_id", "") or os.getenv("PEPPOL_SENDER_ENDPOINT_ID") or "").strip()
            or None
        ),
        endpoint_scheme_id=(
            (getattr(settings, "peppol_sender_scheme_id", "") or os.getenv("PEPPOL_SENDER_SCHEME_ID") or "").strip()
            or None
        ),
    )


def _get_buyer_party(invoice: Any) -> CIIParty:
    """Build buyer party from invoice and client (best-effort)."""
    client = getattr(invoice, "client", None)
    name = (getattr(invoice, "client_name", None) or "Customer").strip()
    tax_id = None
    address_line = None
    email = None
    phone = None
    country = None
    endpoint_id = None
    scheme_id = None

    if client:
        endpoint_id = (client.get_custom_field("peppol_endpoint_id", "") or "").strip() or None
        scheme_id = (client.get_custom_field("peppol_scheme_id", "") or "").strip() or None
        country = (client.get_custom_field("peppol_country", "") or "").strip() or None
        name = (getattr(client, "name", None) or getattr(invoice, "client_name", "") or "Customer").strip()
        tax_id = (client.get_custom_field("vat_id", "") or client.get_custom_field("tax_id", "") or "").strip() or None
        address_line = (
            getattr(client, "address", None) or getattr(invoice, "client_address", None) or ""
        ).strip() or None
        email = (getattr(client, "email", None) or getattr(invoice, "client_email", None) or "").strip() or None
        phone = (getattr(client, "phone", None) or "").strip() or None

    return CIIParty(
        name=name,
        tax_id=tax_id,
        address_line=address_line,
        country_code=country,
        email=email,
        phone=phone,
        endpoint_id=endpoint_id,
        endpoint_scheme_id=scheme_id,
    )


# Minimal XMP template with rdf:RDF for Factur-X extension (PDF/A-3 style)
_FACTURX_XMP_TEMPLATE = """<?xpacket begin="\xef\xbb\xbf" id="W5M0MpCehiHzreSzNTczkc9d"?>
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
        rdf_desc = _facturx_rdf_description()
        minimal_xmp = _FACTURX_XMP_TEMPLATE.format(rdf_description=rdf_desc)
        pdf.Root.Metadata = pdf.make_stream(minimal_xmp.encode("utf-8"))
    except Exception:
        pass


def _facturx_rdf_description() -> str:
    """Return the Factur-X XMP RDF description block."""
    return (
        f'<rdf:Description rdf:about="" xmlns:fx="{FACTURX_XMP_NS}">'
        "<fx:DocumentType>INVOICE</fx:DocumentType>"
        f"<fx:DocumentFileName>{FACTURX_EMBEDDED_FILENAME}</fx:DocumentFileName>"
        "<fx:Version>1.0</fx:Version>"
        "<fx:ConformanceLevel>EN 16931</fx:ConformanceLevel>"
        "</rdf:Description>"
    )


def _add_facturx_xmp(pdf: Any) -> None:
    """Add or ensure Factur-X XMP RDF so validators recognize the embedded CII XML."""
    facturx_rdf = _facturx_rdf_description()
    _ensure_metadata_stream(pdf)
    if not hasattr(pdf, "Root") or not hasattr(pdf.Root, "Metadata"):
        return
    try:
        xmp_bytes = pdf.Root.Metadata.read_bytes()
    except Exception:
        return
    xmp_str = xmp_bytes.decode("utf-8", errors="replace")
    if "fx:DocumentType" in xmp_str or "factur-x" in xmp_str.lower():
        return
    marker = "</rdf:RDF>"
    if marker in xmp_str:
        try:
            insert_pos = xmp_str.rfind(marker)
            new_xmp = xmp_str[:insert_pos] + facturx_rdf + "\n    " + xmp_str[insert_pos:]
            pdf.Root.Metadata = pdf.make_stream(new_xmp.encode("utf-8"))
        except Exception:
            pass
    else:
        try:
            minimal_xmp = _FACTURX_XMP_TEMPLATE.format(rdf_description=facturx_rdf)
            pdf.Root.Metadata = pdf.make_stream(minimal_xmp.encode("utf-8"))
        except Exception:
            pass


def embed_zugferd_xml_in_pdf(pdf_bytes: bytes, invoice: Any, settings: Any) -> Tuple[bytes, Optional[str]]:
    """
    Embed Factur-X CII XML into the given invoice PDF bytes.

    Builds seller/buyer from settings and invoice (best-effort), generates CII
    XML, attaches it as factur-x.xml with AF relationship "Alternative", adds
    Factur-X XMP RDF, and returns the new PDF bytes.

    Returns:
        (new_pdf_bytes, None) on success, or (original_pdf_bytes, error_message) on failure.
    """
    try:
        import pikepdf
        from pikepdf import AttachedFileSpec
    except ImportError as e:
        return pdf_bytes, f"pikepdf not available: {e}"

    try:
        seller = _get_seller_party(settings)
        buyer = _get_buyer_party(invoice)
        cii_xml, _ = build_cii_invoice_xml(invoice=invoice, seller=seller, buyer=buyer)
    except Exception as e:
        return pdf_bytes, f"Failed to build CII XML for Factur-X: {e}"

    try:
        pdf = pikepdf.open(io.BytesIO(pdf_bytes))
        cii_bytes = cii_xml.encode("utf-8")
        try:
            from pikepdf import Name

            relationship = Name("/Alternative")
        except ImportError:
            relationship = "/Alternative"
        try:
            filespec = AttachedFileSpec(
                pdf,
                cii_bytes,
                filename=FACTURX_EMBEDDED_FILENAME,
                mime_type="application/xml",
                relationship=relationship,
            )
        except TypeError:
            with tempfile.NamedTemporaryFile(mode="wb", suffix=".xml", delete=False, prefix="facturx_") as tmp:
                tmp.write(cii_bytes)
                tmp_path = tmp.name
            try:
                filespec = AttachedFileSpec.from_filepath(pdf, tmp_path, relationship="/Alternative")
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
        pdf.attachments[FACTURX_EMBEDDED_FILENAME] = filespec
        _add_facturx_xmp(pdf)
        out = io.BytesIO()
        try:
            pdf.save(out, min_version=("1", 7))
        except TypeError:
            pdf.save(out, min_version="1.7")
        pdf.close()
        return out.getvalue(), None
    except Exception as e:
        return pdf_bytes, f"Failed to embed Factur-X CII XML in PDF: {e}"
