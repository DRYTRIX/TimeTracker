"""CSRF protection for the draft invoice page actions (CSRF enabled at create_app time)."""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from factories import ClientFactory, InvoiceFactory, ProjectFactory, TimeEntryFactory
from sqlalchemy.pool import NullPool

from app import db
from app.models import Invoice, TimeEntry
from app.services.invoice_time_service import ON_DRAFT, InvoiceTimeService

pytestmark = [pytest.mark.routes, pytest.mark.integration]


@pytest.fixture
def app_config():
    """Override conftest app_config so CSRF is enabled at create_app time."""
    return {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///pytest_invoice_draft_csrf.sqlite",
        "SQLALCHEMY_ENGINE_OPTIONS": {
            "pool_pre_ping": True,
            "connect_args": {"timeout": 30},
            "poolclass": NullPool,
        },
        "FLASK_ENV": "testing",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "WTF_CSRF_ENABLED": True,
        "WTF_CSRF_SSL_STRICT": False,
        "SECRET_KEY": "test-secret-key-do-not-use-in-production",
        "SERVER_NAME": "localhost:5000",
        "APPLICATION_ROOT": "/",
        "PREFERRED_URL_SCHEME": "http",
        "SESSION_COOKIE_HTTPONLY": True,
        "BABEL_DEFAULT_LOCALE": "en",
    }


def test_draft_actions_without_csrf_token_are_refused(app, authenticated_client, user):
    cl = ClientFactory(name="Draft CSRF Client")
    project = ProjectFactory(name="Draft CSRF Project", client_id=cl.id, hourly_rate=Decimal("40.00"))
    db.session.flush()
    start = datetime(2026, 10, 5, 9, 0)
    entry = TimeEntryFactory(
        user_id=user.id, project_id=project.id, start_time=start, end_time=start + timedelta(hours=2), billable=True
    )
    invoice = InvoiceFactory(project_id=project.id, client_id=cl.id, client_name=cl.name, created_by=user.id)
    invoice.period_start, invoice.period_end = date(2026, 10, 1), date(2026, 10, 31)
    db.session.commit()
    InvoiceTimeService().add_entries(invoice, [entry], "task")
    db.session.commit()
    line = invoice.items.first()

    for url in (
        f"/invoices/{invoice.id}/lines/{line.id}/entries/{entry.id}/remove",
        f"/invoices/{invoice.id}/lines/{line.id}/entries/{entry.id}/non-billable",
        f"/invoices/{invoice.id}/notes-terms",
    ):
        resp = authenticated_client.post(url, data={"notes": "No token"})
        # The app answers a CSRF failure with 400, or a redirect back for a browser form
        assert resp.status_code in (302, 400), url

    db.session.expire_all()
    assert InvoiceTimeService().billing_state(TimeEntry.query.get(entry.id)) == ON_DRAFT
    assert TimeEntry.query.get(entry.id).billable is True
    assert Invoice.query.get(invoice.id).notes != "No token"


def test_draft_action_with_csrf_token_is_accepted(app, authenticated_client, user):
    cl = ClientFactory(name="Draft CSRF Client 2")
    project = ProjectFactory(name="Draft CSRF Project 2", client_id=cl.id, hourly_rate=Decimal("40.00"))
    invoice = InvoiceFactory(project_id=project.id, client_id=cl.id, client_name=cl.name, created_by=user.id)
    db.session.commit()
    token = (authenticated_client.get("/auth/csrf-token").get_json() or {}).get("csrf_token")
    resp = authenticated_client.post(
        f"/invoices/{invoice.id}/notes-terms", data={"notes": "With token", "csrf_token": token}
    )
    assert resp.status_code == 302
    db.session.expire_all()
    assert Invoice.query.get(invoice.id).notes == "With token"
