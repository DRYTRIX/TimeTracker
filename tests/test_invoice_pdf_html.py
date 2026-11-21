"""HTML invoice templates: rendering, choosing the template, freezing, admin pages."""

import io
from datetime import date
from decimal import Decimal
from types import SimpleNamespace as NS

import pytest

from app import db
from app.models import Invoice, InvoiceHtmlTemplate, Settings
from app.utils import invoice_pdf_html as ipdf
from app.utils import invoice_templates as it

TEMPLATE = """<!DOCTYPE html><html><head><style>@page { size: A4 }</style></head><body>
<h1>Invoice {{ invoice.invoice_number }}</h1>
<p>{{ seller.name }} / {{ buyer.name }}</p>
{% for row in rows %}<div class="row">{{ row.description }} {{ money(row.total) }}</div>{% endfor %}
<p class="total">{{ currency }} {{ money(total) }}</p>
<pre>{{ payment_details }}</pre>
</body></html>"""


def _invoice(**overrides):
    items = [
        NS(
            id=1,
            position=0,
            description="Consulting",
            quantity=Decimal("1"),
            unit_price=Decimal("16666.66"),
            total_amount=Decimal("16666.66"),
        ),
    ]
    data = dict(
        invoice_number="NW-1",
        issue_date=date(2027, 1, 1),
        due_date=date(2027, 1, 31),
        status="draft",
        client=NS(name="Acme", vat_id="DE1", address=None, email=None, custom_fields={}),
        client_name="Acme",
        client_address="Street 1",
        client_email="a@acme.example",
        items=items,
        extra_goods=[],
        expenses=[],
        subtotal=Decimal("16666.66"),
        tax_rate=Decimal("0"),
        tax_amount=Decimal("0"),
        discount_amount=Decimal("0"),
        total_amount=Decimal("16666.66"),
        currency_code="EUR",
        notes="Purpose",
        terms="Terms",
    )
    data.update(overrides)
    return NS(**data)


def _settings(**overrides):
    data = dict(
        company_name="Northwind LLC",
        company_tax_id="400",
        company_address="1 Example Street",
        company_email="",
        company_phone="",
        company_website="",
        company_bank_info="Bank of Example\nIBAN GE00",
        currency="EUR",
        invoice_terms="",
        has_logo=lambda: False,
        get_logo_path=lambda: None,
        invoice_pdf_template="visual",
    )
    data.update(overrides)
    return NS(**data)


def _make_template(name="mine", html=TEMPLATE):
    tpl = InvoiceHtmlTemplate(name=name, html=html, source="created")
    db.session.add(tpl)
    db.session.flush()
    tpl.save_version()
    db.session.commit()
    return tpl


# ---------------------------------------------------------------------------
# Formatting and rendering
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_formatters():
    assert ipdf.format_amount(Decimal("16666.66")) == "16 666.66"
    assert ipdf.format_amount(None) == "0.00"
    assert ipdf.format_quantity(Decimal("24.50")) == "24.5"
    assert ipdf.format_doc_date(date(2026, 10, 30)) == "30/10/2026"
    assert ipdf.format_doc_date(date(2026, 10, 30), "%d.%m.%Y") == "30.10.2026"
    assert str(ipdf.text_lines("a <b>\nc")) == "a &lt;b&gt;<br>c"
    assert str(ipdf.text_paragraphs("one\n\ntwo\nthree")) == "<p>one</p><p>two<br>three</p>"


@pytest.mark.unit
def test_render_uses_payment_details_and_autoescapes(app):
    with app.app_context():
        html = ipdf.render_invoice_html(TEMPLATE, _invoice(client_name="<script>x</script>"), _settings())
    assert "Invoice NW-1" in html
    assert "EUR 16 666.66" in html
    assert "Bank of Example" in html
    assert "<script>x</script>" not in html


@pytest.mark.unit
def test_invoice_payment_text_wins_over_settings(app):
    with app.app_context():
        html = ipdf.render_invoice_html(TEMPLATE, _invoice(payment_details_text="Pay to account X"), _settings())
    assert "Pay to account X" in html and "Bank of Example" not in html


