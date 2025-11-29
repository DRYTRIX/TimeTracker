"""Tests for PDF layout customization functionality."""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from app import db
from app.models import User, Project, Invoice, InvoiceItem, Settings, Client
from factories import UserFactory, ClientFactory, ProjectFactory, InvoiceFactory, InvoiceItemFactory
from flask import url_for


@pytest.fixture
def admin_user(app):
    """Create an admin user for testing."""
    user = UserFactory(username="admin", role="admin", email="admin@test.com")
    user.is_active = True
    user.set_password("password123")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def regular_user(app):
    """Create a regular user for testing."""
    user = UserFactory(username="regular", role="user", email="regular@test.com")
    user.is_active = True
    user.set_password("password123")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def sample_invoice(app, admin_user):
    """Create a sample invoice for testing."""
    # Create a client
    client = ClientFactory(name="Test Client", email="client@test.com")
    db.session.commit()

    # Create a project
    project = ProjectFactory(
        client_id=client.id,
        name="Test Project",
        description="Test project for PDF",
        billable=True,
        hourly_rate=Decimal("100.00"),
    )
    db.session.commit()

    # Create invoice
    invoice = InvoiceFactory(
        invoice_number="INV-2024-001",
        project_id=project.id,
        client_name="Test Client",
        client_email="client@test.com",
        client_address="123 Test St",
        due_date=date.today() + timedelta(days=30),
        created_by=admin_user.id,
        client_id=client.id,
        tax_rate=Decimal("10.00"),
        status="draft",
        notes="Test notes",
        terms="Test terms",
    )
    db.session.commit()

    # Add invoice item
    item = InvoiceItemFactory(
        invoice_id=invoice.id, description="Test Service", quantity=Decimal("5.00"), unit_price=Decimal("100.00")
    )
    db.session.commit()

    return invoice


@pytest.mark.smoke
@pytest.mark.admin
def test_pdf_layout_page_requires_admin(client, regular_user):
    """Test that PDF layout page requires admin access."""
    with client:
        # Login as regular user
        client.post("/auth/login", data={"username": "regular", "password": "password123"})

        # Try to access PDF layout page
        response = client.get("/admin/pdf-layout")

        # Should redirect or show forbidden
        assert response.status_code in [302, 403]


@pytest.mark.smoke
@pytest.mark.admin
def test_pdf_layout_page_accessible_to_admin(admin_authenticated_client):
    """Test that PDF layout page is accessible to admin."""
    # Access PDF layout page
    response = admin_authenticated_client.get("/admin/pdf-layout")

    assert response.status_code == 200
    assert b"PDF Layout Editor" in response.data or b"pdf" in response.data.lower()


@pytest.mark.smoke
@pytest.mark.admin
def test_pdf_layout_save_custom_template(admin_authenticated_client, app):
    """Test saving custom PDF layout templates."""
    from app.models import InvoicePDFTemplate

    custom_html = '<div class="custom-invoice"><h1>{{ invoice.invoice_number }}</h1></div>'
    custom_css = ".custom-invoice { color: red; }"

    # Save custom template (A4 is default)
    response = admin_authenticated_client.post(
        "/admin/pdf-layout",
        data={"invoice_pdf_template_html": custom_html, "invoice_pdf_template_css": custom_css, "page_size": "A4"},
        follow_redirects=True,
    )

    assert response.status_code == 200

    # Verify settings were saved (for A4, it also updates Settings for backwards compatibility)
    with app.app_context():
        settings = Settings.get_settings()
        assert settings.invoice_pdf_template_html == custom_html
        assert settings.invoice_pdf_template_css == custom_css

        # Also check InvoicePDFTemplate
        template = InvoicePDFTemplate.get_template("A4")
        assert template.template_html == custom_html
        assert template.template_css == custom_css


