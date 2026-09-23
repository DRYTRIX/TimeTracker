"""
Shared Factur-X (ZUGFeRD) embed + PDF/A-3 post-processing for invoice PDFs.

Used by HTTP PDF export and email attachment generation so behavior matches.
Embed and optional PDF/A-3 normalization run in a single pikepdf session.
"""

from __future__ import annotations

from typing import Any, Optional, Tuple


def postprocess_invoice_pdf_bytes(
    pdf_bytes: bytes,
    invoice: Any,
    settings: Any,
) -> Tuple[bytes, Optional[str], Optional[str]]:
    """
    Apply Factur-X CII embedding and optional PDF/A-3 normalization per settings.

    Order: single-pass embed (+ PDF/A-3 when enabled).

    Returns:
        (pdf_bytes, embed_error, pdfa_error)
        - If Factur-X is disabled: returns (pdf_bytes, None, None).
        - On embed failure: returns (original pdf_bytes, error_message, None).
        - On PDF/A failure after successful embed: returns (pdf after embed, None, error_message).
          (With the combined path, PDF/A errors surface as embed errors when pdfa3=True.)
    """
    if not getattr(settings, "invoices_zugferd_pdf", False):
        return pdf_bytes, None, None

    from app.utils.zugferd import embed_zugferd_xml_in_pdf

    want_pdfa3 = bool(getattr(settings, "invoices_pdfa3_compliant", False))
    out_pdf, embed_err = embed_zugferd_xml_in_pdf(
        pdf_bytes, invoice, settings, pdfa3=want_pdfa3
    )
    if embed_err:
        # When pdfa3 was requested, distinguish OutputIntent-style failures if message says so
        if want_pdfa3 and "PDF/A" in (embed_err or ""):
            return out_pdf, None, embed_err
        return out_pdf, embed_err, None

    return out_pdf, None, None