@pytest.mark.unit
def test_buyer_comes_from_bill_to_snapshot(app):
    snap = {"legal_name": "Acme Europe BV", "vat_number": "NL001", "registration_number": "123", "address": "Amsterdam"}
    with app.app_context():
        buyer = ipdf.build_context(_invoice(buyer_snapshot=snap), _settings())["buyer"]
    assert (buyer.name, buyer.tax_id, buyer.registration_number, buyer.address) == (
        "Acme Europe BV",
        "NL001",
        "123",
        "Amsterdam",
    )


@pytest.mark.unit
def test_sandbox_blocks_python_internals(app):
    with app.app_context(), pytest.raises(ipdf.TemplateError):
        ipdf.render_html_source("{{ ''.__class__.__mro__[1].__subclasses__() }}", {})


@pytest.mark.unit
def test_validate_reports_line_and_hint(app):
    source = "<p>{{ buyer.name }}</p>\n<p>{{ buyer.vat }}</p>"
    with app.app_context(), pytest.raises(ipdf.TemplateError) as err:
        ipdf.validate_template(source, _invoice(), _settings(), build_pdf=False)
    assert err.value.line == 2
    assert "buyer.vat" in err.value.message
    assert err.value.hint == "buyer.tax_id"


@pytest.mark.unit
def test_validate_rejects_syntax_errors_and_big_files(app):
    with app.app_context():
        with pytest.raises(ipdf.TemplateError) as err:
            ipdf.validate_template("<p>\n{% if x %}", _invoice(), _settings(), build_pdf=False)
        assert err.value.line
        with pytest.raises(ipdf.TemplateError):
            ipdf.validate_template("x" * (ipdf.MAX_TEMPLATE_BYTES + 1), _invoice(), _settings(), build_pdf=False)


@pytest.mark.unit
def test_pdf_gets_bundled_fonts_but_not_server_files_or_network(app):
    pytest.importorskip("weasyprint")
    fetcher = ipdf._weasyprint_fetcher_class()()
    font = ipdf.available_fonts()[0]
    assert fetcher.fetch(ipdf.ASSET_BASE + "fonts/" + font).read()[:4]
    for url in ("file:///etc/passwd", "https://example.com/x.css", ipdf.ASSET_BASE + "fonts/../../config.py"):
        with pytest.raises(Exception):
            fetcher.fetch(url)


@pytest.mark.unit
def test_builtin_simple_renders_to_pdf(app):
    pytest.importorskip("weasyprint")
    with app.app_context():
        pdf = ipdf.render_invoice_pdf(it.builtin_source("simple"), _invoice(), _settings())
    assert pdf[:5] == b"%PDF-"


# ---------------------------------------------------------------------------
# Which template, freezing
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_resolution_order(app):
    with app.app_context():
        tpl = _make_template()
        draft = _invoice()
        assert it.resolve_invoice_template(draft, _settings()).is_visual
        assert it.resolve_invoice_template(draft, _settings(invoice_pdf_template=tpl.ref)).ref == tpl.ref
        assert it.resolve_invoice_template(draft, _settings(invoice_pdf_template="builtin:simple")).html
        entity = NS(pdf_template="builtin:simple")
        with_entity = _invoice(billing_entity=entity)
        assert it.resolve_invoice_template(with_entity, _settings(invoice_pdf_template=tpl.ref)).ref == "builtin:simple"
        assert it.resolve_invoice_template(draft, _settings(invoice_pdf_template="html:999999")).is_visual
        # left draft before templates existed: prints as it always did
        old = _invoice(status="paid")
        assert it.resolve_invoice_template(old, _settings(invoice_pdf_template=tpl.ref)).is_visual


