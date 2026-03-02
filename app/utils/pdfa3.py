"""
PDF/A-3 conversion and metadata normalization for ZUGFeRD invoices.

Adds PDF/A-3 identification (XMP), output intent (sRGB), and ensures
metadata is present so validators (e.g. veraPDF) can recognize the document.
"""

from __future__ import annotations

import io
from typing import Optional, Tuple

# PDF/A-3 identification namespace (veraPDF / ISO 19005)
PDFA_PART = "3"
PDFA_CONFORMANCE = "B"  # Basic (color allowed)
PDFA_NS = "http://www.pdfa.org/ns/pdfa/1.3/"
RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"

# sRGB output intent (ISO 15076-1); minimal ICC reference for PDF/A-3
OUTPUT_INTENT_SUBTYPE = "GTS_PDFA1"
# Standard sRGB ICC profile ID (PDF/A-3 allows reference by registry)
OUTPUT_INTENT_REGISTRY = "http://www.color.org"
OUTPUT_INTENT_INFO = "sRGB IEC61966-2.1"


def _ensure_pdfa3_xmp(xmp_str: str) -> str:
    """Inject or update PDF/A-3 identification in XMP."""
    pdfa_desc = (
        f'<rdf:Description rdf:about="" xmlns:pdfaid="{PDFA_NS}">'
        f"<pdfaid:part>{PDFA_PART}</pdfaid:part>"
        f"<pdfaid:conformance>{PDFA_CONFORMANCE}</pdfaid:conformance>"
        "</rdf:Description>"
    )
    if "pdfaid:part" in xmp_str and "pdfaid:conformance" in xmp_str:
        return xmp_str
    marker = "</rdf:RDF>"
    if marker in xmp_str:
        insert_pos = xmp_str.rfind(marker)
        return xmp_str[:insert_pos] + pdfa_desc + "\n    " + xmp_str[insert_pos:]
    return xmp_str


def convert_to_pdfa3(pdf_bytes: bytes) -> Tuple[bytes, Optional[str]]:
    """
    Normalize PDF to PDF/A-3 (add identification and output intent).
    Returns (new_pdf_bytes, None) on success, or (original_pdf_bytes, error_message) on failure.
    """
    try:
        import pikepdf
    except ImportError as e:
        return pdf_bytes, f"pikepdf not available: {e}"

    try:
        pdf = pikepdf.open(io.BytesIO(pdf_bytes))
    except Exception as e:
        return pdf_bytes, f"Invalid PDF: {e}"

    try:
        # Ensure metadata stream exists
        if not hasattr(pdf.Root, "Metadata") or pdf.Root.Metadata is None:
            minimal = '<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?><x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"></rdf:RDF></x:xmpmeta><?xpacket end="w"?>'
            pdf.Root.Metadata = pdf.make_stream(minimal.encode("utf-8"))

        xmp_bytes = pdf.Root.Metadata.read_bytes()
        xmp_str = xmp_bytes.decode("utf-8", errors="replace")
        new_xmp = _ensure_pdfa3_xmp(xmp_str)
        pdf.Root.Metadata = pdf.make_stream(new_xmp.encode("utf-8"))

        # Add OutputIntent for PDF/A-3 (required for color)
        try:
            intents = pdf.Root.get("/OutputIntents")
            has_intent = intents is not None and len(intents) > 0
        except Exception:
            has_intent = False
        if not has_intent:
            try:
                from pikepdf import Name, Dictionary, Array
                intent = Dictionary(
                    Type=Name.OutputIntent,
                    S=Name("/GTS_PDFA1"),
                    OutputConditionIdentifier=OUTPUT_INTENT_INFO,
                    Info=OUTPUT_INTENT_INFO,
                    OutputCondition="sRGB IEC61966-2.1",
                )
                pdf.Root.OutputIntents = Array(intent)
            except Exception:
                pass

        out = io.BytesIO()
        # Newer pikepdf requires version as (str, int). Disable metadata version sync to avoid
        # "PDF version must be a tuple" when the doc's internal version is stored as string.
        pdf_version = ("1", 7)
        try:
            pdf.save(
                out,
                min_version=pdf_version,
                force_version=pdf_version,
                fix_metadata_version=False,
            )
        except Exception as ex:
            if "tuple" in str(ex).lower():
                # Fallback: avoid force_version so pikepdf doesn't validate doc version as tuple
                pdf.save(
                    out,
                    min_version=pdf_version,
                    force_version=None,
                    fix_metadata_version=False,
                )
            else:
                raise
        pdf.close()
        return out.getvalue(), None
    except Exception as e:
        try:
            pdf.close()
        except Exception:
            pass
        return pdf_bytes, f"PDF/A-3 conversion failed: {e}"
