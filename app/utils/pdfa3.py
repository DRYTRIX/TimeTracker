"""
PDF/A-3 conversion helpers for Factur-X / ZUGFeRD invoices.

Provides ICC profile loading, PDF/A-3 XMP identification (including the
pdfaExtension schema declaration for the Factur-X namespace), OutputIntent
creation, and a standalone convert_to_pdfa3() for PDFs that already have
attachments. Prefer the combined embed path in zugferd.py when adding both
Factur-X XML and PDF/A-3 in one pass.
"""

from __future__ import annotations

import io
import os
import struct
from pathlib import Path
from typing import Any, Optional, Tuple

# Bundled sRGB profile (Compact ICC, MIT license — see app/resources/icc/LICENSE if present)
_BUNDLED_SRGB_ICC = Path(__file__).resolve().parent.parent / "resources" / "icc" / "sRGB-v2-nano.icc"

PDFA_PART = "3"
PDFA_CONFORMANCE = "B"
PDFA_NS = "http://www.aiim.org/pdfa/ns/id/"
PDFA_EXTENSION_NS = "http://www.aiim.org/pdfa/ns/extension/"
PDFA_SCHEMA_NS = "http://www.aiim.org/pdfa/ns/schema#"
PDFA_PROPERTY_NS = "http://www.aiim.org/pdfa/ns/property#"
FACTURX_XMP_NS = "urn:factur-x:pdfa:CrossIndustryDocument:invoice:1p0#"
FACTURX_EMBEDDED_FILENAME = "factur-x.xml"

OUTPUT_INTENT_SUBTYPE = "GTS_PDFA1"
OUTPUT_INTENT_REGISTRY = "http://www.color.org"
OUTPUT_INTENT_INFO = "sRGB IEC61966-2.1"


def _srgb_icc_profile_bytes() -> bytes:
    """
    Prefer INVOICE_SRGB_ICC_PATH if set, then bundled nano sRGB ICC, else synthetic minimal profile.
    """
    env_path = (os.environ.get("INVOICE_SRGB_ICC_PATH") or "").strip()
    if env_path:
        try:
            p = Path(env_path)
            if p.is_file():
                return p.read_bytes()
        except OSError:
            pass
    try:
        if _BUNDLED_SRGB_ICC.is_file():
            return _BUNDLED_SRGB_ICC.read_bytes()
    except OSError:
        pass
    return _minimal_srgb_icc_profile()