@pytest.mark.integration
def test_invoice_freezes_template_and_version_when_leaving_draft(app, invoice_with_items):
    invoice, _ = invoice_with_items
    tpl = _make_template()
    settings = Settings.get_settings()
    settings.invoice_pdf_template = tpl.ref
    db.session.commit()
    first_version = tpl.current_version_id

    invoice = db.session.get(Invoice, invoice.id)
    assert invoice.status == "draft"
    invoice.status = "sent"
    db.session.commit()
    assert invoice.pdf_template_ref == tpl.ref
    assert invoice.pdf_template_version_id == first_version

    tpl.html = TEMPLATE.replace("<h1>", "<h1>CHANGED ")
    tpl.save_version()
    db.session.commit()
    resolved = it.resolve_invoice_template(invoice)
    assert resolved.version_id == first_version
    assert "CHANGED" not in resolved.html


@pytest.mark.integration
def test_delete_switches_users_to_visual_but_keeps_frozen_versions(app, invoice_with_items):
    invoice, _ = invoice_with_items
    tpl = _make_template()
    settings = Settings.get_settings()
    settings.invoice_pdf_template = tpl.ref
    invoice = db.session.get(Invoice, invoice.id)
    invoice.status = "sent"
    db.session.commit()

    it.on_template_deleted(tpl, settings)
    db.session.commit()
    assert settings.invoice_pdf_template == "visual"
    assert tpl.is_deleted
    assert it.resolve_invoice_template(invoice).html == TEMPLATE  # frozen version still prints


@pytest.mark.unit
def test_versions_only_when_html_changes(app):
    with app.app_context():
        tpl = _make_template()
        v1 = tpl.current_version_id
        assert tpl.save_version().id == v1
        tpl.html = TEMPLATE + " "
        assert tpl.save_version().number == 2


@pytest.mark.unit
def test_free_name_adds_number(app):
    with app.app_context():
        _make_template("contract")
        assert InvoiceHtmlTemplate.free_name("contract") == "contract (2)"
        _make_template("contract (2)")
        assert InvoiceHtmlTemplate.free_name("contract") == "contract (3)"


# ---------------------------------------------------------------------------
# Pages and PDF export
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_admin_pages_render(admin_authenticated_client):
    resp = admin_authenticated_client.get("/admin/invoice-templates")
    assert resp.status_code == 200
    assert b"Make your first invoice template" in resp.data
    assert admin_authenticated_client.get("/admin/invoice-templates/new").status_code == 200
    assert admin_authenticated_client.get("/admin/invoice-templates/builtin/simple").status_code == 200
    assert b"Visual layout" in admin_authenticated_client.get("/admin/pdf-layout").data


@pytest.mark.integration
def test_regular_user_cannot_open_templates(authenticated_client):
    resp = authenticated_client.get("/admin/invoice-templates")
    assert resp.status_code in (302, 403)


@pytest.mark.integration
def test_save_blocks_broken_template(admin_authenticated_client, app):
    resp = admin_authenticated_client.post(
        "/admin/invoice-templates/new",
        data={"name": "broken", "html": "<p>{{ buyer.vat }}</p>", "preview_invoice": "sample"},
    )
    assert resp.status_code == 400
    assert b"buyer.tax_id" in resp.data
    with app.app_context():
        assert InvoiceHtmlTemplate.query.filter_by(name="broken").count() == 0


