"""
Comprehensive tests for Expense model and related functionality.

This module tests:
- Expense model creation and validation
- Relationships with User, Project, Client, and Invoice models
- Query methods (get_expenses, get_total_expenses, etc.)
- Approval and reimbursement workflows
- Data integrity and constraints
"""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from app import create_app, db
from app.models import User, Project, Client, Invoice, Expense
from factories import InvoiceFactory
from factories import ExpenseFactory


@pytest.fixture
def app():
    """Create and configure a test application instance."""
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "WTF_CSRF_ENABLED": False})

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client_fixture(app):
    """Create a test Flask client."""
    return app.test_client()


@pytest.fixture
def test_user(app):
    """Create a test user."""
    with app.app_context():
        user = User(username="testuser", role="user")
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def test_admin(app):
    """Create a test admin user."""
    with app.app_context():
        admin = User(username="admin", role="admin")
        db.session.add(admin)
        db.session.commit()
        return admin.id


@pytest.fixture
def test_client(app):
    """Create a test client."""
    with app.app_context():
        client = Client(name="Test Client", description="A test client")
        db.session.add(client)
        db.session.commit()
        return client.id


@pytest.fixture
def test_project(app, test_client):
    """Create a test project."""
    with app.app_context():
        project = Project(
            name="Test Project",
            client_id=test_client,
            description="A test project",
            billable=True,
            hourly_rate=Decimal("100.00"),
        )
        db.session.add(project)
        db.session.commit()
        return project.id


@pytest.fixture
def test_invoice(app, test_client, test_project, test_user):
    """Create a test invoice."""
    with app.app_context():
        client = db.session.get(Client, test_client)
        invoice = InvoiceFactory(
            invoice_number="INV-TEST-001",
            project_id=test_project,
            client_name=client.name,
            due_date=date.today() + timedelta(days=30),
            created_by=test_user,
            client_id=test_client,
            issue_date=date.today(),
            status="draft",
        )
        db.session.commit()
        return invoice.id


# Model Tests


class TestExpenseModel:
    """Test Expense model creation, validation, and basic operations."""

    def test_create_expense(self, app, test_user):
        """Test creating a basic expense."""
        with app.app_context():
            expense = ExpenseFactory(
                user_id=test_user,
                title="Travel Expense",
                category="travel",
                amount=Decimal("150.00"),
                expense_date=date.today(),
                billable=False,
                reimbursable=True,
            )

            assert expense.id is not None
            assert expense.title == "Travel Expense"
            assert expense.category == "travel"
            assert expense.amount == Decimal("150.00")
            assert expense.currency_code == "EUR"
            assert expense.status == "pending"
            assert expense.billable is False
            assert expense.reimbursable is True

    def test_create_expense_with_all_fields(self, app, test_user, test_project, test_client):
        """Test creating an expense with all optional fields."""
        with app.app_context():
            expense = ExpenseFactory(
                user_id=test_user,
                title="Conference Travel",
                category="travel",
                amount=Decimal("500.00"),
                expense_date=date.today(),
                description="Flight and hotel for conference",
                project_id=test_project,
                client_id=test_client,
                currency_code="USD",
                tax_amount=Decimal("50.00"),
                payment_method="credit_card",
                payment_date=date.today(),
                vendor="Airline Inc",
                receipt_number="REC-2024-001",
                notes="Business class flight",
                tags="conference,travel,urgent",
                billable=True,
                reimbursable=True,
            )

            assert expense.description == "Flight and hotel for conference"
            assert expense.project_id == test_project
            assert expense.client_id == test_client
            assert expense.currency_code == "USD"
            assert expense.tax_amount == Decimal("50.00")
            assert expense.vendor == "Airline Inc"
            assert expense.billable is True

    def test_expense_str_representation(self, app, test_user):
        """Test __repr__ method."""
        with app.app_context():
            expense = Expense(
                user_id=test_user,
                title="Office Supplies",
                category="supplies",
                amount=Decimal("75.50"),
                expense_date=date.today(),
            )
            db.session.add(expense)
            db.session.commit()

            assert "Office Supplies" in str(expense)
            assert "EUR" in str(expense)

    def test_expense_timestamps(self, app, test_user):
        """Test automatic timestamp creation."""
        with app.app_context():
            expense = Expense(
                user_id=test_user,
                title="Test Expense",
                category="other",
                amount=Decimal("10.00"),
                expense_date=date.today(),
            )
            db.session.add(expense)
            db.session.commit()

            assert expense.created_at is not None
            assert expense.updated_at is not None
            assert isinstance(expense.created_at, datetime)
            assert isinstance(expense.updated_at, datetime)