def _minimal_srgb_icc_profile() -> bytes:
    """
    Build a minimal sRGB ICC profile that satisfies the PDF/A-3 requirement
    for an embedded DestOutputProfile in the OutputIntent.
    """
    header = bytearray(128)
    header[4:8] = b"lcms"
    header[8:12] = struct.pack(">I", 0x02100000)
    header[12:16] = b"mntr"
    header[16:20] = b"RGB "
    header[20:24] = b"XYZ "
    header[24:36] = struct.pack(">6H", 2024, 1, 1, 0, 0, 0)
    header[36:40] = b"acsp"
    header[40:44] = b"MSFT"
    header[64:68] = struct.pack(">I", 0)
    header[68:72] = struct.pack(">i", int(0.9642 * 65536))
    header[72:76] = struct.pack(">i", int(1.0000 * 65536))
    header[76:80] = struct.pack(">i", int(0.8249 * 65536))
    header[80:84] = b"lcms"

    def _xyz_tag(x: float, y: float, z: float) -> bytes:
        return (
            b"XYZ "
            + b"\x00" * 4
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
        data += struct.pack(">I", 0)
        data += struct.pack(">I", 0)
        data += struct.pack(">H", 0) + b"\x00" * 67
        while len(data) % 4 != 0:
            data += b"\x00"
        return data

    def _text_tag(text: str) -> bytes:
        ascii_bytes = text.encode("ascii") + b"\x00"
        data = b"text" + b"\x00" * 4 + ascii_bytes
        while len(data) % 4 != 0:
            data += b"\x00"
        return data

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
    tag_table_size = 4 + tag_count * 12
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
    profile = struct.pack(">I", len(profile)) + profile[4:]
    return profile


def facturx_pdfa_extension_schema_xml() -> str:
    """Return the pdfaExtension:schemas RDF block declaring the fx: namespace properties."""
    return f"""<rdf:Description rdf:about=""
        xmlns:pdfaExtension="{PDFA_EXTENSION_NS}"
        xmlns:pdfaSchema="{PDFA_SCHEMA_NS}"
        xmlns:pdfaProperty="{PDFA_PROPERTY_NS}">
      <pdfaExtension:schemas>
        <rdf:Bag>
          <rdf:li rdf:parseType="Resource">
            <pdfaSchema:schema>Factur-X PDFA Extension Schema</pdfaSchema:schema>
            <pdfaSchema:namespaceURI>{FACTURX_XMP_NS}</pdfaSchema:namespaceURI>
            <pdfaSchema:prefix>fx</pdfaSchema:prefix>
            <pdfaSchema:property>
              <rdf:Seq>
                <rdf:li rdf:parseType="Resource">
                  <pdfaProperty:name>DocumentFileName</pdfaProperty:name>
                  <pdfaProperty:valueType>Text</pdfaProperty:valueType>
                  <pdfaProperty:category>external</pdfaProperty:category>
                  <pdfaProperty:description>Name of the embedded XML invoice file</pdfaProperty:description>
                </rdf:li>
                <rdf:li rdf:parseType="Resource">
                  <pdfaProperty:name>DocumentType</pdfaProperty:name>
                  <pdfaProperty:valueType>Text</pdfaProperty:valueType>
                  <pdfaProperty:category>external</pdfaProperty:category>
                  <pdfaProperty:description>Document type (INVOICE)</pdfaProperty:description>
                </rdf:li>
                <rdf:li rdf:parseType="Resource">
                  <pdfaProperty:name>Version</pdfaProperty:name>
                  <pdfaProperty:valueType>Text</pdfaProperty:valueType>
                  <pdfaProperty:category>external</pdfaProperty:category>
                  <pdfaProperty:description>Factur-X version</pdfaProperty:description>
                </rdf:li>
                <rdf:li rdf:parseType="Resource">
                  <pdfaProperty:name>ConformanceLevel</pdfaProperty:name>
                  <pdfaProperty:valueType>Text</pdfaProperty:valueType>
                  <pdfaProperty:category>external</pdfaProperty:category>
                  <pdfaProperty:description>Factur-X conformance level</pdfaProperty:description>
                </rdf:li>
              </rdf:Seq>
            </pdfaSchema:property>
          </rdf:li>
        </rdf:Bag>
      </pdfaExtension:schemas>
    </rdf:Description>"""


def facturx_rdf_description() -> str:
    """Return the Factur-X XMP RDF description block."""
    return (
        f'<rdf:Description rdf:about="" xmlns:fx="{FACTURX_XMP_NS}">'
        "<fx:DocumentType>INVOICE</fx:DocumentType>"
        f"<fx:DocumentFileName>{FACTURX_EMBEDDED_FILENAME}</fx:DocumentFileName>"
        "<fx:Version>1.0</fx:Version>"
        "<fx:ConformanceLevel>EN 16931</fx:ConformanceLevel>"
        "</rdf:Description>"
    )


def pdfaid_rdf_description() -> str:
    """Return PDF/A identification RDF description."""
    return (
        f'<rdf:Description rdf:about="" xmlns:pdfaid="{PDFA_NS}">'
        f"<pdfaid:part>{PDFA_PART}</pdfaid:part>"
        f"<pdfaid:conformance>{PDFA_CONFORMANCE}</pdfaid:conformance>"
        "</rdf:Description>"
    )


def inject_rdf_descriptions(xmp_str: str, *descriptions: str) -> str:
    """Insert RDF Description blocks before </rdf:RDF> if not already present."""
    result = xmp_str
    for desc in descriptions:
        # Skip if a distinctive fragment of this description is already present
        if "fx:DocumentType" in desc and "fx:DocumentType" in result:
            continue
        if "pdfaid:part" in desc and "pdfaid:part" in result:
            continue
        if "pdfaExtension:schemas" in desc and "pdfaExtension:schemas" in result:
            continue
        marker = "</rdf:RDF>"
        if marker in result:
            insert_pos = result.rfind(marker)
            result = result[:insert_pos] + desc + "\n    " + result[insert_pos:]
    return result


def apply_output_intent(pdf: Any) -> None:
    """Add sRGB OutputIntent with embedded ICC if the catalog has none."""
    from pikepdf import Array, Dictionary, Name, Stream

    try:
        intents = pdf.Root.get("/OutputIntents")
        has_intent = intents is not None and len(intents) > 0
    except Exception:
        has_intent = False

    if has_intent:
        return

    icc_data = _srgb_icc_profile_bytes()
    icc_stream = Stream(pdf, icc_data)
    icc_stream[Name.N] = 3

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


def apply_pdfa3_metadata(
    pdf: Any,
    *,
    include_facturx: bool = False,
    pdfa3: bool = True,
) -> None:
    """
    Ensure PDF has XMP metadata synced with docinfo when possible.

    - pdfa3=True: add PDF/A-3b identification (pdfaid:part/conformance)
    - include_facturx=True: add Factur-X fx: properties and pdfaExtension schema
    """
    # Prefer pikepdf's metadata API so XMP stays in sync with /Info
    try:
        with pdf.open_metadata(set_pikepdf_as_editor=False, update_docinfo=True) as meta:
            if not meta.get("pdf:Producer"):
                meta["pdf:Producer"] = "TimeTracker"
            if not meta.get("xmp:CreatorTool"):
                meta["xmp:CreatorTool"] = "TimeTracker"
    except Exception:
        pass

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

    descriptions = []
    if pdfa3:
        descriptions.append(pdfaid_rdf_description())
    if include_facturx:
        descriptions.append(facturx_rdf_description())
        descriptions.append(facturx_pdfa_extension_schema_xml())

    if not descriptions:
        return

    new_xmp = inject_rdf_descriptions(xmp_str, *descriptions)
    pdf.Root.Metadata = pdf.make_stream(new_xmp.encode("utf-8"))


def _save_pdfa(pdf: Any) -> bytes:
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
            pdf.save(out, min_version=pdf_version, fix_metadata_version=False)
        else:
            raise
    return out.getvalue()


def convert_to_pdfa3(pdf_bytes: bytes) -> Tuple[bytes, Optional[str]]:
    """
    Normalize PDF to PDF/A-3b by adding identification XMP and an output intent
    with an embedded sRGB ICC profile.

    Returns (new_pdf_bytes, None) on success, or (original_pdf_bytes, error_message) on failure.
    """
    try:
        import pikepdf  # noqa: F401
    except ImportError as e:
        return pdf_bytes, f"pikepdf not available: {e}"

    try:
        pdf = pikepdf.open(io.BytesIO(pdf_bytes))
    except Exception as e:
        return pdf_bytes, f"Invalid PDF: {e}"

    try:
        # Detect whether Factur-X metadata / attachment already present
        include_fx = False
        try:
            if hasattr(pdf, "attachments") and FACTURX_EMBEDDED_FILENAME in pdf.attachments:
                include_fx = True
        except Exception:
            pass
        try:
            if hasattr(pdf.Root, "Metadata") and pdf.Root.Metadata is not None:
                existing = pdf.Root.Metadata.read_bytes().decode("utf-8", errors="replace")
                if "fx:DocumentType" in existing or "factur-x" in existing.lower():
                    include_fx = True
        except Exception:
            pass

        apply_pdfa3_metadata(pdf, include_facturx=include_fx)
        try:
            apply_output_intent(pdf)
        except Exception:
            # Fallback without embedded profile
            try:
                from pikepdf import Array, Dictionary, Name

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

        result = _save_pdfa(pdf)
        pdf.close()
        return result, None
    except Exception as e:
        try:
            pdf.close()
        except Exception:
            pass
        return pdf_bytes, f"PDF/A-3 conversion failed: {e}"
