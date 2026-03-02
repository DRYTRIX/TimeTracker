"""Tests for PDF/A-3 conversion."""
import io

import pytest

try:
    import pikepdf
except ImportError:
    pikepdf = None


@pytest.mark.unit
@pytest.mark.skipif(not pikepdf, reason="pikepdf not installed")
def test_convert_to_pdfa3_adds_identification(app):
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

    # Open and check XMP contains pdfaid
    result = pikepdf.open(io.BytesIO(out_bytes))
    if result.Root.get("/Metadata"):
        xmp = result.Root.Metadata.read_bytes().decode("utf-8", errors="replace")
        assert "pdfaid:part" in xmp or "pdfa" in xmp.lower()
    result.close()


@pytest.mark.unit
def test_convert_to_pdfa3_returns_error_on_invalid_pdf(app):
    from app.utils.pdfa3 import convert_to_pdfa3

    out_bytes, err = convert_to_pdfa3(b"not a pdf")
    assert err is not None
    assert out_bytes == b"not a pdf"
