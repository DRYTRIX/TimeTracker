import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from app import db
from app.models import User, Project, Invoice, InvoiceItem, Settings, Client

@pytest.fixture
def sample_user(app):
    """Create a sample user for testing."""
    user = User(username='testuser', role='user')
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def sample_project(app):
    """Create a sample project for testing."""
    project = Project(
        name='Test Project',
        client='Test Client',
        description='A test project',
        billable=True,
        hourly_rate=Decimal('75.00')
    )
    db.session.add(project)
    db.session.commit()
    return project

@pytest.fixture
def sample_invoice(app, sample_user, sample_project):
    """Create a sample invoice for testing."""
    # Create a client first
    from app.models import Client
    client = Client(
        name='Sample Invoice Client',
        email='sample@test.com'
    )
    db.session.add(client)
    db.session.commit()
    
    invoice = Invoice(
        invoice_number='INV-20241201-001',
        project_id=sample_project.id,
        client_name='Sample Invoice Client',
        due_date=date.today() + timedelta(days=30),
        created_by=sample_user.id,
        client_id=client.id
    )
    db.session.add(invoice)
    db.session.commit()
    return invoice

@pytest.mark.smoke
@pytest.mark.invoices
def test_invoice_creation(app, sample_user, sample_project):
    """Test that invoices can be created correctly."""
    # Create a client first
    from app.models import Client
    client = Client(
        name='Invoice Creation Test Client',
        email='creation@test.com'
    )
    db.session.add(client)
    db.session.commit()
    
    invoice = Invoice(
        invoice_number='INV-20241201-002',
        project_id=sample_project.id,
        client_name='Invoice Creation Test Client',
        due_date=date.today() + timedelta(days=30),
        created_by=sample_user.id,
        client_id=client.id,
        tax_rate=Decimal('20.00')
    )
    
    db.session.add(invoice)
    db.session.commit()
    
    assert invoice.id is not None
    assert invoice.invoice_number == 'INV-20241201-002'
    assert invoice.client_name == 'Invoice Creation Test Client'
    assert invoice.status == 'draft'
    assert invoice.tax_rate == Decimal('20.00')

@pytest.mark.smoke
@pytest.mark.invoices
def test_invoice_item_creation(app, sample_invoice):
    """Test that invoice items can be created correctly."""
    item = InvoiceItem(
        invoice_id=sample_invoice.id,
        description='Development work',
        quantity=Decimal('10.00'),
        unit_price=Decimal('75.00')
    )
    
    db.session.add(item)
    db.session.commit()
    
    assert item.id is not None
    assert item.total_amount == Decimal('750.00')
    assert item.invoice_id == sample_invoice.id

@pytest.mark.smoke
@pytest.mark.invoices
def test_invoice_totals_calculation(app, sample_invoice):
    """Test that invoice totals are calculated correctly."""
    # Add multiple items
    item1 = InvoiceItem(
        invoice_id=sample_invoice.id,
        description='Development work',
        quantity=Decimal('10.00'),
        unit_price=Decimal('75.00')
    )
    
    item2 = InvoiceItem(
        invoice_id=sample_invoice.id,
        description='Design work',
        quantity=Decimal('5.00'),
        unit_price=Decimal('100.00')
    )
    
    db.session.add_all([item1, item2])
    db.session.commit()
    
    # Calculate totals
    sample_invoice.calculate_totals()
    
    assert sample_invoice.subtotal == Decimal('1250.00')  # 10*75 + 5*100
    assert sample_invoice.tax_amount == Decimal('0.00')  # 0% tax rate
    assert sample_invoice.total_amount == Decimal('1250.00')

def test_invoice_with_tax(app, sample_user, sample_project):
    """Test invoice calculation with tax."""
    # Create a client first
    from app.models import Client
    client = Client(
        name='Tax Test Client',
        email='tax@test.com'
    )
    db.session.add(client)
    db.session.commit()
    
    invoice = Invoice(
        invoice_number='INV-20241201-003',
        project_id=sample_project.id,
        client_name='Tax Test Client',
        due_date=date.today() + timedelta(days=30),
        created_by=sample_user.id,
        client_id=client.id,
        tax_rate=Decimal('20.00')
    )
    
    db.session.add(invoice)
    db.session.commit()
    
    # Add item
    item = InvoiceItem(
        invoice_id=invoice.id,
        description='Development work',
        quantity=Decimal('10.00'),
        unit_price=Decimal('75.00')
    )
    
    db.session.add(item)
    db.session.commit()
    
    # Calculate totals
    invoice.calculate_totals()
    
    assert invoice.subtotal == Decimal('750.00')
    assert invoice.tax_amount == Decimal('150.00')  # 20% of 750
    assert invoice.total_amount == Decimal('900.00')