class TestExpenseProperties:
    """Test Expense computed properties."""

    def test_total_amount_property(self, app, test_user):
        """Test total_amount property including tax."""
        with app.app_context():
            expense = Expense(
                user_id=test_user,
                title="Test Expense",
                category="travel",
                amount=Decimal("100.00"),
                tax_amount=Decimal("10.00"),
                expense_date=date.today(),
            )
            db.session.add(expense)
            db.session.commit()

            assert expense.total_amount == Decimal("110.00")

    def test_tag_list_property(self, app, test_user):
        """Test tag_list property parsing."""
        with app.app_context():
            expense = Expense(
                user_id=test_user,
                title="Test Expense",
                category="travel",
                amount=Decimal("100.00"),
                expense_date=date.today(),
                tags="urgent, client-meeting, conference",
            )
            db.session.add(expense)
            db.session.commit()

            tags = expense.tag_list
            assert len(tags) == 3
            assert "urgent" in tags
            assert "client-meeting" in tags
            assert "conference" in tags

    def test_is_approved_property(self, app, test_user, test_admin):
        """Test is_approved property."""
        with app.app_context():
            expense = Expense(
                user_id=test_user,
                title="Test Expense",
                category="travel",
                amount=Decimal("100.00"),
                expense_date=date.today(),
            )
            db.session.add(expense)
            db.session.commit()

            # Initially not approved
            assert expense.is_approved is False

            # Approve
            expense.approve(test_admin)
            db.session.commit()

            assert expense.is_approved is True

    def test_is_reimbursed_property(self, app, test_user):
        """Test is_reimbursed property."""
        with app.app_context():
            expense = Expense(
                user_id=test_user,
                title="Test Expense",
                category="travel",
                amount=Decimal("100.00"),
                expense_date=date.today(),
            )
            db.session.add(expense)
            db.session.commit()

            assert expense.is_reimbursed is False

            expense.mark_as_reimbursed()
            db.session.commit()

            assert expense.is_reimbursed is True


class TestExpenseRelationships:
    """Test Expense relationships with other models."""

    def test_user_relationship(self, app, test_user):
        """Test relationship with User model."""
        with app.app_context():
            expense = Expense(
                user_id=test_user,
                title="Test Expense",
                category="travel",
                amount=Decimal("100.00"),
                expense_date=date.today(),
            )
            db.session.add(expense)
            db.session.commit()

            expense = db.session.get(Expense, expense.id)
            user = db.session.get(User, test_user)

            assert expense.user is not None
            assert expense.user.id == test_user
            assert expense in user.expenses.all()

    def test_project_relationship(self, app, test_user, test_project):
        """Test relationship with Project model."""
        with app.app_context():
            expense = Expense(
                user_id=test_user,
                title="Test Expense",
                category="travel",
                amount=Decimal("100.00"),
                expense_date=date.today(),
                project_id=test_project,
            )
            db.session.add(expense)
            db.session.commit()

            expense = db.session.get(Expense, expense.id)
            project = db.session.get(Project, test_project)

            assert expense.project is not None
            assert expense.project.id == test_project
            assert expense in project.expenses.all()

    def test_client_relationship(self, app, test_user, test_client):
        """Test relationship with Client model."""
        with app.app_context():
            expense = Expense(
                user_id=test_user,
                title="Test Expense",
                category="travel",
                amount=Decimal("100.00"),
                expense_date=date.today(),
                client_id=test_client,
            )
            db.session.add(expense)
            db.session.commit()

            expense = db.session.get(Expense, expense.id)
            client = db.session.get(Client, test_client)

            assert expense.client is not None
            assert expense.client.id == test_client
            assert expense in client.expenses.all()


