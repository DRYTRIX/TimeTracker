"""
Factur-X / ZUGFeRD: embed CII XML into invoice PDFs.

When enabled, exported invoice PDFs contain an embedded CII (Cross-Industry
Invoice) XML file so the document is both human-readable (PDF) and
machine-readable (EN 16931). Embedding is done with pikepdf.

Standards compliance:
- The embedded XML uses UN/CEFACT CII format (NOT UBL). This is the
  correct payload format for Factur-X 1.0 / ZUGFeRD 2.x.
- Peppol transport uses UBL (see app/integrations/peppol.py).
- The file is attached as an Associated File with relationship "Data"
  (primary machine-readable invoice), catalog /AF array, and Factur-X
  XMP metadata (with pdfaExtension schema) so validators recognize the
  document. Optional PDF/A-3b normalization (OutputIntent + pdfaid) can
  run in the same pikepdf session.
"""

from __future__ import annotations

import io
import os
from datetime import datetime, timezone
from typing import Any, Optional, Tuple

from app.utils.cii_invoice import CIIParty, build_cii_invoice_xml
from app.utils.pdfa3 import (
    FACTURX_EMBEDDED_FILENAME as _PDFA_FX_NAME,
    apply_output_intent,
    apply_pdfa3_metadata,
)

# Standard embedded filename per Factur-X specification
FACTURX_EMBEDDED_FILENAME = "factur-x.xml"
# Legacy alias kept for backwards compatibility in tests
ZUGFERD_EMBEDDED_FILENAME = FACTURX_EMBEDDED_FILENAME

# Factur-X XMP namespace (PDF/A-3 Associated Files)
FACTURX_XMP_NS = "urn:factur-x:pdfa:CrossIndustryDocument:invoice:1p0#"

assert FACTURX_EMBEDDED_FILENAME == _PDFA_FX_NAME


def _get_seller_party(settings: Any) -> CIIParty:
    """Build seller party from Settings (structured address preferred)."""
    street = (getattr(settings, "company_street", None) or "").strip() or None
    postcode = (getattr(settings, "company_postcode", None) or "").strip() or None
    city = (getattr(settings, "company_city", None) or "").strip() or None
    country = (getattr(settings, "company_country", None) or "").strip() or None
    if not country:
        country = (
            (getattr(settings, "peppol_sender_country", "") or os.getenv("PEPPOL_SENDER_COUNTRY") or "").strip() or None
        )
    address_line = street or (getattr(settings, "company_address", None) or "").strip() or None

    return CIIParty(
        name=(getattr(settings, "company_name", None) or "Company").strip(),
        tax_id=(getattr(settings, "company_tax_id", None) or "").strip() or None,
        address_line=address_line,
        street=street,
        city=city,
        postcode=postcode,
        country_code=country,
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
        iban=(getattr(settings, "company_iban", None) or "").strip() or None,
        bic=(getattr(settings, "company_bic", None) or "").strip() or None,
    )


def _get_buyer_party(invoice: Any) -> CIIParty:
    """Build buyer party from invoice and client (structured address preferred)."""
    client = getattr(invoice, "client", None)
    name = (getattr(invoice, "client_name", None) or "Customer").strip()
    tax_id = None
    address_line = None
    street = None
    city = None
    postcode = None
    email = None
    phone = None
    country = None
    endpoint_id = None
    scheme_id = None

    if client:
        endpoint_id = (client.get_custom_field("peppol_endpoint_id", "") or "").strip() or None
        scheme_id = (client.get_custom_field("peppol_scheme_id", "") or "").strip() or None
        country = (getattr(client, "country", None) or "").strip() or None
        if not country:
            country = (client.get_custom_field("peppol_country", "") or "").strip() or None
        if not country:
            country = (
                client.get_custom_field("country", "") or client.get_custom_field("country_code", "") or ""
            ).strip() or None
        name = (getattr(client, "name", None) or getattr(invoice, "client_name", "") or "Customer").strip()
        tax_id = (getattr(client, "vat_id", None) or "").strip() or None
        if not tax_id:
            tax_id = (
                client.get_custom_field("vat_id", "") or client.get_custom_field("tax_id", "") or ""
            ).strip() or None
        street = (getattr(client, "street", None) or "").strip() or None
        city = (getattr(client, "city", None) or "").strip() or None
        postcode = (getattr(client, "postcode", None) or "").strip() or None
        address_line = street or (
            getattr(client, "address", None) or getattr(invoice, "client_address", None) or ""
        ).strip() or None
        email = (getattr(client, "email", None) or getattr(invoice, "client_email", None) or "").strip() or None
        phone = (getattr(client, "phone", None) or "").strip() or None
    else:
        address_line = (getattr(invoice, "client_address", None) or "").strip() or None
        email = (getattr(invoice, "client_email", None) or "").strip() or None

    return CIIParty(
        name=name,
        tax_id=tax_id,
        address_line=address_line,
        street=street,
        city=city,
        postcode=postcode,
        country_code=country,
        email=email,
        phone=phone,
        endpoint_id=endpoint_id,
        endpoint_scheme_id=scheme_id,
    )


