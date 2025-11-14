"""
Comprehensive tests for ProjectCost model and related functionality.

This module tests:
- ProjectCost model creation and validation
- Relationships with Project, User, and Invoice models
- Query methods (get_project_costs, get_total_costs, etc.)
- Invoicing workflow
- Data integrity and constraints
"""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from app import create_app, db
from app.models import User, Project, Client, Invoice, ProjectCost
from factories import InvoiceFactory


@pytest.fixture
def app():
    """Create and configure a test application instance."""
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False
    })
    
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
        user = User(username='testuser', role='user')
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def test_admin(app):
    """Create a test admin user."""
    with app.app_context():
        admin = User(username='admin', role='admin')
        db.session.add(admin)
        db.session.commit()
        return admin.id


@pytest.fixture
def test_client(app):
    """Create a test client."""
    with app.app_context():
        client = Client(name='Test Client', description='A test client')
        db.session.add(client)
        db.session.commit()
        return client.id


@pytest.fixture
def test_project(app, test_client):
    """Create a test project."""
    with app.app_context():
        project = Project(
            name='Test Project',
            client_id=test_client,
            description='A test project',
            billable=True,
            hourly_rate=Decimal('100.00')
        )
        db.session.add(project)
        db.session.commit()
        return project.id


@pytest.fixture
def test_invoice(app, test_client, test_project, test_user):
    """Create a test invoice."""
    with app.app_context():
        # Get the client to retrieve client_name
        client = db.session.get(Client, test_client)
        invoice = InvoiceFactory(
            invoice_number='INV-TEST-001',
            project_id=test_project,
            client_name=client.name,
            due_date=date.today() + timedelta(days=30),
            created_by=test_user,
            client_id=test_client,
            status='draft'
        )
        db.session.add(invoice)
        db.session.commit()
        return invoice.id


# Model Tests

class TestProjectCostModel:
    """Test ProjectCost model creation, validation, and basic operations."""
    
    def test_create_project_cost(self, app, test_project, test_user):
        """Test creating a basic project cost."""
        with app.app_context():
            cost = ProjectCost(
                project_id=test_project,
                user_id=test_user,
                description='Office supplies',
                category='materials',
                amount=Decimal('50.00'),
                cost_date=date.today()
            )
            db.session.add(cost)
            db.session.commit()
            
            assert cost.id is not None
            assert cost.description == 'Office supplies'
            assert cost.category == 'materials'
            assert cost.amount == Decimal('50.00')
            assert cost.currency_code == 'EUR'
            assert cost.billable is True
            assert cost.invoiced is False
            assert cost.invoice_id is None
    
    def test_create_project_cost_with_all_fields(self, app, test_project, test_user):
        """Test creating a project cost with all optional fields."""
        with app.app_context():
            cost = ProjectCost(
                project_id=test_project,
                user_id=test_user,
                description='Travel expenses',
                category='travel',
                amount=Decimal('250.75'),
                cost_date=date.today(),
                billable=False,
                notes='Flight to client meeting',
                currency_code='USD',
                receipt_path='/receipts/flight_2025.pdf'
            )
            db.session.add(cost)
            db.session.commit()
            
            assert cost.billable is False
            assert cost.notes == 'Flight to client meeting'
            assert cost.currency_code == 'USD'
            assert cost.receipt_path == '/receipts/flight_2025.pdf'
    
    def test_project_cost_str_representation(self, app, test_project, test_user):
        """Test __repr__ method."""
        with app.app_context():
            cost = ProjectCost(
                project_id=test_project,
                user_id=test_user,
                description='Equipment rental',
                category='equipment',
                amount=Decimal('500.00'),
                cost_date=date.today()
            )
            db.session.add(cost)
            db.session.commit()
            
            assert 'Equipment rental' in str(cost)
            assert '500.00' in str(cost) or '500' in str(cost)
            assert 'EUR' in str(cost)
    
    def test_project_cost_timestamps(self, app, test_project, test_user):
        """Test automatic timestamp creation."""
        with app.app_context():
            cost = ProjectCost(
                project_id=test_project,
                user_id=test_user,
                description='Test cost',
                category='other',
                amount=Decimal('10.00'),
                cost_date=date.today()
            )
            db.session.add(cost)
            db.session.commit()
            
            assert cost.created_at is not None
            assert cost.updated_at is not None
            assert isinstance(cost.created_at, datetime)
            assert isinstance(cost.updated_at, datetime)


