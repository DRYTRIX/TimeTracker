"""Choosing an invoice's currency in the create and edit forms.

The create form offers a Currency select. It defaults to the currency of the client's latest invoice,
else Settings.currency. A draft invoice can change its currency in the edit form; a sent or paid one
cannot.
"""

import pytest

from app import db
from app.models import Settings

pytestmark = [pytest.mark.integration]


def _create_form(project, test_client, **extra):
    from datetime import date, timedelta

    data = {
        "project_id": project.id,
        "client_name": test_client.name,
        "due_date": (date.today() + timedelta(days=30)).strftime("%Y-%m-%d"),
        "tax_rate": "0",
    }
    data.update(extra)
    return data


def _usd_settings():
    settings = Settings.get_settings()
    settings.currency = "USD"
    db.session.commit()


def _newest_invoice():
    from app.models import Invoice

    return Invoice.query.order_by(Invoice.id.desc()).first()


def test_create_form_offers_currency_select(app, authenticated_client, project):
    _usd_settings()
    resp = authenticated_client.get("/invoices/create")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert 'name="currency_code"' in html
    assert 'data-currency="USD"' in html  # project option carries its client's default currency


def test_create_uses_chosen_currency(app, authenticated_client, project, test_client):
    _usd_settings()
    resp = authenticated_client.post("/invoices/create", data=_create_form(project, test_client, currency_code="eur"))
    assert resp.status_code in (200, 302)
    assert _newest_invoice().currency_code == "EUR"


def test_create_defaults_to_clients_latest_invoice_currency(app, authenticated_client, project, test_client, invoice):
    _usd_settings()
    invoice.currency_code = "RUB"
    db.session.commit()
    authenticated_client.post("/invoices/create", data=_create_form(project, test_client))
    newest = _newest_invoice()
    assert newest.id != invoice.id
    assert newest.currency_code == "RUB"


def test_create_without_history_uses_settings_currency(app, authenticated_client, project, test_client):
    _usd_settings()
    authenticated_client.post("/invoices/create", data=_create_form(project, test_client, currency_code="bad!"))
    assert _newest_invoice().currency_code == "USD"


def test_edit_draft_changes_currency(app, authenticated_client, invoice):
    _usd_settings()
    resp = authenticated_client.get(f"/invoices/{invoice.id}/edit")
    assert 'name="currency_code"' in resp.get_data(as_text=True)
    authenticated_client.post(
        f"/invoices/{invoice.id}/edit",
        data={
            "client_name": invoice.client_name,
            "due_date": invoice.due_date.strftime("%Y-%m-%d"),
            "tax_rate": "0",
            "currency_code": "GEL",
        },
    )
    db.session.refresh(invoice)
    assert invoice.currency_code == "GEL"


def test_edit_sent_invoice_keeps_currency(app, authenticated_client, invoice):
    invoice.status = "sent"
    invoice.currency_code = "EUR"
    db.session.commit()
    resp = authenticated_client.get(f"/invoices/{invoice.id}/edit")
    assert 'name="currency_code"' not in resp.get_data(as_text=True)
    authenticated_client.post(
        f"/invoices/{invoice.id}/edit",
        data={"due_date": invoice.due_date.strftime("%Y-%m-%d"), "notes": "x", "currency_code": "USD"},
    )
    db.session.refresh(invoice)
    assert invoice.currency_code == "EUR"


def test_currency_helpers(app, invoice):
    from app.utils.invoice_currency import (
        currency_choices,
        default_currencies_by_client,
        default_currency_for_client,
        normalize_currency_code,
    )

    assert normalize_currency_code(" eur ") == "EUR"
    assert normalize_currency_code("euro") is None
    invoice.currency_code = "RUB"
    db.session.commit()
    settings = Settings.get_settings()
    assert default_currency_for_client(invoice.client_id, settings) == "RUB"
    assert default_currencies_by_client(settings)[invoice.client_id] == "RUB"
    assert "RUB" in currency_choices(settings)