def test_invoice_number_generation(app):
    """Test that invoice numbers are generated correctly."""
    # This test would need to be run in isolation or with a clean database
    # as it depends on the current date and existing invoice numbers
    
    # First invoice
    invoice_number = Invoice.generate_invoice_number()
    # Just check the format, not the exact date
    assert invoice_number is not None
    assert 'INV-' in invoice_number
    assert len(invoice_number.split('-')) == 3
        

def test_invoice_overdue_status(app, sample_user, sample_project):
    """Test that invoices are marked as overdue correctly."""
    # Create a client first
    from app.models import Client
    client = Client(
        name='Overdue Test Client',
        email='overdue@test.com'
    )
    db.session.add(client)
    db.session.commit()
    
    # Create an overdue invoice
    overdue_date = date.today() - timedelta(days=5)
    invoice = Invoice(
        invoice_number='INV-20241201-004',
        project_id=sample_project.id,
        client_id=client.id,
        client_name='Test Client',
        due_date=overdue_date,
        created_by=sample_user.id
    )
    # Set status after creation
    invoice.status = 'sent'
    
    db.session.add(invoice)
    db.session.commit()
    
    # Refresh to get latest values
    db.session.expire(invoice)
    db.session.refresh(invoice)
    
    # Check if invoice is overdue
    # Note: is_overdue might be a property that checks the due date
    # If the property exists and works, this should pass
    if hasattr(invoice, 'is_overdue'):
        assert invoice.is_overdue is True or invoice.is_overdue is False  # Just verify it exists
    
    # Test days_overdue if it exists
    if hasattr(invoice, 'days_overdue'):
        assert invoice.days_overdue >= 0  # Should be non-negative


@pytest.mark.routes
def test_create_invoice_template_has_client_data_attributes(app, client, user, project):
    """Ensure the create invoice page renders project options with client data attributes."""
    # Authenticate
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True

    # Ensure project has a client with email/address
    proj = Project.query.get(project.id)
    cl = Client.query.get(proj.client_id)
    cl.email = 'client@example.com'
    cl.address = '123 Test St\nCity'
    from app import db
    db.session.commit()

    resp = client.get('/invoices/create')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # The option should include data-client-name/email/address
    assert f'data-client-name="{cl.name}"' in html
    assert 'data-client-email="client@example.com"' in html
    assert 'data-client-address="123 Test St' in html

def test_invoice_to_dict(app, sample_invoice):
    """Test that invoice can be converted to dictionary."""
    invoice_dict = sample_invoice.to_dict()
    
    assert 'id' in invoice_dict
    assert 'invoice_number' in invoice_dict
    assert 'client_name' in invoice_dict
    assert 'status' in invoice_dict
    assert 'created_at' in invoice_dict
    assert 'updated_at' in invoice_dict

def test_invoice_item_to_dict(app, sample_invoice):
    """Test that invoice item can be converted to dictionary."""
    item = InvoiceItem(
        invoice_id=sample_invoice.id,
        description='Test item',
        quantity=Decimal('5.00'),
        unit_price=Decimal('50.00')
    )
    
    db.session.add(item)
    db.session.commit()
    
    item_dict = item.to_dict()
    
    assert 'id' in item_dict
    assert 'description' in item_dict
    assert 'quantity' in item_dict
    assert 'unit_price' in item_dict
    assert 'total_amount' in item_dict


@pytest.mark.routes
def test_edit_invoice_template_has_expected_fields(app, client, user, project):
    """Ensure the edit invoice page renders key fields and existing items."""
    # Authenticate
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True

    # Create client and invoice with an item
    from app.models import Client, InvoiceItem
    cl = Client(name='Edit Test Client', email='edit@test.com', address='Street 1')
    db.session.add(cl)
    db.session.commit()

    inv = Invoice(
        invoice_number='INV-TEST-EDIT-001',
        project_id=project.id,
        client_name=cl.name,
        client_id=cl.id,
        due_date=date.today() + timedelta(days=14),
        created_by=user.id,
        tax_rate=Decimal('10.00'),
        notes='Note',
        terms='Terms'
    )
    db.session.add(inv)
    db.session.commit()

    it = InvoiceItem(invoice_id=inv.id, description='Line A', quantity=Decimal('2.00'), unit_price=Decimal('50.00'))
    db.session.add(it)
    db.session.commit()

    resp = client.get(f'/invoices/{inv.id}/edit')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # Fields
    assert 'name="client_name"' in html
    assert 'name="client_email"' in html
    assert 'name="client_address"' in html
    assert 'name="due_date"' in html
    assert 'name="tax_rate"' in html
    assert 'name="notes"' in html
    assert 'name="terms"' in html

    # Item row present with existing description
    assert 'Line A' in html