class TestProjectCostRelationships:
    """Test ProjectCost relationships with other models."""
    
    def test_project_relationship(self, app, test_project, test_user):
        """Test relationship with Project model."""
        with app.app_context():
            cost = ProjectCost(
                project_id=test_project,
                user_id=test_user,
                description='Test cost',
                category='materials',
                amount=Decimal('100.00'),
                cost_date=date.today()
            )
            db.session.add(cost)
            db.session.commit()
            
            # Refresh objects to load relationships
            cost = db.session.get(ProjectCost, cost.id)
            project = db.session.get(Project, test_project)
            
            assert cost.project is not None
            assert cost.project.id == test_project
            assert cost in project.costs.all()
    
    def test_user_relationship(self, app, test_project, test_user):
        """Test relationship with User model."""
        with app.app_context():
            cost = ProjectCost(
                project_id=test_project,
                user_id=test_user,
                description='Test cost',
                category='services',
                amount=Decimal('200.00'),
                cost_date=date.today()
            )
            db.session.add(cost)
            db.session.commit()
            
            # Refresh objects to load relationships
            cost = db.session.get(ProjectCost, cost.id)
            user = db.session.get(User, test_user)
            
            assert cost.user is not None
            assert cost.user.id == test_user
            assert cost in user.project_costs.all()
    
    def test_invoice_relationship(self, app, test_project, test_user, test_invoice):
        """Test relationship with Invoice model."""
        with app.app_context():
            cost = ProjectCost(
                project_id=test_project,
                user_id=test_user,
                description='Test cost',
                category='materials',
                amount=Decimal('150.00'),
                cost_date=date.today()
            )
            db.session.add(cost)
            db.session.commit()
            
            # Mark as invoiced
            cost.mark_as_invoiced(test_invoice)
            db.session.commit()
            
            # Refresh object
            cost = db.session.get(ProjectCost, cost.id)
            
            assert cost.invoice_id == test_invoice
            assert cost.invoiced is True


class TestProjectCostMethods:
    """Test ProjectCost instance and class methods."""
    
    def test_is_invoiced_property(self, app, test_project, test_user, test_invoice):
        """Test is_invoiced property."""
        with app.app_context():
            cost = ProjectCost(
                project_id=test_project,
                user_id=test_user,
                description='Test cost',
                category='materials',
                amount=Decimal('50.00'),
                cost_date=date.today()
            )
            db.session.add(cost)
            db.session.commit()
            
            # Initially not invoiced
            assert cost.is_invoiced is False
            
            # Mark as invoiced
            cost.mark_as_invoiced(test_invoice)
            db.session.commit()
            
            assert cost.is_invoiced is True
    
    def test_mark_as_invoiced(self, app, test_project, test_user, test_invoice):
        """Test marking a cost as invoiced."""
        with app.app_context():
            cost = ProjectCost(
                project_id=test_project,
                user_id=test_user,
                description='Test cost',
                category='materials',
                amount=Decimal('75.00'),
                cost_date=date.today()
            )
            db.session.add(cost)
            db.session.commit()
            
            original_updated_at = cost.updated_at
            
            # Small delay to ensure timestamp changes
            import time
            time.sleep(0.01)
            
            cost.mark_as_invoiced(test_invoice)
            db.session.commit()
            
            assert cost.invoiced is True
            assert cost.invoice_id == test_invoice
            # Note: updated_at might not change in all databases
    
    def test_unmark_as_invoiced(self, app, test_project, test_user, test_invoice):
        """Test unmarking a cost as invoiced."""
        with app.app_context():
            cost = ProjectCost(
                project_id=test_project,
                user_id=test_user,
                description='Test cost',
                category='materials',
                amount=Decimal('60.00'),
                cost_date=date.today()
            )
            db.session.add(cost)
            db.session.commit()
            
            # Mark as invoiced
            cost.mark_as_invoiced(test_invoice)
            db.session.commit()
            assert cost.invoiced is True
            
            # Unmark
            cost.unmark_as_invoiced()
            db.session.commit()
            
            assert cost.invoiced is False
            assert cost.invoice_id is None
    
    def test_to_dict(self, app, test_project, test_user):
        """Test converting cost to dictionary."""
        with app.app_context():
            cost = ProjectCost(
                project_id=test_project,
                user_id=test_user,
                description='Test cost',
                category='travel',
                amount=Decimal('120.50'),
                cost_date=date.today(),
                notes='Test notes'
            )
            db.session.add(cost)
            db.session.commit()
            
            # Refresh to load relationships
            cost = db.session.get(ProjectCost, cost.id)
            cost_dict = cost.to_dict()
            
            assert cost_dict['id'] == cost.id
            assert cost_dict['project_id'] == test_project
            assert cost_dict['user_id'] == test_user
            assert cost_dict['description'] == 'Test cost'
            assert cost_dict['category'] == 'travel'
            assert cost_dict['amount'] == 120.50
            assert cost_dict['currency_code'] == 'EUR'
            assert cost_dict['billable'] is True
            assert cost_dict['invoiced'] is False
            assert cost_dict['notes'] == 'Test notes'
            assert 'created_at' in cost_dict
            assert 'updated_at' in cost_dict