@pytest.mark.integration
def test_create_upload_duplicate_delete(admin_authenticated_client, app):
    resp = admin_authenticated_client.post(
        "/admin/invoice-templates/new", data={"name": "contract", "html": TEMPLATE, "preview_invoice": "sample"}
    )
    assert resp.status_code == 302
    resp = admin_authenticated_client.post(
        "/admin/invoice-templates/upload",
        data={"file": (io.BytesIO(TEMPLATE.encode()), "contract.html")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 302
    with app.app_context():
        names = sorted(t.name for t in InvoiceHtmlTemplate.active().all())
        assert names == ["contract", "contract (2)"]
        tid = InvoiceHtmlTemplate.query.filter_by(name="contract").first().id
    assert admin_authenticated_client.post(f"/admin/invoice-templates/{tid}/duplicate").status_code == 302
    assert admin_authenticated_client.get(f"/admin/invoice-templates/{tid}/download").data == TEMPLATE.encode()
    assert admin_authenticated_client.post(f"/admin/invoice-templates/{tid}/delete").status_code == 302
    with app.app_context():
        assert db.session.get(InvoiceHtmlTemplate, tid).is_deleted


@pytest.mark.integration
def test_preview_returns_html_or_error(admin_authenticated_client):
    ok = admin_authenticated_client.post(
        "/admin/invoice-templates/preview", json={"html": TEMPLATE, "invoice": "sample"}
    )
    assert "SAMPLE-0001" in ok.get_json()["html"]
    bad = admin_authenticated_client.post(
        "/admin/invoice-templates/preview", json={"html": "{{ buyer.vat }}", "invoice": "sample"}
    )
    assert bad.get_json()["hint"] == "buyer.tax_id"


@pytest.mark.integration
def test_export_prints_with_default_html_template(app, authenticated_client, invoice_with_items):
    pytest.importorskip("weasyprint")
    invoice, _ = invoice_with_items
    tpl = _make_template()
    Settings.get_settings().invoice_pdf_template = tpl.ref
    db.session.commit()
    resp = authenticated_client.get(f"/invoices/{invoice.id}/export/pdf")
    assert resp.status_code == 200 and resp.data[:5] == b"%PDF-"
    from pypdf import PdfReader

    text = PdfReader(io.BytesIO(resp.data)).pages[0].extract_text()
    assert invoice.invoice_number in text


@pytest.mark.integration
def test_settings_page_saves_default_template(admin_authenticated_client, app):
    with app.app_context():
        tpl = _make_template()
        ref = tpl.ref
    page = admin_authenticated_client.get("/admin/settings")
    assert b"Default invoice template" in page.data
    assert ref.encode() in page.data


# ---------------------------------------------------------------------------
# Legal entities: own template, logo, preview
# ---------------------------------------------------------------------------


def _png_bytes():
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (40, 20), (79, 70, 229)).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def billing_entity(app):
    from app.models import BillingEntity, PaymentAccount

    entity = BillingEntity(short_name="ACME", legal_name="ACME TRADING LLC", registration_number="123456789")
    db.session.add(entity)
    db.session.flush()
    db.session.add(
        PaymentAccount(
            billing_entity_id=entity.id,
            currency="EUR",
            iban="DE89370400440532013000",
            details_text="JSC CREDO BANK\nAccount: {IBAN}",
        )
    )
    db.session.commit()
    return entity


@pytest.mark.integration
def test_entity_form_saves_template_and_logo(admin_authenticated_client, app, billing_entity):
    tpl = _make_template("contract")
    resp = admin_authenticated_client.post(
        f"/admin/legal-entities/{billing_entity.id}",
        data={"short_name": "ACME", "pdf_template": tpl.ref, "logo": (io.BytesIO(_png_bytes()), "logo.png")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 302
    entity = db.session.get(type(billing_entity), billing_entity.id)
    assert entity.pdf_template == tpl.ref
    assert entity.logo_filename and entity.logo_filename.startswith("entity_logo_")
    assert entity.seller_snapshot()["logo_filename"] == entity.logo_filename
    logo_file = type(entity).logo_path(entity.logo_filename)
    try:
        assert logo_file
        from app.utils.billing_entities import SellerSettings

        seller = SellerSettings(Settings.get_settings(), entity.seller_snapshot(), "", "")
        assert seller.has_logo() and seller.get_logo_path() == logo_file
        assert ipdf.build_context(_invoice(), seller)["seller"].logo == "logo"
    finally:
        import os

        if logo_file and os.path.exists(logo_file):
            os.remove(logo_file)

    page = admin_authenticated_client.get(f"/admin/legal-entities/{entity.id}")
    assert b"Invoice template" in page.data and b"Default (Visual layout)" in page.data

    # unknown template and "Default" both store nothing
    admin_authenticated_client.post(
        f"/admin/legal-entities/{entity.id}", data={"short_name": "ACME", "pdf_template": "html:999999"}
    )
    assert db.session.get(type(entity), entity.id).pdf_template is None


@pytest.mark.integration
def test_entity_rejects_non_image_logo(admin_authenticated_client, app, billing_entity):
    admin_authenticated_client.post(
        f"/admin/legal-entities/{billing_entity.id}",
        data={"short_name": "ACME", "logo": (io.BytesIO(b"not an image"), "logo.png")},
        content_type="multipart/form-data",
    )
    assert db.session.get(type(billing_entity), billing_entity.id).logo_filename is None


@pytest.mark.integration
def test_entity_template_wins_over_settings_and_logo_reaches_the_seller(app, billing_entity, invoice_with_items):
    from app.utils.billing_entities import seller_settings_for

    invoice, _ = invoice_with_items
    default_tpl = _make_template("default")
    own_tpl = _make_template("own", TEMPLATE.replace("<h1>", "<h1>OWN "))
    Settings.get_settings().invoice_pdf_template = default_tpl.ref
    billing_entity.pdf_template = own_tpl.ref
    invoice = db.session.get(Invoice, invoice.id)
    invoice.billing_entity_id = billing_entity.id
    invoice.seller_snapshot = billing_entity.seller_snapshot()
    db.session.commit()

    assert it.resolve_invoice_template(invoice).ref == own_tpl.ref

    billing_entity.pdf_template = None
    db.session.commit()
    assert it.resolve_invoice_template(invoice).ref == default_tpl.ref

    seller = seller_settings_for(invoice, Settings.get_settings())
    assert seller.has_logo() is False  # no logo yet
    assert it.entities_with_own_template() == []


@pytest.mark.integration
def test_deleting_template_moves_entity_to_visual(app, billing_entity):
    tpl = _make_template()
    billing_entity.pdf_template = tpl.ref
    db.session.commit()
    it.on_template_deleted(tpl)
    db.session.commit()
    assert billing_entity.pdf_template == "visual"


@pytest.mark.integration
def test_entity_preview_pdf(admin_authenticated_client, app, billing_entity):
    pytest.importorskip("weasyprint")
    billing_entity.pdf_template = "builtin:simple"
    db.session.commit()
    resp = admin_authenticated_client.get(f"/admin/legal-entities/{billing_entity.id}/preview-pdf")
    assert resp.status_code == 200 and resp.data[:5] == b"%PDF-"
    from pypdf import PdfReader

    text = "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(resp.data)).pages)
    assert "ACME TRADING LLC" in text and "DE89370400440532013000" in text

    # no invoices at all: the Visual layout cannot be previewed on a sample
    resp = admin_authenticated_client.get(f"/admin/legal-entities/{billing_entity.id}/preview-pdf?template=visual")
    assert resp.status_code == 302


@pytest.mark.integration
def test_entity_preview_uses_the_template_in_the_select(
    admin_authenticated_client, app, billing_entity, invoice_with_items
):
    pytest.importorskip("weasyprint")
    from pypdf import PdfReader

    own = _make_template("own", TEMPLATE.replace("<h1>", "<h1>UNSAVED CHOICE "))
    billing_entity.pdf_template = None  # saved: default (visual)
    db.session.commit()
    url = f"/admin/legal-entities/{billing_entity.id}/preview-pdf"

    resp = admin_authenticated_client.get(f"{url}?template={own.ref}")
    text = PdfReader(io.BytesIO(resp.data)).pages[0].extract_text()
    assert "UNSAVED CHOICE" in text and "ACME TRADING LLC" in text and "DE89370400440532013000" in text

    visual = admin_authenticated_client.get(f"{url}?template=visual")
    assert visual.status_code == 200 and visual.data[:5] == b"%PDF-"
    assert "UNSAVED CHOICE" not in PdfReader(io.BytesIO(visual.data)).pages[0].extract_text()