class TestExpenseMethods:
    """Test Expense instance and class methods."""

    def test_approve_method(self, app, test_user, test_admin):
        """Test approving an expense."""
        with app.app_context():
            expense = Expense(
                user_id=test_user,
                title="Test Expense",
                category="travel",
                amount=Decimal("100.00"),
                expense_date=date.today(),
            )
            db.session.add(expense)
            db.session.commit()

            expense.approve(test_admin, notes="Approved for reimbursement")
            db.session.commit()

            assert expense.status == "approved"
            assert expense.approved_by == test_admin
            assert expense.approved_at is not None

    def test_reject_method(self, app, test_user, test_admin):
        """Test rejecting an expense."""
        with app.app_context():
            expense = Expense(
                user_id=test_user,
                title="Test Expense",
                category="travel",
                amount=Decimal("100.00"),
                expense_date=date.today(),
            )
            db.session.add(expense)
            db.session.commit()

            expense.reject(test_admin, "Receipt not provided")
            db.session.commit()

            assert expense.status == "rejected"
            assert expense.approved_by == test_admin
            assert expense.rejection_reason == "Receipt not provided"

    def test_mark_as_reimbursed(self, app, test_user, test_admin):
        """Test marking expense as reimbursed."""
        with app.app_context():
            expense = Expense(
                user_id=test_user,
                title="Test Expense",
                category="travel",
                amount=Decimal("100.00"),
                expense_date=date.today(),
            )
            db.session.add(expense)
            db.session.commit()

            # Approve first
            expense.approve(test_admin)
            db.session.commit()

            # Mark as reimbursed
            expense.mark_as_reimbursed()
            db.session.commit()

            assert expense.reimbursed is True
            assert expense.reimbursed_at is not None
            assert expense.status == "reimbursed"

    def test_mark_as_invoiced(self, app, test_user, test_invoice):
        """Test marking expense as invoiced."""
        with app.app_context():
            expense = Expense(
                user_id=test_user,
                title="Test Expense",
                category="travel",
                amount=Decimal("100.00"),
                expense_date=date.today(),
                billable=True,
            )
            db.session.add(expense)
            db.session.commit()

            expense.mark_as_invoiced(test_invoice)
            db.session.commit()

            assert expense.invoiced is True
            assert expense.invoice_id == test_invoice

    def test_to_dict(self, app, test_user):
        """Test converting expense to dictionary."""
        with app.app_context():
            expense = Expense(
                user_id=test_user,
                title="Test Expense",
                category="travel",
                amount=Decimal("100.00"),
                tax_amount=Decimal("10.00"),
                expense_date=date.today(),
                description="Test description",
            )
            db.session.add(expense)
            db.session.commit()

            expense = db.session.get(Expense, expense.id)
            expense_dict = expense.to_dict()

            assert expense_dict["id"] == expense.id
            assert expense_dict["user_id"] == test_user
            assert expense_dict["title"] == "Test Expense"
            assert expense_dict["category"] == "travel"
            assert expense_dict["amount"] == 100.00
            assert expense_dict["tax_amount"] == 10.00
            assert expense_dict["total_amount"] == 110.00
            assert "created_at" in expense_dict