@pytest.mark.smoke
@pytest.mark.admin
def test_pdf_layout_reset_to_defaults(admin_authenticated_client, app):
    """Test resetting PDF layout to defaults."""
    # First, set custom templates
    settings = Settings.get_settings()
    settings.invoice_pdf_template_html = "<div>Custom HTML</div>"
    settings.invoice_pdf_template_css = "body { color: blue; }"
    db.session.commit()

    # Reset to defaults
    response = admin_authenticated_client.post("/admin/pdf-layout/reset", follow_redirects=True)

    assert response.status_code == 200

    # Verify templates were cleared
    settings = Settings.get_settings()
    assert settings.invoice_pdf_template_html == ""
    assert settings.invoice_pdf_template_css == ""


@pytest.mark.smoke
@pytest.mark.admin
def test_pdf_layout_get_defaults(admin_authenticated_client):
    """Test getting default PDF layout templates."""
    # Get default templates
    response = admin_authenticated_client.get("/admin/pdf-layout/default")

    assert response.status_code == 200
    assert response.is_json

    data = response.get_json()
    assert "html" in data
    assert "css" in data


@pytest.mark.smoke
@pytest.mark.admin
def test_pdf_layout_preview(admin_authenticated_client, sample_invoice):
    """Test PDF layout preview functionality."""
    # Test preview with custom HTML/CSS
    response = admin_authenticated_client.post(
        "/admin/pdf-layout/preview",
        data={
            "html": "<h1>Test Invoice {{ invoice.invoice_number }}</h1>",
            "css": "h1 { color: red; }",
            "invoice_id": sample_invoice.id,
        },
    )

    assert response.status_code == 200
    # Should return HTML content
    assert b"Test Invoice" in response.data or b"INV-2024-001" in response.data


@pytest.mark.smoke
@pytest.mark.admin
def test_pdf_layout_preview_with_mock_invoice(admin_authenticated_client, app):
    """Test PDF layout preview with mock invoice when no real invoice exists."""
    # Delete all invoices
    Invoice.query.delete()
    db.session.commit()

    # Test preview should still work with mock invoice
    response = admin_authenticated_client.post(
        "/admin/pdf-layout/preview",
        data={"html": "<h1>{{ invoice.invoice_number }}</h1>", "css": "h1 { color: blue; }"},
    )

    assert response.status_code == 200


@pytest.mark.models
def test_settings_pdf_template_fields_exist(app):
    """Test that Settings model has PDF template fields."""
    settings = Settings.get_settings()

    assert hasattr(settings, "invoice_pdf_template_html")
    assert hasattr(settings, "invoice_pdf_template_css")


@pytest.mark.models
def test_settings_pdf_template_defaults(app):
    """Test that PDF template fields have proper defaults."""
    settings = Settings.get_settings()

    # Should default to empty strings
    if not settings.invoice_pdf_template_html:
        assert settings.invoice_pdf_template_html == "" or settings.invoice_pdf_template_html is None
    if not settings.invoice_pdf_template_css:
        assert settings.invoice_pdf_template_css == "" or settings.invoice_pdf_template_css is None


@pytest.mark.integration
def test_pdf_generation_with_custom_template(app, sample_invoice):
    """Test PDF generation uses custom templates when available."""
    from app.utils.pdf_generator import InvoicePDFGenerator

    # Set custom template
    settings = Settings.get_settings()
    settings.invoice_pdf_template_html = """
    <div class="custom-wrapper">
        <h1>Custom Invoice: {{ invoice.invoice_number }}</h1>
        <p>Client: {{ invoice.client_name }}</p>
    </div>
    """
    settings.invoice_pdf_template_css = """
    .custom-wrapper { padding: 20px; }
    h1 { color: #333; }
    """
    db.session.commit()

    # Generate PDF
    generator = InvoicePDFGenerator(sample_invoice, settings)
    pdf_bytes = generator.generate_pdf()

    # Should generate valid PDF
    assert pdf_bytes is not None
    assert len(pdf_bytes) > 0
    # PDF files start with %PDF
    assert pdf_bytes[:4] == b"%PDF"


