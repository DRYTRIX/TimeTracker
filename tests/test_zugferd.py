"""Tests for Factur-X / ZUGFeRD: embedding CII XML in invoice PDFs."""
from datetime import date, timedelta
from decimal import Decimal
import io

import pytest

from app import db
from app.models import Client, Invoice, InvoiceItem, Project, User
from app.utils.zugferd import FACTURX_EMBEDDED_FILENAME, embed_zugferd_xml_in_pdf


@pytest.mark.unit
def test_embed_facturx_xml_in_pdf_adds_cii_attachment(app):
    """Embed step adds factur-x.xml (CII) to PDF with correct structure."""
    try:
        import pikepdf
    except ImportError:
        pytest.skip("pikepdf not installed")

    with app.app_context():
        user = User(username="zugferduser", role="user", email="zugferd@example.com")
        user.is_active = True
        user.set_password("password123")
        db.session.add(user)

        client = Client(name="ZugFerd Client", email="client@example.com", address="Addr 1")
        client.set_custom_field("peppol_endpoint_id", "9915:DE123456789")
        client.set_custom_field("peppol_scheme_id", "9915")
        client.set_custom_field("peppol_country", "DE")
        db.session.add(client)
        db.session.commit()

        project = Project(
            name="ZugFerd Project",
            client_id=client.id,
            billable=True,
            hourly_rate=Decimal("80.00"),
        )
        project.status = "active"
        db.session.add(project)
        db.session.commit()

        inv = Invoice(
            invoice_number="INV-ZUG-001",
            project_id=project.id,
            client_name=client.name,
            client_id=client.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            created_by=user.id,
            currency_code="EUR",
            tax_rate=Decimal("20.00"),
        )
        db.session.add(inv)
        db.session.commit()

        db.session.add(
            InvoiceItem(
                invoice_id=inv.id,
                description="Consulting",
                quantity=Decimal("1"),
                unit_price=Decimal("100.00"),
            )
        )
        db.session.commit()
        inv.calculate_totals()
        db.session.commit()

        settings = __import__("app.models", fromlist=["Settings"]).Settings.get_settings()
        if not getattr(settings, "company_name", None):
            settings.company_name = "Test Company"
        if not getattr(settings, "peppol_sender_endpoint_id", None):
            settings.peppol_sender_endpoint_id = "9915:BE111111111"
        if not getattr(settings, "peppol_sender_scheme_id", None):
            settings.peppol_sender_scheme_id = "9915"
        db.session.commit()

        # Minimal valid PDF (one blank page)
        pdf = pikepdf.Pdf.new()
        pdf.add_blank_page(page_size=(595, 842))
        buf = io.BytesIO()
        pdf.save(buf)
        pdf.close()
        pdf_bytes = buf.getvalue()

        out_bytes, err = embed_zugferd_xml_in_pdf(pdf_bytes, inv, settings)
        assert err is None
        assert len(out_bytes) > len(pdf_bytes)

        result = pikepdf.open(io.BytesIO(out_bytes))
        assert FACTURX_EMBEDDED_FILENAME in result.attachments
        attached = result.attachments[FACTURX_EMBEDDED_FILENAME].get_file()
        xml_content = attached.read_bytes().decode("utf-8")
        result.close()

        # Must be CII (CrossIndustryInvoice), NOT UBL
        assert "CrossIndustryInvoice" in xml_content
        assert "INV-ZUG-001" in xml_content

        # EN 16931 CII requires BilledQuantity with unitCode
        assert "BilledQuantity" in xml_content
        assert 'unitCode="C62"' in xml_content

        # Grand total: 100 + 20% tax = 120
        assert "GrandTotalAmount" in xml_content
        assert "120.00" in xml_content

        # Must contain seller and buyer party names
        assert "ZugFerd Client" in xml_content

        # Must contain the Factur-X guideline ID
        assert "urn:cen.eu:en16931:2017" in xml_content


@pytest.mark.unit
def test_embed_facturx_xml_has_correct_xmp_metadata(app):
    """Embedded PDF has Factur-X XMP metadata (not the old ZUGFeRD CII namespace)."""
    try:
        import pikepdf
    except ImportError:
        pytest.skip("pikepdf not installed")

    with app.app_context():
        from types import SimpleNamespace

        settings = __import__("app.models", fromlist=["Settings"]).Settings.get_settings()
        if not getattr(settings, "company_name", None):
            settings.company_name = "Test Company"
        db.session.commit()

        inv = SimpleNamespace(
            id=1,
            invoice_number="INV-META-001",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=14),
            currency_code="EUR",
            subtotal=Decimal("50.00"),
            tax_rate=Decimal("0"),
            tax_amount=Decimal("0"),
            total_amount=Decimal("50.00"),
            notes=None,
            buyer_reference=None,
            project=None,
            client=None,
            client_name="Buyer",
            client_email=None,
            client_address=None,
            items=[SimpleNamespace(description="Work", quantity=1, unit_price=50, total_amount=50)],
            expenses=[],
            extra_goods=[],
        )

        pdf = pikepdf.Pdf.new()
        pdf.add_blank_page(page_size=(595, 842))
        buf = io.BytesIO()
        pdf.save(buf)
        pdf.close()
        pdf_bytes = buf.getvalue()

        out_bytes, err = embed_zugferd_xml_in_pdf(pdf_bytes, inv, settings)
        assert err is None

        result = pikepdf.open(io.BytesIO(out_bytes))
        xmp = result.Root.Metadata.read_bytes().decode("utf-8", errors="replace")
        result.close()

        # Must use Factur-X namespace, not the old ZUGFeRD CII namespace
        assert "factur-x" in xmp.lower() or "fx:DocumentType" in xmp
        assert "factur-x.xml" in xmp


@pytest.mark.unit
def test_embed_returns_original_pdf_on_failure(app):
    """When embedding fails (e.g. invalid PDF), return original bytes and error message."""
    with app.app_context():
        from types import SimpleNamespace

        settings = __import__("app.models", fromlist=["Settings"]).Settings.get_settings()
        inv = SimpleNamespace(
            id=1,
            invoice_number="INV-X",
            issue_date=date.today(),
            due_date=date.today(),
            currency_code="EUR",
            subtotal=Decimal("0"),
            tax_rate=Decimal("0"),
            tax_amount=Decimal("0"),
            total_amount=Decimal("0"),
            notes=None,
            buyer_reference=None,
            project=None,
            client=None,
            client_name="Test",
            client_email=None,
            client_address=None,
            items=[],
            expenses=[],
            extra_goods=[],
        )
        invalid_pdf_bytes = b"not a valid pdf"

        out_bytes, err = embed_zugferd_xml_in_pdf(invalid_pdf_bytes, inv, settings)
        assert err is not None
        assert out_bytes == invalid_pdf_bytes