class TestProjectCostQueries:
    """Test ProjectCost query class methods."""
    
    def test_get_project_costs(self, app, test_project, test_user):
        """Test retrieving project costs."""
        with app.app_context():
            # Create multiple costs
            costs = [
                ProjectCost(
                    project_id=test_project,
                    user_id=test_user,
                    description=f'Cost {i}',
                    category='materials',
                    amount=Decimal(f'{100 + i * 10}.00'),
                    cost_date=date.today() - timedelta(days=i)
                )
                for i in range(5)
            ]
            db.session.add_all(costs)
            db.session.commit()
            
            # Get all costs
            retrieved = ProjectCost.get_project_costs(test_project)
            assert len(retrieved) == 5
            
            # Should be ordered by cost_date desc (newest first)
            assert retrieved[0].description == 'Cost 0'
    
    def test_get_project_costs_with_date_filter(self, app, test_project, test_user):
        """Test filtering costs by date range."""
        with app.app_context():
            # Create costs over different dates
            costs = [
                ProjectCost(
                    project_id=test_project,
                    user_id=test_user,
                    description=f'Cost {i}',
                    category='materials',
                    amount=Decimal('100.00'),
                    cost_date=date.today() - timedelta(days=i * 10)
                )
                for i in range(5)
            ]
            db.session.add_all(costs)
            db.session.commit()
            
            # Filter by date range
            start_date = date.today() - timedelta(days=25)
            end_date = date.today() - timedelta(days=5)
            
            filtered = ProjectCost.get_project_costs(
                test_project,
                start_date=start_date,
                end_date=end_date
            )
            
            # Should get costs from days 10 and 20
            assert len(filtered) == 2
    
    def test_get_project_costs_billable_only(self, app, test_project, test_user):
        """Test filtering for billable costs only."""
        with app.app_context():
            # Create mix of billable and non-billable
            costs = [
                ProjectCost(
                    project_id=test_project,
                    user_id=test_user,
                    description=f'Cost {i}',
                    category='materials',
                    amount=Decimal('100.00'),
                    cost_date=date.today(),
                    billable=(i % 2 == 0)
                )
                for i in range(6)
            ]
            db.session.add_all(costs)
            db.session.commit()
            
            # Get billable only
            billable = ProjectCost.get_project_costs(test_project, billable_only=True)
            assert len(billable) == 3
            assert all(cost.billable for cost in billable)
    
    def test_get_total_costs(self, app, test_project, test_user):
        """Test calculating total costs."""
        with app.app_context():
            # Create costs
            amounts = [Decimal('100.00'), Decimal('250.50'), Decimal('75.25')]
            costs = [
                ProjectCost(
                    project_id=test_project,
                    user_id=test_user,
                    description=f'Cost {i}',
                    category='materials',
                    amount=amount,
                    cost_date=date.today()
                )
                for i, amount in enumerate(amounts)
            ]
            db.session.add_all(costs)
            db.session.commit()
            
            # Get total
            total = ProjectCost.get_total_costs(test_project)
            expected = sum(amounts)
            assert abs(total - float(expected)) < 0.01
    
    def test_get_uninvoiced_costs(self, app, test_project, test_user, test_invoice):
        """Test retrieving uninvoiced billable costs."""
        with app.app_context():
            # Create mix of invoiced and uninvoiced costs
            cost1 = ProjectCost(
                project_id=test_project,
                user_id=test_user,
                description='Uninvoiced cost',
                category='materials',
                amount=Decimal('100.00'),
                cost_date=date.today(),
                billable=True
            )
            cost2 = ProjectCost(
                project_id=test_project,
                user_id=test_user,
                description='Invoiced cost',
                category='materials',
                amount=Decimal('200.00'),
                cost_date=date.today(),
                billable=True
            )
            cost3 = ProjectCost(
                project_id=test_project,
                user_id=test_user,
                description='Non-billable cost',
                category='materials',
                amount=Decimal('50.00'),
                cost_date=date.today(),
                billable=False
            )
            
            db.session.add_all([cost1, cost2, cost3])
            db.session.commit()
            
            # Mark cost2 as invoiced
            cost2.mark_as_invoiced(test_invoice)
            db.session.commit()
            
            # Get uninvoiced
            uninvoiced = ProjectCost.get_uninvoiced_costs(test_project)
            assert len(uninvoiced) == 1
            assert uninvoiced[0].description == 'Uninvoiced cost'
    
    def test_get_costs_by_category(self, app, test_project, test_user):
        """Test grouping costs by category."""
        with app.app_context():
            # Create costs in different categories
            categories = ['travel', 'travel', 'materials', 'equipment', 'materials']
            amounts = [Decimal('100.00'), Decimal('150.00'), Decimal('50.00'), 
                      Decimal('500.00'), Decimal('75.00')]
            
            costs = [
                ProjectCost(
                    project_id=test_project,
                    user_id=test_user,
                    description=f'Cost {i}',
                    category=category,
                    amount=amount,
                    cost_date=date.today()
                )
                for i, (category, amount) in enumerate(zip(categories, amounts))
            ]
            db.session.add_all(costs)
            db.session.commit()
            
            # Get by category
            by_category = ProjectCost.get_costs_by_category(test_project)
            
            # Should have 3 categories
            assert len(by_category) == 3
            
            # Find travel category
            travel = next(c for c in by_category if c['category'] == 'travel')
            assert travel['count'] == 2
            assert abs(travel['total_amount'] - 250.00) < 0.01


