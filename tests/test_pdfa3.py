"""Tests for PDF/A-3 conversion with ICC profile embedding."""
import io

import pytest

try:
    import pikepdf
except ImportError:
    pikepdf = None


@pytest.mark.unit
@pytest.mark.skipif(not pikepdf, reason="pikepdf not installed")
def test_convert_to_pdfa3_adds_identification(app):
    """PDF/A-3 conversion adds XMP pdfaid identification."""
    from app.utils.pdfa3 import convert_to_pdfa3

    pdf = pikepdf.Pdf.new()
    pdf.add_blank_page(page_size=(595, 842))
    buf = io.BytesIO()
    pdf.save(buf)
    pdf.close()
    pdf_bytes = buf.getvalue()

    out_bytes, err = convert_to_pdfa3(pdf_bytes)
    assert err is None
    assert len(out_bytes) >= len(pdf_bytes)

    result = pikepdf.open(io.BytesIO(out_bytes))
    assert result.Root.get("/Metadata") is not None
    xmp = result.Root.Metadata.read_bytes().decode("utf-8", errors="replace")
    assert "pdfaid:part" in xmp
    assert ">3<" in xmp or "3</pdfaid:part>" in xmp
    assert "pdfaid:conformance" in xmp
    result.close()


@pytest.mark.unit
@pytest.mark.skipif(not pikepdf, reason="pikepdf not installed")
def test_convert_to_pdfa3_adds_output_intent(app):
    """PDF/A-3 conversion adds an OutputIntent with ICC profile reference."""
    from app.utils.pdfa3 import convert_to_pdfa3

    pdf = pikepdf.Pdf.new()
    pdf.add_blank_page(page_size=(595, 842))
    buf = io.BytesIO()
    pdf.save(buf)
    pdf.close()
    pdf_bytes = buf.getvalue()

    out_bytes, err = convert_to_pdfa3(pdf_bytes)
    assert err is None

    result = pikepdf.open(io.BytesIO(out_bytes))
    intents = result.Root.get("/OutputIntents")
    assert intents is not None
    assert len(intents) > 0
    intent = intents[0]
    assert str(intent.get("/S")) == "/GTS_PDFA1"
    # Check that DestOutputProfile (ICC stream) is present
    dest_profile = intent.get("/DestOutputProfile")
    assert dest_profile is not None, "OutputIntent should contain an embedded ICC profile"
    result.close()


@pytest.mark.unit
@pytest.mark.skipif(not pikepdf, reason="pikepdf not installed")
def test_convert_to_pdfa3_icc_profile_is_valid(app):
    """The embedded ICC profile has the correct signature and structure."""
    from app.utils.pdfa3 import convert_to_pdfa3
    import struct

    pdf = pikepdf.Pdf.new()
    pdf.add_blank_page(page_size=(595, 842))
    buf = io.BytesIO()
    pdf.save(buf)
    pdf.close()
    pdf_bytes = buf.getvalue()

    out_bytes, err = convert_to_pdfa3(pdf_bytes)
    assert err is None

    result = pikepdf.open(io.BytesIO(out_bytes))
    intent = result.Root.OutputIntents[0]
    icc_stream = intent.DestOutputProfile
    icc_data = icc_stream.read_bytes()
    result.close()

    # ICC profile must be at least 128 bytes (header size)
    assert len(icc_data) >= 128

    # Profile size in header must match actual size
    profile_size = struct.unpack(">I", icc_data[:4])[0]
    assert profile_size == len(icc_data)

    # Signature must be 'acsp' at offset 36
    assert icc_data[36:40] == b"acsp"

    # Color space must be 'RGB '
    assert icc_data[16:20] == b"RGB "


@pytest.mark.unit
@pytest.mark.skipif(not pikepdf, reason="pikepdf not installed")
def test_convert_to_pdfa3_preserves_existing_xmp(app):
    """Conversion preserves existing XMP metadata while adding PDF/A-3 identification."""
    from app.utils.pdfa3 import convert_to_pdfa3

    pdf = pikepdf.Pdf.new()
    pdf.add_blank_page(page_size=(595, 842))
    existing_xmp = (
        '<?xpacket begin="\xef\xbb\xbf" id="W5M0MpCehiHzreSzNTczkc9d"?>'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">'
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
        '<rdf:Description rdf:about="" xmlns:dc="http://purl.org/dc/elements/1.1/">'
        "<dc:title>Test Invoice</dc:title>"
        "</rdf:Description>"
        "</rdf:RDF></x:xmpmeta>"
        '<?xpacket end="w"?>'
    )
    pdf.Root.Metadata = pdf.make_stream(existing_xmp.encode("utf-8"))
    buf = io.BytesIO()
    pdf.save(buf)
    pdf.close()

    out_bytes, err = convert_to_pdfa3(buf.getvalue())
    assert err is None

    result = pikepdf.open(io.BytesIO(out_bytes))
    xmp = result.Root.Metadata.read_bytes().decode("utf-8", errors="replace")
    result.close()

    assert "pdfaid:part" in xmp
    assert "dc:title" in xmp, "Existing XMP metadata should be preserved"


@pytest.mark.unit
def test_convert_to_pdfa3_returns_error_on_invalid_pdf(app):
    from app.utils.pdfa3 import convert_to_pdfa3

    out_bytes, err = convert_to_pdfa3(b"not a pdf")
    assert err is not None
    assert out_bytes == b"not a pdf"