class TestExpenseQueries:
    """Test Expense query class methods."""

    def test_get_expenses(self, app, test_user):
        """Test retrieving expenses."""
        with app.app_context():
            expenses = [
                Expense(
                    user_id=test_user,
                    title=f"Expense {i}",
                    category="travel",
                    amount=Decimal(f"{100 + i * 10}.00"),
                    expense_date=date.today() - timedelta(days=i),
                )
                for i in range(5)
            ]
            db.session.add_all(expenses)
            db.session.commit()

            retrieved = Expense.get_expenses(user_id=test_user)
            assert len(retrieved) == 5

            # Should be ordered by expense_date desc
            assert retrieved[0].title == "Expense 0"

    def test_get_expenses_by_status(self, app, test_user, test_admin):
        """Test filtering expenses by status."""
        with app.app_context():
            # Create expenses with different statuses
            exp1 = Expense(
                user_id=test_user,
                title="Pending Expense",
                category="travel",
                amount=Decimal("100.00"),
                expense_date=date.today(),
            )
            exp2 = Expense(
                user_id=test_user,
                title="Approved Expense",
                category="travel",
                amount=Decimal("200.00"),
                expense_date=date.today(),
            )
            db.session.add_all([exp1, exp2])
            db.session.commit()

            exp2.approve(test_admin)
            db.session.commit()

            pending = Expense.get_expenses(user_id=test_user, status="pending")
            assert len(pending) == 1
            assert pending[0].title == "Pending Expense"

            approved = Expense.get_expenses(user_id=test_user, status="approved")
            assert len(approved) == 1
            assert approved[0].title == "Approved Expense"

    def test_get_total_expenses(self, app, test_user):
        """Test calculating total expenses."""
        with app.app_context():
            amounts = [Decimal("100.00"), Decimal("250.50"), Decimal("75.25")]
            taxes = [Decimal("10.00"), Decimal("25.00"), Decimal("7.50")]

            expenses = [
                Expense(
                    user_id=test_user,
                    title=f"Expense {i}",
                    category="travel",
                    amount=amount,
                    tax_amount=tax,
                    expense_date=date.today(),
                )
                for i, (amount, tax) in enumerate(zip(amounts, taxes))
            ]
            db.session.add_all(expenses)
            db.session.commit()

            total = Expense.get_total_expenses(user_id=test_user, include_tax=True)
            expected = sum(amounts) + sum(taxes)
            assert abs(total - float(expected)) < 0.01

    def test_get_expenses_by_category(self, app, test_user):
        """Test grouping expenses by category."""
        with app.app_context():
            categories = ["travel", "travel", "meals", "supplies", "meals"]
            amounts = [Decimal("100.00"), Decimal("150.00"), Decimal("50.00"), Decimal("75.00"), Decimal("60.00")]

            expenses = [
                Expense(
                    user_id=test_user, title=f"Expense {i}", category=category, amount=amount, expense_date=date.today()
                )
                for i, (category, amount) in enumerate(zip(categories, amounts))
            ]
            db.session.add_all(expenses)
            db.session.commit()

            by_category = Expense.get_expenses_by_category(user_id=test_user)

            assert len(by_category) == 3

            travel = next(c for c in by_category if c["category"] == "travel")
            assert travel["count"] == 2
            assert abs(travel["total_amount"] - 250.00) < 0.01

    def test_get_pending_approvals(self, app, test_user):
        """Test retrieving pending expenses."""
        with app.app_context():
            exp1 = Expense(
                user_id=test_user,
                title="Pending 1",
                category="travel",
                amount=Decimal("100.00"),
                expense_date=date.today(),
                status="pending",
            )
            exp2 = Expense(
                user_id=test_user,
                title="Pending 2",
                category="travel",
                amount=Decimal("200.00"),
                expense_date=date.today(),
                status="pending",
            )
            db.session.add_all([exp1, exp2])
            db.session.commit()

            pending = Expense.get_pending_approvals(user_id=test_user)
            assert len(pending) == 2

    def test_get_uninvoiced_expenses(self, app, test_user, test_admin, test_project):
        """Test retrieving uninvoiced billable expenses."""
        with app.app_context():
            exp1 = Expense(
                user_id=test_user,
                title="Billable Expense",
                category="travel",
                amount=Decimal("100.00"),
                expense_date=date.today(),
                billable=True,
                project_id=test_project,
            )
            exp2 = Expense(
                user_id=test_user,
                title="Non-billable Expense",
                category="travel",
                amount=Decimal("200.00"),
                expense_date=date.today(),
                billable=False,
                project_id=test_project,
            )
            db.session.add_all([exp1, exp2])
            db.session.commit()

            # Approve both
            exp1.approve(test_admin)
            exp2.approve(test_admin)
            db.session.commit()

            uninvoiced = Expense.get_uninvoiced_expenses(project_id=test_project)
            assert len(uninvoiced) == 1
            assert uninvoiced[0].title == "Billable Expense"


class TestExpenseConstraints:
    """Test database constraints and data integrity."""

    def test_cannot_create_expense_without_user(self, app):
        """Test that user_id is required."""
        with app.app_context():
            expense = Expense(
                user_id=None,
                title="Test Expense",
                category="travel",
                amount=Decimal("100.00"),
                expense_date=date.today(),
            )
            db.session.add(expense)

            with pytest.raises(Exception):
                db.session.commit()

            db.session.rollback()


# Smoke Tests


class TestExpenseSmokeTests:
    """Basic smoke tests to ensure Expense functionality works."""

    def test_expense_creation_smoke(self, app, test_user):
        """Smoke test: Can we create an expense?"""
        with app.app_context():
            expense = Expense(
                user_id=test_user,
                title="Smoke Test Expense",
                category="travel",
                amount=Decimal("99.99"),
                expense_date=date.today(),
            )
            db.session.add(expense)
            db.session.commit()

            assert expense.id is not None

    def test_expense_query_smoke(self, app, test_user):
        """Smoke test: Can we query expenses?"""
        with app.app_context():
            expense = Expense(
                user_id=test_user,
                title="Query Smoke Test",
                category="travel",
                amount=Decimal("200.00"),
                expense_date=date.today(),
            )
            db.session.add(expense)
            db.session.commit()

            expenses = Expense.query.filter_by(user_id=test_user).all()
            assert len(expenses) > 0

    def test_expense_workflow_smoke(self, app, test_user, test_admin):
        """Smoke test: Does the full approval workflow work?"""
        with app.app_context():
            # Create expense
            expense = Expense(
                user_id=test_user,
                title="Workflow Test",
                category="travel",
                amount=Decimal("500.00"),
                expense_date=date.today(),
                reimbursable=True,
            )
            db.session.add(expense)
            db.session.commit()

            # Approve
            expense.approve(test_admin)
            db.session.commit()
            assert expense.status == "approved"

            # Reimburse
            expense.mark_as_reimbursed()
            db.session.commit()
            assert expense.status == "reimbursed"
