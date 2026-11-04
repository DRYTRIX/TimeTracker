"""
Tests for InvoiceService.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from app import db
from app.models import Client, Invoice, Project, TimeEntry
from app.services import InvoiceService


@pytest.mark.unit
def test_list_invoices_with_eager_loading(app, test_project, test_user):
    """Test listing invoices with eager loading prevents N+1"""
    service = InvoiceService()

    # Create an invoice
    invoice = Invoice(
        invoice_number="INV-001",
        project_id=test_project.id,
        client_id=test_project.client_id,
        client_name="Test Client",
        issue_date=date.today(),
        due_date=date.today(),
        total_amount=1000.00,
        created_by=test_user.id,
    )
    db.session.add(invoice)
    db.session.commit()

    # List invoices
    result = service.list_invoices(user_id=test_user.id, is_admin=True)

    assert result["invoices"] is not None
    assert len(result["invoices"]) >= 1

    # Verify relations are loaded (no N+1 query)
    invoice = result["invoices"][0]
    assert invoice.project is not None
    assert invoice.client is not None


@pytest.mark.unit
def test_list_invoices_filtering(app, test_project, test_user):
    """Test invoice list filtering"""
    service = InvoiceService()

    # Create invoices with different statuses
    invoice1 = Invoice(
        invoice_number="INV-001",
        project_id=test_project.id,
        client_id=test_project.client_id,
        client_name="Test Client",
        status="draft",
        payment_status="unpaid",
        issue_date=date.today(),
        due_date=date.today(),
        total_amount=1000.00,
        created_by=test_user.id,
    )
    invoice2 = Invoice(
        invoice_number="INV-002",
        project_id=test_project.id,
        client_id=test_project.client_id,
        client_name="Test Client",
        status="sent",
        payment_status="unpaid",
        issue_date=date.today(),
        due_date=date.today(),
        total_amount=2000.00,
        created_by=test_user.id,
    )
    db.session.add_all([invoice1, invoice2])
    db.session.commit()

    # Filter by status
    result = service.list_invoices(status="draft", user_id=test_user.id, is_admin=True)
    draft_invoices = [i for i in result["invoices"] if i.status == "draft"]
    assert len(draft_invoices) >= 1


@pytest.mark.unit
def test_get_invoice_with_details(app, test_project, test_user):
    """Test getting invoice with all details"""
    service = InvoiceService()

    # Create an invoice
    invoice = Invoice(
        invoice_number="INV-001",
        project_id=test_project.id,
        client_id=test_project.client_id,
        client_name="Test Client",
        issue_date=date.today(),
        due_date=date.today(),
        total_amount=1000.00,
        created_by=test_user.id,
    )
    db.session.add(invoice)
    db.session.commit()

    # Get invoice details
    invoice = service.get_invoice_with_details(invoice.id)

    assert invoice is not None
    assert invoice.invoice_number == "INV-001"
    # Verify relations are loaded
    assert invoice.project is not None
    assert invoice.client is not None


@pytest.mark.unit
def test_create_invoice_from_time_entries_with_tax(app, test_project, test_user):
    """Test creating invoice from time entries with tax calculation"""
    from datetime import datetime, timedelta
    from decimal import Decimal

    service = InvoiceService()

    # Create time entries
    entry1 = TimeEntry(
        user_id=test_user.id,
        project_id=test_project.id,
        start_time=datetime.utcnow() - timedelta(hours=2),
        end_time=datetime.utcnow(),
        duration_seconds=7200,  # 2 hours
        billable=True,
    )
    entry2 = TimeEntry(
        user_id=test_user.id,
        project_id=test_project.id,
        start_time=datetime.utcnow() - timedelta(hours=3),
        end_time=datetime.utcnow() - timedelta(hours=1),
        duration_seconds=7200,  # 2 hours
        billable=True,
    )
    db.session.add_all([entry1, entry2])
    db.session.commit()

    # Set project hourly rate
    test_project.hourly_rate = Decimal("50.00")
    db.session.commit()

    result = service.create_invoice_from_time_entries(
        project_id=test_project.id, time_entry_ids=[entry1.id, entry2.id], created_by=test_user.id
    )

    assert result["success"] is True
    assert result["invoice"] is not None
    # 4 hours * 50 = 200
    assert result["invoice"].subtotal == Decimal("200.00")


@pytest.mark.unit
def test_create_invoice_from_time_entries_no_billable(app, test_project, test_user):
    """Test creating invoice from time entries with no billable entries"""
    from datetime import datetime, timedelta

    service = InvoiceService()

    # Create non-billable time entry
    entry = TimeEntry(
        user_id=test_user.id,
        project_id=test_project.id,
        start_time=datetime.utcnow() - timedelta(hours=2),
        end_time=datetime.utcnow(),
        duration_seconds=7200,
        billable=False,  # Not billable
    )
    db.session.add(entry)
    db.session.commit()

    result = service.create_invoice_from_time_entries(
        project_id=test_project.id, time_entry_ids=[entry.id], created_by=test_user.id
    )

    assert result["success"] is False
    assert result["error"] == "no_entries"


@pytest.mark.unit
def test_create_invoice_from_time_entries_invalid_project(app, test_user):
    """Test creating invoice with invalid project"""
    service = InvoiceService()

    result = service.create_invoice_from_time_entries(
        project_id=99999, time_entry_ids=[], created_by=test_user.id  # Non-existent project
    )

    assert result["success"] is False
    assert result["error"] == "invalid_project"


@pytest.mark.unit
def test_mark_invoice_as_sent_updates_time_entries(app, test_project, test_user):
    """Test that marking invoice as sent updates time entries as paid"""
    from datetime import datetime, timedelta
    from decimal import Decimal

    service = InvoiceService()

    # Create time entry
    entry = TimeEntry(
        user_id=test_user.id,
        project_id=test_project.id,
        start_time=datetime.utcnow() - timedelta(hours=2),
        end_time=datetime.utcnow(),
        duration_seconds=7200,
        billable=True,
    )
    db.session.add(entry)
    db.session.commit()

    # Create invoice from time entry
    test_project.hourly_rate = Decimal("50.00")
    db.session.commit()

    result = service.create_invoice_from_time_entries(
        project_id=test_project.id, time_entry_ids=[entry.id], created_by=test_user.id
    )

    assert result["success"] is True
    invoice = result["invoice"]

    # Mark as sent
    result = service.mark_as_sent(invoice.id)
    assert result["success"] is True

    # Refresh entry and check if paid
    db.session.refresh(entry)
    assert entry.paid is True


@pytest.mark.unit
def test_update_invoice_status(app, test_project, test_user):
    """Test updating invoice status"""
    from datetime import date

    service = InvoiceService()

    # Create invoice
    invoice = Invoice(
        invoice_number="INV-001",
        project_id=test_project.id,
        client_id=test_project.client_id,
        client_name="Test Client",
        issue_date=date.today(),
        due_date=date.today(),
        total_amount=1000.00,
        created_by=test_user.id,
        status="draft",
    )
    db.session.add(invoice)
    db.session.commit()

    # Status changes require an explicit allow flag (not mass-assignable)
    result = service.update_invoice(
        invoice_id=invoice.id,
        status="sent",
        user_id=test_user.id,
        _allow_status=True,
    )

    assert result["success"] is True
    db.session.refresh(invoice)
    assert invoice.status == "sent"

    # Without the flag, status in kwargs is ignored
    result = service.update_invoice(
        invoice_id=invoice.id,
        status="paid",
        user_id=test_user.id,
    )
    assert result["success"] is True
    db.session.refresh(invoice)
    assert invoice.status == "sent"


@pytest.mark.unit
def test_create_client_unbilled_invoice_two_projects(app, test_user, test_client, test_project):
    """One draft invoice grouped by project; second call returns no_unbilled_entries."""
    service = InvoiceService()

    p2 = Project(
        name="Second Project",
        client_id=test_client.id,
        description="p2",
        billable=True,
        hourly_rate=Decimal("100.00"),
    )
    p2.status = "active"
    db.session.add(p2)
    db.session.commit()

    start = datetime(2025, 1, 10, 9, 0, 0)
    e1 = TimeEntry(
        user_id=test_user.id,
        project_id=test_project.id,
        start_time=start,
        end_time=start + timedelta(hours=1),
        duration_seconds=3600,
        billable=True,
    )
    e2 = TimeEntry(
        user_id=test_user.id,
        project_id=p2.id,
        start_time=start + timedelta(days=1),
        end_time=start + timedelta(days=1, hours=2),
        duration_seconds=7200,
        billable=True,
    )
    db.session.add_all([e1, e2])
    db.session.commit()

    preview = service.get_client_unbilled_invoice_preview(test_client.id)
    assert preview["entry_count"] == 2
    assert preview["total_hours"] == pytest.approx(3.0)
    assert preview["estimated_total"] == pytest.approx(275.0)

    r1 = service.create_client_unbilled_invoice(test_client.id, acting_user_id=test_user.id)
    assert r1["success"] is True
    assert r1["item_count"] == 2
    inv = Invoice.query.get(r1["invoice_id"])
    assert inv is not None
    assert inv.client_id == test_client.id
    assert inv.project_id == p2.id
    assert len(inv.items.all()) == 2
    assert r1["total"] == pytest.approx(float(inv.total_amount))

    r2 = service.create_client_unbilled_invoice(test_client.id, acting_user_id=test_user.id)
    assert r2["success"] is False
    assert r2["error"] == "no_unbilled_entries"
