"""PDF QR / EPC payload tests."""

from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.utils.pdf_generator_reportlab import build_epc_sepa_qr_payload


def test_build_epc_sepa_qr_payload():
    payload = build_epc_sepa_qr_payload(
        name="Acme GmbH",
        iban="DE89 3704 0044 0532 0130 00",
        amount=Decimal("119.00"),
        remittance="INV-1",
        bic="COBADEFFXXX",
    )
    lines = payload.split("\n")
    assert lines[0] == "BCD"
    assert lines[1] == "002"
    assert lines[4] == "COBADEFFXXX"
    assert lines[5] == "Acme GmbH"
    assert lines[6] == "DE89370400440532013000"
    assert lines[7] == "EUR119.00"
    assert lines[10] == "INV-1"


def test_qr_rendering_smoke():
    pytest.importorskip("reportlab")
    from io import BytesIO

    from reportlab.pdfgen import canvas

    from app.utils.pdf_generator_reportlab import ReportLabTemplateRenderer

    invoice = SimpleNamespace(invoice_number="INV-99", total_amount=Decimal("50.00"))
    settings = SimpleNamespace(company_name="Co", company_iban="DE89370400440532013000", company_bic="")
    data_context = {"invoice": invoice, "settings": settings}
    template = {
        "page": {"size": "A4", "margin": {"top": 20, "right": 20, "bottom": 20, "left": 20}},
        "elements": [
            {
                "type": "qr_code",
                "x": 50,
                "y": 50,
                "width": 80,
                "height": 80,
                "mode": "epc",
            }
        ],
    }
    renderer = ReportLabTemplateRenderer(template, data_context)
    buf = BytesIO()
    canv = canvas.Canvas(buf)
    renderer._draw_qr_code_on_canvas(canv, template["elements"][0], 50, 700, 842)
    canv.save()
    assert buf.getvalue().startswith(b"%PDF")