def _pdf_date_now() -> str:
    """Return a PDF date string (D:YYYYMMDDHHmmSS+00'00')."""
    now = datetime.now(timezone.utc)
    return now.strftime("D:%Y%m%d%H%M%S+00'00'")


def _attach_facturx_xml(pdf: Any, cii_bytes: bytes) -> Any:
    """
    Attach factur-x.xml with full PDF/A-3 Associated File structure:
    - Filespec with AFRelationship=/Data, F/UF filename, EF stream
    - Embedded stream with /Subtype /text/xml and /Params (ModDate, Size)
    - Catalog /AF array referencing the filespec
    - Names/EmbeddedFiles name tree (via pdf.attachments)
    """
    from pikepdf import Array, Dictionary, Name, Stream

    mod_date = _pdf_date_now()
    params = Dictionary(
        ModDate=mod_date,
        Size=len(cii_bytes),
    )
    ef_stream = Stream(pdf, cii_bytes)
    ef_stream[Name.Type] = Name.EmbeddedFile
    ef_stream[Name.Subtype] = Name("/text/xml")
    ef_stream[Name.Params] = params

    filespec = Dictionary(
        Type=Name.Filespec,
        F=FACTURX_EMBEDDED_FILENAME,
        UF=FACTURX_EMBEDDED_FILENAME,
        Desc="Factur-X Invoice",
        AFRelationship=Name.Data,
        EF=Dictionary(F=ef_stream, UF=ef_stream),
    )
    filespec_obj = pdf.make_indirect(filespec)

    # Name tree for EmbeddedFiles (also consumed by pdf.attachments)
    try:
        pdf.attachments[FACTURX_EMBEDDED_FILENAME] = filespec_obj
    except Exception:
        # Manual Names tree if attachments API rejects Dictionary
        if "/Names" not in pdf.Root:
            pdf.Root.Names = Dictionary()
        names = pdf.Root.Names
        if "/EmbeddedFiles" not in names:
            names.EmbeddedFiles = Dictionary(Names=Array())
        ef_names = names.EmbeddedFiles
        if "/Names" not in ef_names:
            ef_names.Names = Array()
        name_arr = ef_names.Names
        # Remove existing entry for this filename
        new_arr = Array()
        i = 0
        while i < len(name_arr):
            if str(name_arr[i]) == FACTURX_EMBEDDED_FILENAME:
                i += 2
                continue
            new_arr.append(name_arr[i])
            if i + 1 < len(name_arr):
                new_arr.append(name_arr[i + 1])
            i += 2
        new_arr.append(FACTURX_EMBEDDED_FILENAME)
        new_arr.append(filespec_obj)
        ef_names.Names = new_arr

    # Catalog /AF array (required by PDF/A-3 for associated files)
    try:
        existing_af = pdf.Root.get("/AF")
    except Exception:
        existing_af = None
    if existing_af is None:
        pdf.Root.AF = Array([filespec_obj])
    else:
        # Append if not already present
        af_list = list(existing_af)
        af_list.append(filespec_obj)
        pdf.Root.AF = Array(af_list)

    return filespec_obj


def embed_zugferd_xml_in_pdf(
    pdf_bytes: bytes,
    invoice: Any,
    settings: Any,
    *,
    pdfa3: bool = False,
) -> Tuple[bytes, Optional[str]]:
    """
    Embed Factur-X CII XML into the given invoice PDF bytes.

    Builds seller/buyer from settings and invoice, generates CII XML,
    attaches it as factur-x.xml with full AF structure and Factur-X XMP.
    When pdfa3=True, also adds PDF/A-3b identification and OutputIntent
    in the same pikepdf session.

    Returns:
        (new_pdf_bytes, None) on success, or (original_pdf_bytes, error_message) on failure.
    """
    try:
        import pikepdf
    except ImportError as e:
        return pdf_bytes, f"pikepdf not available: {e}"

    try:
        seller = _get_seller_party(settings)
        buyer = _get_buyer_party(invoice)
        cii_xml, _ = build_cii_invoice_xml(
            invoice=invoice,
            seller=seller,
            buyer=buyer,
            settings=settings,
        )
    except Exception as e:
        return pdf_bytes, f"Failed to build CII XML for Factur-X: {e}"

    try:
        pdf = pikepdf.open(io.BytesIO(pdf_bytes))
        cii_bytes = cii_xml.encode("utf-8")
        _attach_facturx_xml(pdf, cii_bytes)

        # XMP: Factur-X properties + pdfaExtension; PDF/A-3 id when requested
        apply_pdfa3_metadata(pdf, include_facturx=True, pdfa3=pdfa3)
        if pdfa3:
            try:
                apply_output_intent(pdf)
            except Exception:
                pass

        out = io.BytesIO()
        pdf_version = ("1", 7)
        try:
            pdf.save(
                out,
                min_version=pdf_version,
                force_version=pdf_version,
                fix_metadata_version=False,
            )
        except TypeError:
            try:
                pdf.save(out, min_version=pdf_version, fix_metadata_version=False)
            except TypeError:
                pdf.save(out, min_version="1.7")
        pdf.close()
        return out.getvalue(), None
    except Exception as e:
        return pdf_bytes, f"Failed to embed Factur-X CII XML in PDF: {e}"