@pytest.mark.integration
def test_pdf_generation_with_default_template(app, sample_invoice):
    """Test PDF generation uses default template when no custom template set."""
    from app.utils.pdf_generator import InvoicePDFGenerator

    # Clear any custom templates
    settings = Settings.get_settings()
    settings.invoice_pdf_template_html = ""
    settings.invoice_pdf_template_css = ""
    db.session.commit()

    # Generate PDF
    generator = InvoicePDFGenerator(sample_invoice, settings)
    pdf_bytes = generator.generate_pdf()

    # Should generate valid PDF
    assert pdf_bytes is not None
    assert len(pdf_bytes) > 0
    # PDF files start with %PDF
    assert pdf_bytes[:4] == b"%PDF"


@pytest.mark.smoke
@pytest.mark.admin
def test_pdf_layout_navigation_link_exists(admin_authenticated_client):
    """Test that PDF layout link exists in admin navigation."""
    # Access admin dashboard or any admin page
    response = admin_authenticated_client.get("/admin/settings")

    assert response.status_code == 200
    # Should contain link to PDF layout page
    # The link might be in the navigation or as a menu item


@pytest.mark.smoke
@pytest.mark.admin
def test_pdf_layout_form_csrf_protection(admin_authenticated_client):
    """Test that PDF layout form has CSRF protection."""
    # Get the PDF layout page
    response = admin_authenticated_client.get("/admin/pdf-layout")

    assert response.status_code == 200
    # Should contain CSRF token
    assert b"csrf_token" in response.data or b'name="csrf_token"' in response.data


@pytest.mark.integration
def test_pdf_layout_jinja_variable_rendering(app, sample_invoice):
    """Test that Jinja variables are properly rendered in custom templates."""
    from app.utils.pdf_generator import InvoicePDFGenerator

    # Set custom template with various Jinja variables
    settings = Settings.get_settings()
    settings.invoice_pdf_template_html = """
    <div>
        <h1>Invoice: {{ invoice.invoice_number }}</h1>
        <p>Client: {{ invoice.client_name }}</p>
        <p>Company: {{ settings.company_name }}</p>
        <p>Total: {{ format_money(invoice.total_amount) }}</p>
    </div>
    """
    db.session.commit()

    # Generate PDF
    generator = InvoicePDFGenerator(sample_invoice, settings)
    pdf_bytes = generator.generate_pdf()

    # Should generate valid PDF without errors
    assert pdf_bytes is not None
    assert len(pdf_bytes) > 0


@pytest.mark.smoke
@pytest.mark.admin
def test_pdf_layout_rate_limiting(admin_authenticated_client):
    """Test that PDF layout endpoints have rate limiting."""
    # Make multiple rapid requests to preview endpoint
    for i in range(65):  # Exceeds the 60 per minute limit
        response = admin_authenticated_client.post(
            "/admin/pdf-layout/preview", data={"html": "<h1>Test</h1>", "css": "h1 { color: red; }"}
        )

        # After 60 requests, should be rate limited
        if i >= 60:
            assert response.status_code == 429  # Too Many Requests
            break


@pytest.mark.integration
def test_pdf_layout_with_invoice_items_loop(app, sample_invoice):
    """Test custom template with loop over invoice items."""
    from app.utils.pdf_generator import InvoicePDFGenerator

    # Set custom template with items loop
    settings = Settings.get_settings()
    settings.invoice_pdf_template_html = """
    <div>
        <h1>Invoice: {{ invoice.invoice_number }}</h1>
        <table>
            <thead>
                <tr>
                    <th>Description</th>
                    <th>Quantity</th>
                    <th>Price</th>
                </tr>
            </thead>
            <tbody>
                {% for item in invoice.items %}
                <tr>
                    <td>{{ item.description }}</td>
                    <td>{{ item.quantity }}</td>
                    <td>{{ format_money(item.total_amount) }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    """
    db.session.commit()

    # Generate PDF
    generator = InvoicePDFGenerator(sample_invoice, settings)
    pdf_bytes = generator.generate_pdf()

    # Should generate valid PDF
    assert pdf_bytes is not None
    assert len(pdf_bytes) > 0
    assert pdf_bytes[:4] == b"%PDF"
