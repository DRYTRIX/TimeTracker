"""Defaults of a new invoice from the client's latest invoice: due date and terms (notes have none)."""

from datetime import date, timedelta

import pytest

from app import db
from app.models import BillingEntity, Invoice, Settings
from app.utils import invoice_defaults

pytestmark = [pytest.mark.integration]


def _invoice(project, test_client, user, number, issued, due, terms=None):
    inv = Invoice(
        invoice_number=number,
        project_id=project.id,
        client_id=test_client.id,
        client_name=test_client.name,
        due_date=due,
        created_by=user.id,
        issue_date=issued,
        terms=terms,
    )
    db.session.add(inv)
    db.session.commit()
    return inv


def _entity(terms=None):
    e = BillingEntity(short_name="Seller", legal_name="SELLER LLC", default_terms=terms)
    db.session.add(e)
    db.session.commit()
    return e


def test_due_date_keeps_the_clients_payment_period(app, user, project, test_client):
    _invoice(project, test_client, user, "D-1", date(2026, 11, 1), date(2026, 11, 16))
    assert invoice_defaults.due_date_for(test_client.id, date(2026, 12, 31)) == date(2027, 1, 15)


def test_due_date_follows_the_latest_invoice(app, user, project, test_client):
    _invoice(project, test_client, user, "D-1", date(2026, 10, 1), date(2026, 10, 31))
    _invoice(project, test_client, user, "D-2", date(2026, 11, 1), date(2026, 11, 8))
    assert invoice_defaults.due_days_for(test_client.id) == 7


def test_due_date_for_new_client_is_30_days(app, test_client):
    assert invoice_defaults.due_date_for(test_client.id, date(2026, 12, 31)) == date(2027, 1, 30)
    assert invoice_defaults.due_date_for(None, date(2026, 12, 31)) == date(2027, 1, 30)


def test_terms_from_the_clients_latest_invoice(app, user, project, test_client):
    _invoice(project, test_client, user, "T-1", date(2026, 11, 1), date(2026, 11, 16), terms="Net 15")
    entity = _entity("Entity terms")
    assert invoice_defaults.terms_for(test_client.id, entity, Settings.get_settings()) == "Net 15"


def test_terms_fall_back_to_entity_then_settings(app, user, project, test_client):
    _invoice(project, test_client, user, "T-1", date(2026, 11, 1), date(2026, 11, 16), terms="  ")
    settings = Settings.get_settings()
    settings.invoice_terms = "Settings terms"
    db.session.commit()
    assert invoice_defaults.terms_for(test_client.id, _entity("Entity terms"), settings) == "Entity terms"
    assert invoice_defaults.terms_for(test_client.id, _entity(None), settings) == "Settings terms"
    assert invoice_defaults.terms_for(test_client.id, None, settings) == "Settings terms"


def test_client_defaults_only_for_clients_with_invoices(app, user, project, test_client):
    assert invoice_defaults.client_defaults([test_client.id]) == {}
    _invoice(project, test_client, user, "C-1", date(2026, 11, 1), date(2026, 11, 16), terms="Net 15")
    assert invoice_defaults.client_defaults([test_client.id]) == {
        test_client.id: {"terms": "Net 15", "days": 15, "client": test_client.name}
    }


def test_create_form_due_date_and_hint_data(app, authenticated_client, user, project, test_client):
    _invoice(project, test_client, user, "F-1", date(2026, 11, 1), date(2026, 11, 16), terms="Net 15")
    html = authenticated_client.get(f"/invoices/new?project_id={project.id}").get_data(as_text=True)
    # Issue date: the last day of last month; due 15 days later, as on the client's last invoice
    issue = date.today().replace(day=1) - timedelta(days=1)
    assert f'name="issue_date" id="issue_date" value="{issue.isoformat()}"' in html
    assert f'name="due_date" id="due_date" value="{(issue + timedelta(days=15)).isoformat()}"' in html
    assert '"terms": "Net 15"' in html or '"terms":"Net 15"' in html
    assert f'<option value="{test_client.id}" selected>' in html


def test_create_form_without_invoices_is_30_days(app, authenticated_client, project):
    html = authenticated_client.get(f"/invoices/new?project_id={project.id}").get_data(as_text=True)
    issue = date.today().replace(day=1) - timedelta(days=1)
    assert f'name="due_date" id="due_date" value="{(issue + timedelta(days=30)).isoformat()}"' in html
