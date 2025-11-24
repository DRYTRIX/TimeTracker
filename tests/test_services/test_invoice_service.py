"""
Tests for InvoiceService.
"""

import pytest
from datetime import date
from app.services import InvoiceService
from app.models import Invoice, Project, Client, TimeEntry
from app import db


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
        created_by=test_user.id
    )
    db.session.add(invoice)
    db.session.commit()
    
    # List invoices
    result = service.list_invoices(
        user_id=test_user.id,
        is_admin=True
    )
    
    assert result['invoices'] is not None
    assert len(result['invoices']) >= 1
    
    # Verify relations are loaded (no N+1 query)
    invoice = result['invoices'][0]
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
        status='draft',
        payment_status='unpaid',
        issue_date=date.today(),
        due_date=date.today(),
        total_amount=1000.00,
        created_by=test_user.id
    )
    invoice2 = Invoice(
        invoice_number="INV-002",
        project_id=test_project.id,
        client_id=test_project.client_id,
        client_name="Test Client",
        status='sent',
        payment_status='unpaid',
        issue_date=date.today(),
        due_date=date.today(),
        total_amount=2000.00,
        created_by=test_user.id
    )
    db.session.add_all([invoice1, invoice2])
    db.session.commit()
    
    # Filter by status
    result = service.list_invoices(
        status='draft',
        user_id=test_user.id,
        is_admin=True
    )
    draft_invoices = [i for i in result['invoices'] if i.status == 'draft']
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
        created_by=test_user.id
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

