"""Invoices print and return their own currency.

Invoice PDFs printed Settings.currency for every invoice, so a EUR invoice came out as "USD" when the
global setting was USD. The API accepted currency_code on create but did not return it.
"""

import io

import pytest

from app import db
from app.models import Settings

pytestmark = [pytest.mark.integration]


@pytest.fixture
def eur_invoice(app, invoice_with_items):
    invoice, _items = invoice_with_items
    settings = Settings.get_settings()
    settings.currency = "USD"
    invoice.currency_code = "EUR"
    db.session.commit()
    return invoice


def test_main_generator_uses_invoice_currency(app, eur_invoice):
    from app.utils.pdf_generator import InvoicePDFGenerator

    gen = InvoicePDFGenerator(eur_invoice, settings=Settings.get_settings())
    assert gen._format_currency(1234.5) == "1,234.50 EUR"


def test_fallback_generator_uses_invoice_currency(app, eur_invoice):
    from app.utils.pdf_generator_fallback import InvoicePDFGeneratorFallback

    gen = InvoicePDFGeneratorFallback(eur_invoice, settings=Settings.get_settings())
    assert gen._format_currency(1234.5) == "1,234.50 EUR"


def test_generator_falls_back_to_settings_currency(app, eur_invoice):
    from app.utils.pdf_generator import InvoicePDFGenerator

    class NoCurrency:
        currency_code = None

    gen = InvoicePDFGenerator(eur_invoice, settings=Settings.get_settings())
    gen.invoice = NoCurrency()
    assert gen._format_currency(1) == "1.00 USD"


def test_fallback_pdf_text_has_invoice_currency(app, eur_invoice):
    from pypdf import PdfReader

    from app.utils.pdf_generator_fallback import InvoicePDFGeneratorFallback

    pdf = InvoicePDFGeneratorFallback(eur_invoice, settings=Settings.get_settings()).generate_pdf()
    text = "".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf)).pages)
    assert "EUR" in text
    assert "USD" not in text


@pytest.fixture
def invoices_client(app, user):
    from app.models import ApiToken

    token, plain = ApiToken.create_token(user_id=user.id, name="invoices", scopes="read:invoices", expires_days=1)
    db.session.add(token)
    db.session.commit()
    c = app.test_client()
    c.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {plain}"
    return c


def test_api_returns_invoice_currency(app, invoices_client, eur_invoice):
    resp = invoices_client.get(f"/api/v1/invoices/{eur_invoice.id}")
    assert resp.status_code == 200, resp.get_json()
    data = resp.get_json()
    data = data.get("invoice", data)
    assert data["currency_code"] == "EUR"


def test_to_dict_has_currency(app, eur_invoice):
    assert eur_invoice.to_dict()["currency_code"] == "EUR"
