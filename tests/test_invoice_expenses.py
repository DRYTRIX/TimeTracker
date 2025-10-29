"""
Tests for invoice expense functionality
"""
import pytest
from datetime import datetime, timedelta, date
from decimal import Decimal
from app import db
from app.models import Invoice, InvoiceItem, Expense, User, Project, Client


@pytest.fixture
def test_user(app):
    """Create a test user"""
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.set_password('testpass')
        user.is_admin = True  # Set after initialization
        db.session.add(user)
        db.session.commit()
        yield user
        db.session.delete(user)
        db.session.commit()


@pytest.fixture
def test_client(app):
    """Create a test client"""
    with app.app_context():
        client = Client(name='Test Client', email='client@example.com')
        db.session.add(client)
        db.session.commit()
        yield client
        db.session.delete(client)
        db.session.commit()


@pytest.fixture
def test_project(app, test_client):
    """Create a test project"""
    with app.app_context():
        project = Project(
            name='Test Project',
            client_id=test_client.id,
            billable=True,
            hourly_rate=Decimal('100.00')
        )
        db.session.add(project)
        db.session.commit()
        yield project
        db.session.delete(project)
        db.session.commit()


@pytest.fixture
def test_invoice(app, test_user, test_project, test_client):
    """Create a test invoice"""
    with app.app_context():
        invoice = Invoice(
            invoice_number='INV-TEST-001',
            project_id=test_project.id,
            client_name=test_client.name,
            client_id=test_client.id,
            due_date=date.today() + timedelta(days=30),
            created_by=test_user.id,
            tax_rate=Decimal('10.00')
        )
        db.session.add(invoice)
        db.session.commit()
        yield invoice
        db.session.delete(invoice)
        db.session.commit()


@pytest.fixture
def test_expense(app, test_user, test_project):
    """Create a test expense"""
    with app.app_context():
        expense = Expense(
            user_id=test_user.id,
            project_id=test_project.id,
            title='Travel Expense',
            description='Client meeting travel',
            category='travel',
            amount=Decimal('150.00'),
            tax_amount=Decimal('15.00'),
            expense_date=date.today(),
            billable=True,
            vendor='Taxi Service'
        )
        db.session.add(expense)
        db.session.commit()
        yield expense
        db.session.delete(expense)
        db.session.commit()