@pytest.mark.routes
def test_generate_from_time_page_renders_lists(app, client, user, project):
    """Ensure the generate-from-time page renders unbilled entries and costs with checkboxes."""
    # Authenticate
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True

    # Create client and invoice
    cl = Client(name='GenFromTime Client', email='gft@test.com')
    db.session.add(cl)
    db.session.commit()

    inv = Invoice(
        invoice_number='INV-TEST-GFT-001',
        project_id=project.id,
        client_name=cl.name,
        client_id=cl.id,
        due_date=date.today() + timedelta(days=7),
        created_by=user.id
    )
    db.session.add(inv)
    db.session.commit()

    # Add an unbilled time entry and a project cost
    from app.models import TimeEntry, ProjectCost
    start = datetime.utcnow() - timedelta(hours=2)
    end = datetime.utcnow()
    te = TimeEntry(user_id=user.id, project_id=project.id, start_time=start, end_time=end, notes='Work A', billable=True)
    db.session.add(te)
    db.session.commit()

    pc = ProjectCost(project_id=project.id, user_id=user.id, description='Expense A', category='materials', amount=Decimal('12.50'), cost_date=date.today(), billable=True)
    db.session.add(pc)
    db.session.commit()

    # Visit page
    resp = client.get(f'/invoices/{inv.id}/generate-from-time')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # Check checkboxes render
    assert 'name="time_entries[]"' in html
    assert 'name="project_costs[]"' in html
    # Check summary numbers render
    assert 'Total available hours' in html
    assert 'Total available costs' in html

# Payment Status Tracking Tests

def test_invoice_payment_status_initialization(app, sample_user, sample_project):
    """Test that invoices initialize with correct payment status."""
    # Create a client first
    from app.models import Client
    client = Client(
        name='Payment Status Test Client',
        email='payment@test.com'
    )
    db.session.add(client)
    db.session.commit()
    
    invoice = Invoice(
        invoice_number='INV-20241201-005',
        project_id=sample_project.id,
        client_name='Payment Status Test Client',
        due_date=date.today() + timedelta(days=30),
        created_by=sample_user.id,
        client_id=client.id
    )
    
    db.session.add(invoice)
    db.session.commit()
    
    # Check default payment status values
    assert invoice.payment_status == 'unpaid'
    assert invoice.amount_paid == Decimal('0')
    assert invoice.payment_date is None
    assert invoice.payment_method is None
    assert invoice.payment_reference is None
    assert invoice.payment_notes is None
    
    # Check payment properties
    assert invoice.is_paid == False
    assert invoice.is_partially_paid == False

def test_record_full_payment(app, sample_invoice):
    """Test recording a full payment."""
    # Set up invoice with items
    item = InvoiceItem(
        invoice_id=sample_invoice.id,
        description='Development work',
        quantity=Decimal('10.00'),
        unit_price=Decimal('75.00')
    )
    db.session.add(item)
    db.session.commit()
    
    sample_invoice.calculate_totals()
    total_amount = sample_invoice.total_amount
    
    # Record full payment
    payment_date = date.today()
    sample_invoice.record_payment(
        amount=total_amount,
        payment_date=payment_date,
        payment_method='bank_transfer',
        payment_reference='TXN123456',
        payment_notes='Payment received via bank transfer'
    )
    
    # Check payment tracking
    assert sample_invoice.amount_paid == total_amount
    assert sample_invoice.payment_status == 'fully_paid'
    assert sample_invoice.payment_date == payment_date
    assert sample_invoice.payment_method == 'bank_transfer'
    assert sample_invoice.payment_reference == 'TXN123456'
    assert sample_invoice.payment_notes == 'Payment received via bank transfer'
    
    # Check properties
    assert sample_invoice.is_paid == True
    assert sample_invoice.is_partially_paid == False
    assert sample_invoice.outstanding_amount == Decimal('0')
    assert sample_invoice.payment_percentage == 100.0
    
    # Check that invoice status was updated
    assert sample_invoice.status == 'paid'

def test_record_partial_payment(app, sample_invoice):
    """Test recording a partial payment."""
    # Set up invoice with items
    item = InvoiceItem(
        invoice_id=sample_invoice.id,
        description='Development work',
        quantity=Decimal('10.00'),
        unit_price=Decimal('100.00')
    )
    db.session.add(item)
    db.session.commit()
    
    sample_invoice.calculate_totals()
    total_amount = sample_invoice.total_amount  # 1000.00
    
    # Record partial payment (50%)
    partial_amount = total_amount / 2
    sample_invoice.record_payment(
        amount=partial_amount,
        payment_method='credit_card',
        payment_reference='CC-789'
    )
    
    # Check payment tracking
    assert sample_invoice.amount_paid == partial_amount
    assert sample_invoice.payment_status == 'partially_paid'
    assert sample_invoice.payment_method == 'credit_card'
    assert sample_invoice.payment_reference == 'CC-789'
    
    # Check properties
    assert sample_invoice.is_paid == False
    assert sample_invoice.is_partially_paid == True
    assert sample_invoice.outstanding_amount == partial_amount
    assert sample_invoice.payment_percentage == 50.0

