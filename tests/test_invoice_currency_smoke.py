"""
Smoke tests for invoice currency functionality
Simple high-level tests to ensure the system works end-to-end
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal

from app import db
from app.models import Invoice, Settings
from factories import UserFactory, ClientFactory, ProjectFactory


def _create_invoice_graph(*, username: str, client_name: str, project_name: str, currency: str):
    """Persist user/client/project, then create an Invoice with real FK ids.

    Avoid InvoiceFactory here: its SubFactory + Settings.get_settings() rollback
    interaction can wipe uncommitted rows and trigger SQLite FK failures.
    """
    user = UserFactory(username=username, role="admin", email=f"{username}@example.com")
    db.session.flush()

    client = ClientFactory(name=client_name, email=f"{username}-client@example.com")
    db.session.flush()

    project = ProjectFactory(
        name=project_name,
        client_id=client.id,
        billable=True,
        hourly_rate=Decimal("100.00"),
    )
    project.created_by = user.id
    project.status = "active"
    db.session.flush()

    # Commit graph before touching Settings so a settings create/rollback cannot wipe it
    db.session.commit()

    settings = Settings.query.first() or Settings.get_settings()
    if getattr(settings, "id", None) is None:
        db.session.add(settings)
        db.session.flush()
    settings.currency = currency
    db.session.commit()

    invoice = Invoice(
        invoice_number=f"{username.upper()}-001",
        project_id=project.id,
        client_name=client.name,
        due_date=date.today() + timedelta(days=30),
        created_by=user.id,
        client_id=client.id,
        status="draft",
        currency_code=settings.currency,
        tax_rate=Decimal("20.00"),
    )
    db.session.add(invoice)
    db.session.commit()
    return invoice, settings


@pytest.mark.smoke
def test_invoice_currency_smoke(app):
    """Smoke test: Create invoice and verify it uses settings currency"""
    with app.app_context():
        invoice, settings = _create_invoice_graph(
            username="smokeuser",
            client_name="Smoke Client",
            project_name="Smoke Project",
            currency="CHF",
        )
        assert invoice.currency_code == "CHF", f"Expected CHF but got {invoice.currency_code}"
        assert settings.currency == "CHF"


@pytest.mark.smoke
def test_pdf_generator_uses_settings_currency(app):
    """Smoke test: Verify PDF generator uses settings currency"""
    with app.app_context():
        invoice, settings = _create_invoice_graph(
            username="pdfuser",
            client_name="PDF Client",
            project_name="PDF Project",
            currency="SEK",
        )
        assert invoice.currency_code == settings.currency
        assert settings.currency == "SEK"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
