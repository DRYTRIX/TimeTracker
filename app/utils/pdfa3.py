"""
PDF/A-3 conversion and metadata normalization for Factur-X / ZUGFeRD invoices.

Adds PDF/A-3 identification (XMP), output intent with embedded sRGB ICC
profile, and ensures metadata is present so validators (e.g. veraPDF) can
recognize the document as PDF/A-3b compliant.

Limitations:
- Font subsetting/embedding is the responsibility of the PDF generator
  (WeasyPrint/reportlab). This module only handles metadata and color.
- For full archival compliance, run veraPDF after conversion to catch any
  remaining issues from the source PDF.
"""

from __future__ import annotations

import io
import struct
import zlib
from typing import Optional, Tuple

PDFA_PART = "3"
PDFA_CONFORMANCE = "B"
PDFA_NS = "http://www.aiim.org/pdfa/ns/id/"
RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"

OUTPUT_INTENT_SUBTYPE = "GTS_PDFA1"
OUTPUT_INTENT_REGISTRY = "http://www.color.org"
OUTPUT_INTENT_INFO = "sRGB IEC61966-2.1"


def _minimal_srgb_icc_profile() -> bytes:
    """
    Build a minimal sRGB ICC profile that satisfies the PDF/A-3 requirement
    for an embedded DestOutputProfile in the OutputIntent.

    This is a stripped-down profile based on the sRGB IEC61966-2.1 spec.
    It contains the required header, tag table, and enough data for veraPDF
    to accept it as a valid ICC color profile.
    """
    # ICC profile header (128 bytes)
    header = bytearray(128)
    # Profile size (filled in later)
    # Preferred CMM type
    header[4:8] = b"lcms"
    # Profile version 2.1.0
    header[8:12] = struct.pack(">I", 0x02100000)
    # Device class: mntr (monitor)
    header[12:16] = b"mntr"
    # Color space: RGB
    header[16:20] = b"RGB "
    # PCS: XYZ
    header[20:24] = b"XYZ "
    # Date/time: 2024-01-01 00:00:00
    header[24:36] = struct.pack(">6H", 2024, 1, 1, 0, 0, 0)
    # Signature: acsp
    header[36:40] = b"acsp"
    # Primary platform: MSFT
    header[40:44] = b"MSFT"
    # Rendering intent: perceptual
    header[64:68] = struct.pack(">I", 0)
    # PCS illuminant D50 (X=0.9642, Y=1.0000, Z=0.8249 in s15Fixed16)
    header[68:72] = struct.pack(">i", int(0.9642 * 65536))
    header[72:76] = struct.pack(">i", int(1.0000 * 65536))
    header[76:80] = struct.pack(">i", int(0.8249 * 65536))
    # Creator signature
    header[80:84] = b"lcms"

    # Tag table: desc, wtpt, rXYZ, gXYZ, bXYZ, rTRC, gTRC, bTRC, cprt
    tags = []

    def _xyz_tag(x: float, y: float, z: float) -> bytes:
        return (
            b"XYZ " + b"\x00" * 4
            + struct.pack(">i", int(x * 65536))
            + struct.pack(">i", int(y * 65536))
            + struct.pack(">i", int(z * 65536))
        )

    def _curv_tag_gamma(gamma: float) -> bytes:
        val = int(gamma * 256)
        return b"curv" + b"\x00" * 4 + struct.pack(">I", 1) + struct.pack(">H", val) + b"\x00\x00"

    def _desc_tag(text: str) -> bytes:
        ascii_bytes = text.encode("ascii") + b"\x00"
        data = b"desc" + b"\x00" * 4 + struct.pack(">I", len(ascii_bytes)) + ascii_bytes
        # Unicode and ScriptCode localization (empty)
        data += struct.pack(">I", 0)  # Unicode language code
        data += struct.pack(">I", 0)  # Unicode count
        data += struct.pack(">H", 0) + b"\x00" * 67  # ScriptCode
        while len(data) % 4 != 0:
            data += b"\x00"
        return data

    def _text_tag(text: str) -> bytes:
        ascii_bytes = text.encode("ascii") + b"\x00"
        data = b"text" + b"\x00" * 4 + ascii_bytes
        while len(data) % 4 != 0:
            data += b"\x00"
        return data

    # sRGB approximate values
    desc_data = _desc_tag("sRGB IEC61966-2.1")
    wtpt_data = _xyz_tag(0.9505, 1.0000, 1.0890)
    rXYZ_data = _xyz_tag(0.4124, 0.2126, 0.0193)
    gXYZ_data = _xyz_tag(0.3576, 0.7152, 0.1192)
    bXYZ_data = _xyz_tag(0.1805, 0.0722, 0.9505)
    rTRC_data = _curv_tag_gamma(2.2)
    gTRC_data = _curv_tag_gamma(2.2)
    bTRC_data = _curv_tag_gamma(2.2)
    cprt_data = _text_tag("No copyright, use freely")

    tag_datas = [
        (b"desc", desc_data),
        (b"wtpt", wtpt_data),
        (b"rXYZ", rXYZ_data),
        (b"gXYZ", gXYZ_data),
        (b"bXYZ", bXYZ_data),
        (b"rTRC", rTRC_data),
        (b"gTRC", gTRC_data),
        (b"bTRC", bTRC_data),
        (b"cprt", cprt_data),
    ]

    tag_count = len(tag_datas)
    tag_table_size = 4 + tag_count * 12  # count + entries
    data_offset = 128 + tag_table_size

    tag_table = struct.pack(">I", tag_count)
    payload = b""
    for sig, data in tag_datas:
        offset = data_offset + len(payload)
        tag_table += sig + struct.pack(">II", offset, len(data))
        payload += data
        while len(payload) % 4 != 0:
            payload += b"\x00"

    profile = bytes(header) + tag_table + payload
    # Write profile size into header
    profile = struct.pack(">I", len(profile)) + profile[4:]

    return profile


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
    Normalize PDF to PDF/A-3b by adding identification XMP, an output intent
    with an embedded sRGB ICC profile, and marking info as XMP-only.

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
            minimal = (
                '<?xpacket begin="\xef\xbb\xbf" id="W5M0MpCehiHzreSzNTczkc9d"?>'
                '<x:xmpmeta xmlns:x="adobe:ns:meta/">'
                '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
                "</rdf:RDF></x:xmpmeta>"
                '<?xpacket end="w"?>'
            )
            pdf.Root.Metadata = pdf.make_stream(minimal.encode("utf-8"))

        xmp_bytes = pdf.Root.Metadata.read_bytes()
        xmp_str = xmp_bytes.decode("utf-8", errors="replace")
        new_xmp = _ensure_pdfa3_xmp(xmp_str)
        pdf.Root.Metadata = pdf.make_stream(new_xmp.encode("utf-8"))

        # Add OutputIntent with embedded ICC profile for PDF/A-3
        try:
            intents = pdf.Root.get("/OutputIntents")
            has_intent = intents is not None and len(intents) > 0
        except Exception:
            has_intent = False

        if not has_intent:
            try:
                from pikepdf import Name, Dictionary, Array, Stream

                icc_data = _minimal_srgb_icc_profile()
                icc_stream = Stream(pdf, icc_data)
                icc_stream[Name.N] = 3  # RGB = 3 components

                intent = Dictionary(
                    Type=Name.OutputIntent,
                    S=Name("/GTS_PDFA1"),
                    OutputConditionIdentifier=OUTPUT_INTENT_INFO,
                    Info=OUTPUT_INTENT_INFO,
                    OutputCondition="sRGB IEC61966-2.1",
                    RegistryName=OUTPUT_INTENT_REGISTRY,
                    DestOutputProfile=icc_stream,
                )
                pdf.Root.OutputIntents = Array([intent])
            except Exception:
                # Fallback: intent without embedded profile (less compliant but still useful)
                try:
                    from pikepdf import Name, Dictionary, Array
                    intent = Dictionary(
                        Type=Name.OutputIntent,
                        S=Name("/GTS_PDFA1"),
                        OutputConditionIdentifier=OUTPUT_INTENT_INFO,
                        Info=OUTPUT_INTENT_INFO,
                        OutputCondition="sRGB IEC61966-2.1",
                        RegistryName=OUTPUT_INTENT_REGISTRY,
                    )
                    pdf.Root.OutputIntents = Array([intent])
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
        except Exception as ex:
            if "tuple" in str(ex).lower():
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
