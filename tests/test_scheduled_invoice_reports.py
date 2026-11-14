"""Tests for scheduled invoice report generation."""

import json

import pytest
from factories import UserFactory

from app import db
from app.models.reporting import SavedReportView
from app.services.scheduled_report_service import ScheduledReportService


@pytest.fixture
def invoice_report_view(app):
    with app.app_context():
        user = UserFactory()
        db.session.add(user)
        db.session.commit()

        config = {
            "data_source": "invoices",
            "filters": {},
            "columns": ["invoice_number", "total_amount", "status"],
        }
        view = SavedReportView(
            name="Invoice schedule test",
            owner_id=user.id,
            scope="private",
            config_json=json.dumps(config),
        )
        db.session.add(view)
        db.session.commit()
        yield view, user
        db.session.delete(view)
        db.session.delete(user)
        db.session.commit()


def test_generate_report_data_uses_invoice_data_source(app, invoice_report_view):
    view, user = invoice_report_view
    with app.app_context():
        service = ScheduledReportService()
        config = json.loads(view.config_json)
        data = service._generate_report_data(view, config, user_id=user.id)
        assert data.get("message") != "Invoice reports not yet implemented"
        assert "data" in data


def test_check_overdue_skips_draft_and_paid(app, user, project):
    """Overdue job must not mark draft invoices overdue, and must skip fully paid."""
    from datetime import date, timedelta
    from decimal import Decimal

    from app import db
    from app.models import Invoice
    from app.utils.scheduled_tasks import check_overdue_invoices
    from factories import ClientFactory, InvoiceFactory

    client = ClientFactory(name="Overdue Job Client")
    db.session.commit()
    past = date.today() - timedelta(days=10)

    draft = InvoiceFactory(
        invoice_number="INV-OD-DRAFT",
        project_id=project.id,
        client_id=client.id,
        client_name=client.name,
        created_by=user.id,
        due_date=past,
        total_amount=Decimal("100.00"),
    )
    draft.status = "draft"
    draft.payment_status = "unpaid"

    sent = InvoiceFactory(
        invoice_number="INV-OD-SENT",
        project_id=project.id,
        client_id=client.id,
        client_name=client.name,
        created_by=user.id,
        due_date=past,
        total_amount=Decimal("100.00"),
    )
    sent.status = "sent"
    sent.payment_status = "unpaid"

    paid = InvoiceFactory(
        invoice_number="INV-OD-PAID",
        project_id=project.id,
        client_id=client.id,
        client_name=client.name,
        created_by=user.id,
        due_date=past,
        total_amount=Decimal("100.00"),
    )
    paid.status = "sent"
    paid.payment_status = "fully_paid"
    paid.amount_paid = Decimal("100.00")

    issued = InvoiceFactory(
        invoice_number="INV-OD-ISSUED",
        project_id=project.id,
        client_id=client.id,
        client_name=client.name,
        created_by=user.id,
        due_date=past,
        total_amount=Decimal("100.00"),
    )
    issued.status = "issued"
    issued.payment_status = "unpaid"
    db.session.commit()

    check_overdue_invoices()
    db.session.refresh(draft)
    db.session.refresh(sent)
    db.session.refresh(paid)
    db.session.refresh(issued)

    assert draft.status == "draft"
    assert sent.status == "overdue"
    assert paid.status == "sent"
    assert issued.status == "overdue"
