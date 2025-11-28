import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal

from app import db
from app.models import Client, Project, Invoice, TimeEntry
from factories import TimeEntryFactory, ClientFactory, ProjectFactory, InvoiceFactory


@pytest.mark.smoke
def test_prepaid_hours_summary_display(app, client, user):
    """Smoke test to ensure prepaid hours summary renders on generate-from-time page."""
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
        sess["_fresh"] = True

    prepaid_client = ClientFactory(
        name="Smoke Prepaid", email="smoke@example.com", prepaid_hours_monthly=Decimal("50"), prepaid_reset_day=1
    )
    db.session.commit()

    project = ProjectFactory(
        name="Smoke Project", client_id=prepaid_client.id, billable=True, hourly_rate=Decimal("85.00")
    )
    db.session.commit()

    invoice = InvoiceFactory(
        invoice_number="INV-SMOKE-001",
        project_id=project.id,
        client_name=prepaid_client.name,
        client_id=prepaid_client.id,
        due_date=date.today() + timedelta(days=14),
        created_by=user.id,
        status="draft",
    )
    db.session.commit()

    start = datetime.utcnow() - timedelta(hours=5)
    end = datetime.utcnow()
    TimeEntryFactory(user_id=user.id, project_id=project.id, start_time=start, end_time=end, billable=True)

    response = client.get(f"/invoices/{invoice.id}/generate-from-time")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Prepaid Hours Overview" in html
    assert "Monthly Prepaid Hours" not in html  # ensure we are on the summary, not the form
