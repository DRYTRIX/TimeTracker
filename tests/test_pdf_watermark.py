"""Tests for the optional 'Generated with TimeTracker' PDF watermark."""

from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app import db
from app.models import Invoice, InvoiceItem, Settings
from app.utils.pdf_watermark import (
    make_page_callback,
    should_draw_watermark,
)
from app.utils.summary_report_pdf import build_summary_report_pdf
from app.utils.time_entries_pdf import build_time_entries_pdf
from factories import ClientFactory, ProjectFactory, UserFactory


# ReportLab compresses page content streams; the clickable link URL is stored
# uncompressed and is a reliable presence marker for the watermark.
WATERMARK_MARKER = b"timetracker.drytrix.com"


@pytest.mark.unit
def test_should_draw_watermark_unlicensed():
    assert should_draw_watermark(SimpleNamespace(donate_ui_hidden=False)) is True


@pytest.mark.unit
def test_should_draw_watermark_licensed():
    assert should_draw_watermark(SimpleNamespace(donate_ui_hidden=True)) is False


@pytest.mark.unit
def test_should_draw_watermark_missing_attr():
    # Missing attribute treated as not activated → watermark shown
    assert should_draw_watermark(SimpleNamespace()) is True


@pytest.mark.unit
def test_make_page_callback_calls_existing_then_watermark():
    calls = []

    def existing(canv, doc):
        calls.append("existing")

    class FakeCanv:
        def saveState(self):
            calls.append("save")

        def restoreState(self):
            calls.append("restore")

        def setFont(self, *a, **k):
            pass

        def setFillColor(self, *a, **k):
            pass

        def drawString(self, *a, **k):
            calls.append("draw")

        def stringWidth(self, *a, **k):
            return 100

        def linkURL(self, *a, **k):
            calls.append("link")

    cb = make_page_callback(existing, enabled=True)
    cb(FakeCanv(), SimpleNamespace())
    assert calls == ["existing", "save", "draw", "link", "restore"]

    calls.clear()
    cb_off = make_page_callback(existing, enabled=False)
    cb_off(FakeCanv(), SimpleNamespace())
    assert calls == ["existing"]


def _set_license(activated: bool) -> Settings:
    settings = Settings.get_settings()
    settings.donate_ui_hidden = activated
    db.session.commit()
    return settings


@pytest.mark.integration
def test_summary_report_pdf_includes_watermark_when_unlicensed(app):
    with app.app_context():
        _set_license(False)
        pdf_bytes = build_summary_report_pdf(1.5, 8.0, 32.0, [])
        assert pdf_bytes[:4] == b"%PDF"
        assert WATERMARK_MARKER in pdf_bytes


@pytest.mark.integration
def test_summary_report_pdf_omits_watermark_when_licensed(app):
    with app.app_context():
        _set_license(True)
        pdf_bytes = build_summary_report_pdf(1.5, 8.0, 32.0, [])
        assert pdf_bytes[:4] == b"%PDF"
        assert WATERMARK_MARKER not in pdf_bytes


@pytest.mark.integration
def test_time_entries_pdf_includes_watermark_when_unlicensed(app):
    with app.app_context():
        _set_license(False)
        pdf_bytes = build_time_entries_pdf([])
        assert pdf_bytes[:4] == b"%PDF"
        assert WATERMARK_MARKER in pdf_bytes


@pytest.mark.integration
def test_time_entries_pdf_omits_watermark_when_licensed(app):
    with app.app_context():
        _set_license(True)
        pdf_bytes = build_time_entries_pdf([])
        assert pdf_bytes[:4] == b"%PDF"
        assert WATERMARK_MARKER not in pdf_bytes


@pytest.mark.integration
def test_invoice_fallback_pdf_watermark_respects_license(app):
    """Fallback invoice generator shows watermark only when unlicensed."""
    from app.utils.pdf_generator_fallback import InvoicePDFGeneratorFallback

    with app.app_context():
        user = UserFactory(username="wmuser", role="admin", email="wm@example.com")
        db.session.flush()
        client = ClientFactory(name="Watermark Client")
        db.session.flush()
        project = ProjectFactory(name="WM Project", client_id=client.id)
        project.created_by = user.id
        db.session.commit()

        invoice = Invoice(
            invoice_number="WM-001",
            project_id=project.id,
            client_name=client.name,
            client_id=client.id,
            due_date=date.today() + timedelta(days=30),
            tax_rate=Decimal("0.00"),
            created_by=user.id,
        )
        db.session.add(invoice)
        db.session.flush()
        db.session.add(
            InvoiceItem(
                invoice_id=invoice.id,
                description="Work",
                quantity=Decimal("1.00"),
                unit_price=Decimal("100.00"),
            )
        )
        invoice.calculate_totals()
        db.session.commit()

        _set_license(False)
        pdf_unlicensed = InvoicePDFGeneratorFallback(invoice).generate_pdf()
        assert WATERMARK_MARKER in pdf_unlicensed

        _set_license(True)
        pdf_licensed = InvoicePDFGeneratorFallback(invoice).generate_pdf()
        assert WATERMARK_MARKER not in pdf_licensed