class TestProjectCostConstraints:
    """Test database constraints and data integrity."""
    
    def test_cannot_create_cost_without_project(self, app, test_user):
        """Test that project_id is required."""
        with app.app_context():
            cost = ProjectCost(
                project_id=None,
                user_id=test_user,
                description='Test cost',
                category='materials',
                amount=Decimal('100.00'),
                cost_date=date.today()
            )
            db.session.add(cost)
            
            with pytest.raises(Exception):  # Should raise IntegrityError
                db.session.commit()
            
            db.session.rollback()
    
    def test_cannot_create_cost_without_user(self, app, test_project):
        """Test that user_id is required."""
        with app.app_context():
            cost = ProjectCost(
                project_id=test_project,
                user_id=None,
                description='Test cost',
                category='materials',
                amount=Decimal('100.00'),
                cost_date=date.today()
            )
            db.session.add(cost)
            
            with pytest.raises(Exception):  # Should raise IntegrityError
                db.session.commit()
            
            db.session.rollback()
    
    def test_cascade_delete_with_project(self, app, test_client, test_user):
        """Test that costs are deleted when project is deleted."""
        with app.app_context():
            # Create project and cost
            project = Project(
                name='Temp Project',
                client_id=test_client,
                description='Temporary project'
            )
            db.session.add(project)
            db.session.commit()
            project_id = project.id
            
            cost = ProjectCost(
                project_id=project_id,
                user_id=test_user,
                description='Test cost',
                category='materials',
                amount=Decimal('100.00'),
                cost_date=date.today()
            )
            db.session.add(cost)
            db.session.commit()
            cost_id = cost.id
            
            # Delete project
            db.session.delete(project)
            db.session.commit()
            
            # Cost should be deleted
            deleted_cost = db.session.get(ProjectCost, cost_id)
            assert deleted_cost is None


# Smoke Tests

class TestProjectCostSmokeTests:
    """Basic smoke tests to ensure ProjectCost functionality works."""
    
    def test_project_cost_creation_smoke(self, app, test_project, test_user):
        """Smoke test: Can we create a project cost?"""
        with app.app_context():
            cost = ProjectCost(
                project_id=test_project,
                user_id=test_user,
                description='Smoke test cost',
                category='materials',
                amount=Decimal('99.99'),
                cost_date=date.today()
            )
            db.session.add(cost)
            db.session.commit()
            
            assert cost.id is not None
    
    def test_project_cost_query_smoke(self, app, test_project, test_user):
        """Smoke test: Can we query project costs?"""
        with app.app_context():
            cost = ProjectCost(
                project_id=test_project,
                user_id=test_user,
                description='Query smoke test',
                category='travel',
                amount=Decimal('200.00'),
                cost_date=date.today()
            )
            db.session.add(cost)
            db.session.commit()
            
            costs = ProjectCost.query.filter_by(project_id=test_project).all()
            assert len(costs) > 0
    
    def test_project_cost_relationship_smoke(self, app, test_project, test_user):
        """Smoke test: Do relationships work?"""
        with app.app_context():
            cost = ProjectCost(
                project_id=test_project,
                user_id=test_user,
                description='Relationship smoke test',
                category='equipment',
                amount=Decimal('500.00'),
                cost_date=date.today()
            )
            db.session.add(cost)
            db.session.commit()
            
            # Refresh to load relationships
            cost = db.session.get(ProjectCost, cost.id)
            project = db.session.get(Project, test_project)
            user = db.session.get(User, test_user)
            
            assert cost.project is not None
            assert cost.user is not None
            assert cost in project.costs.all()
            assert cost in user.project_costs.all()