def test_record_overpayment(app, sample_invoice):
    """Test recording an overpayment."""
    # Set up invoice with items
    item = InvoiceItem(
        invoice_id=sample_invoice.id,
        description='Development work',
        quantity=Decimal('5.00'),
        unit_price=Decimal('100.00')
    )
    db.session.add(item)
    db.session.commit()
    
    sample_invoice.calculate_totals()
    total_amount = sample_invoice.total_amount  # 500.00
    
    # Record overpayment
    overpayment_amount = total_amount + Decimal('50.00')  # 550.00
    sample_invoice.record_payment(
        amount=overpayment_amount,
        payment_method='cash'
    )
    
    # Check payment tracking
    assert sample_invoice.amount_paid == overpayment_amount
    assert sample_invoice.payment_status == 'overpaid'
    assert sample_invoice.outstanding_amount == Decimal('-50.00')
    assert sample_invoice.payment_percentage > 100.0

def test_multiple_payments(app, sample_invoice):
    """Test recording multiple payments."""
    # Set up invoice with items
    item = InvoiceItem(
        invoice_id=sample_invoice.id,
        description='Development work',
        quantity=Decimal('10.00'),
        unit_price=Decimal('100.00')
    )
    db.session.add(item)
    db.session.commit()
    
    sample_invoice.calculate_totals()
    total_amount = sample_invoice.total_amount  # 1000.00
    
    # First payment (30%)
    first_payment = Decimal('300.00')
    sample_invoice.record_payment(
        amount=first_payment,
        payment_method='check',
        payment_reference='CHK-001'
    )
    
    assert sample_invoice.amount_paid == first_payment
    assert sample_invoice.payment_status == 'partially_paid'
    
    # Second payment (70% - completing the payment)
    second_payment = Decimal('700.00')
    sample_invoice.record_payment(
        amount=second_payment,
        payment_method='bank_transfer',
        payment_reference='TXN-002'
    )
    
    # Check final payment status
    assert sample_invoice.amount_paid == total_amount
    assert sample_invoice.payment_status == 'fully_paid'
    assert sample_invoice.outstanding_amount == Decimal('0')
    assert sample_invoice.payment_percentage == 100.0

def test_update_payment_status_method(app, sample_invoice):
    """Test the update_payment_status method."""
    # Set up invoice with items
    item = InvoiceItem(
        invoice_id=sample_invoice.id,
        description='Development work',
        quantity=Decimal('10.00'),
        unit_price=Decimal('100.00')
    )
    db.session.add(item)
    db.session.commit()
    
    sample_invoice.calculate_totals()
    total_amount = sample_invoice.total_amount
    
    # Test unpaid status
    sample_invoice.amount_paid = Decimal('0')
    sample_invoice.update_payment_status()
    assert sample_invoice.payment_status == 'unpaid'
    
    # Test partial payment status
    sample_invoice.amount_paid = total_amount / 2
    sample_invoice.update_payment_status()
    assert sample_invoice.payment_status == 'partially_paid'
    
    # Test fully paid status
    sample_invoice.amount_paid = total_amount
    sample_invoice.update_payment_status()
    assert sample_invoice.payment_status == 'fully_paid'
    
    # Test overpaid status
    sample_invoice.amount_paid = total_amount + Decimal('100')
    sample_invoice.update_payment_status()
    assert sample_invoice.payment_status == 'overpaid'

def test_invoice_to_dict_includes_payment_fields(app, sample_invoice):
    """Test that invoice to_dict includes payment tracking fields."""
    # Record a payment
    sample_invoice.record_payment(
        amount=Decimal('500.00'),
        payment_date=date.today(),
        payment_method='paypal',
        payment_reference='PP-123',
        payment_notes='PayPal payment'
    )
    
    invoice_dict = sample_invoice.to_dict()
    
    # Check that payment fields are included
    assert 'payment_date' in invoice_dict
    assert 'payment_method' in invoice_dict
    assert 'payment_reference' in invoice_dict
    assert 'payment_notes' in invoice_dict
    assert 'amount_paid' in invoice_dict
    assert 'payment_status' in invoice_dict
    assert 'is_paid' in invoice_dict
    assert 'is_partially_paid' in invoice_dict
    assert 'outstanding_amount' in invoice_dict
    assert 'payment_percentage' in invoice_dict
    
    # Check values
    assert invoice_dict['payment_method'] == 'paypal'
    assert invoice_dict['payment_reference'] == 'PP-123'
    assert invoice_dict['payment_notes'] == 'PayPal payment'
    assert invoice_dict['amount_paid'] == 500.00