class TestInvoiceExpenseIntegration:
    """Test invoice expense integration"""
    
    def test_link_expense_to_invoice(self, app, test_invoice, test_expense):
        """Test linking an expense to an invoice"""
        with app.app_context():
            # Mark expense as invoiced
            test_expense.mark_as_invoiced(test_invoice.id)
            db.session.commit()
            
            # Verify the expense is linked
            assert test_expense.invoiced is True
            assert test_expense.invoice_id == test_invoice.id
            assert test_expense.is_invoiced is True
            
            # Verify the invoice has the expense
            assert test_expense in test_invoice.expenses.all()
    
    def test_unlink_expense_from_invoice(self, app, test_invoice, test_expense):
        """Test unlinking an expense from an invoice"""
        with app.app_context():
            # Mark expense as invoiced first
            test_expense.mark_as_invoiced(test_invoice.id)
            db.session.commit()
            
            # Then unmark it
            test_expense.unmark_as_invoiced()
            db.session.commit()
            
            # Verify the expense is unlinked
            assert test_expense.invoiced is False
            assert test_expense.invoice_id is None
            assert test_expense.is_invoiced is False
    
    def test_calculate_totals_with_expenses(self, app, test_invoice, test_expense):
        """Test that invoice totals include expenses"""
        with app.app_context():
            # Add an invoice item
            item = InvoiceItem(
                invoice_id=test_invoice.id,
                description='Development Work',
                quantity=Decimal('10.00'),
                unit_price=Decimal('100.00')
            )
            db.session.add(item)
            
            # Link expense to invoice
            test_expense.mark_as_invoiced(test_invoice.id)
            db.session.commit()
            
            # Calculate totals
            test_invoice.calculate_totals()
            db.session.commit()
            
            # Expected: 1000 (item) + 165 (expense with tax) = 1165
            # Then apply 10% tax on subtotal: 1165 * 1.10 = 1281.50
            expected_subtotal = Decimal('1165.00')  # 1000 + 165
            expected_tax = Decimal('116.50')  # 1165 * 0.10
            expected_total = Decimal('1281.50')  # 1165 + 116.50
            
            assert test_invoice.subtotal == expected_subtotal
            assert test_invoice.tax_amount == expected_tax
            assert test_invoice.total_amount == expected_total
    
    def test_uninvoiced_expenses_query(self, app, test_expense, test_project):
        """Test querying for uninvoiced expenses"""
        with app.app_context():
            # The expense should be uninvoiced initially
            uninvoiced = Expense.get_uninvoiced_expenses(project_id=test_project.id)
            
            assert len(uninvoiced) > 0
            assert test_expense in uninvoiced
    
    def test_uninvoiced_expenses_excludes_invoiced(self, app, test_invoice, test_expense, test_project):
        """Test that invoiced expenses are excluded from uninvoiced query"""
        with app.app_context():
            # Mark expense as invoiced
            test_expense.mark_as_invoiced(test_invoice.id)
            db.session.commit()
            
            # Query for uninvoiced expenses
            uninvoiced = Expense.get_uninvoiced_expenses(project_id=test_project.id)
            
            # The expense should not be in the list
            assert test_expense not in uninvoiced
    
    def test_expense_in_pdf_export(self, app, test_invoice, test_expense):
        """Test that expenses are included in PDF export (template test)"""
        with app.app_context():
            # Link expense to invoice
            test_expense.mark_as_invoiced(test_invoice.id)
            db.session.commit()
            
            # Refresh to get the relationship
            db.session.refresh(test_invoice)
            
            # Verify the expense is accessible from the invoice
            expenses = test_invoice.expenses.all()
            assert len(expenses) == 1
            assert expenses[0].id == test_expense.id
    
    def test_multiple_expenses_on_invoice(self, app, test_invoice, test_user, test_project):
        """Test that multiple expenses can be added to an invoice"""
        with app.app_context():
            # Create multiple expenses
            expense1 = Expense(
                user_id=test_user.id,
                project_id=test_project.id,
                title='Travel Expense 1',
                category='travel',
                amount=Decimal('100.00'),
                expense_date=date.today(),
                billable=True
            )
            expense2 = Expense(
                user_id=test_user.id,
                project_id=test_project.id,
                title='Meals Expense',
                category='meals',
                amount=Decimal('50.00'),
                expense_date=date.today(),
                billable=True
            )
            db.session.add_all([expense1, expense2])
            db.session.commit()
            
            # Link both to invoice
            expense1.mark_as_invoiced(test_invoice.id)
            expense2.mark_as_invoiced(test_invoice.id)
            db.session.commit()
            
            # Verify both are linked
            expenses = test_invoice.expenses.all()
            assert len(expenses) == 2
            
            # Calculate totals
            test_invoice.calculate_totals()
            db.session.commit()
            
            # Expected: 150 (expenses) * 1.10 (tax) = 165
            expected_subtotal = Decimal('150.00')
            expected_tax = Decimal('15.00')
            expected_total = Decimal('165.00')
            
            assert test_invoice.subtotal == expected_subtotal
            assert test_invoice.tax_amount == expected_tax
            assert test_invoice.total_amount == expected_total
            
            # Cleanup
            db.session.delete(expense1)
            db.session.delete(expense2)
            db.session.commit()


class TestExpenseProperties:
    """Test expense model properties"""
    
    def test_expense_total_amount_includes_tax(self, app, test_expense):
        """Test that expense total_amount property includes tax"""
        with app.app_context():
            # Expense amount is 150, tax is 15
            assert test_expense.total_amount == Decimal('165.00')
    
    def test_expense_is_invoiced_property(self, app, test_invoice, test_expense):
        """Test the is_invoiced property"""
        with app.app_context():
            # Initially not invoiced
            assert test_expense.is_invoiced is False
            
            # After marking as invoiced
            test_expense.mark_as_invoiced(test_invoice.id)
            db.session.commit()
            
            assert test_expense.is_invoiced is True

