"""
Tests for ExtraGood model
"""
import pytest
from decimal import Decimal
from datetime import datetime
from app.models import ExtraGood, Project, User, Client, Invoice
from factories import InvoiceFactory


class TestExtraGoodModel:
    """Test cases for ExtraGood model"""
    
    def test_create_extra_good_for_project(self, app, db_session):
        """Test creating an extra good for a project"""
        # Create test data
        client = Client(name="Test Client")
        db_session.add(client)
        db_session.commit()
        
        user = User(username="testuser", email="test@example.com", role='user')
        user.password_hash = "hash"
        db_session.add(user)
        db_session.commit()
        
        project = Project(name="Test Project", client_id=client.id)
        db_session.add(project)
        db_session.commit()
        
        # Create extra good
        good = ExtraGood(
            name="Test Product",
            unit_price=100.00,
            quantity=5,
            created_by=user.id,
            project_id=project.id,
            description="Test description",
            category="product",
            sku="TEST-001"
        )
        db_session.add(good)
        db_session.commit()
        
        # Verify
        assert good.id is not None
        assert good.name == "Test Product"
        assert good.quantity == Decimal('5')
        assert good.unit_price == Decimal('100.00')
        assert good.total_amount == Decimal('500.00')
        assert good.project_id == project.id
        assert good.created_by == user.id
        assert good.category == "product"
        assert good.sku == "TEST-001"
    
    def test_create_extra_good_for_invoice(self, app, db_session):
        """Test creating an extra good for an invoice"""
        # Create test data
        client = Client(name="Test Client")
        db_session.add(client)
        db_session.commit()
        
        user = User(username="testuser", email="test@example.com", role='user')
        user.password_hash = "hash"
        db_session.add(user)
        db_session.commit()
        
        project = Project(name="Test Project", client_id=client.id)
        db_session.add(project)
        db_session.commit()
        
        invoice = InvoiceFactory(
            invoice_number="INV-001",
            project_id=project.id,
            client_name="Test Client",
            due_date=datetime.utcnow().date(),
            created_by=user.id,
            client_id=client.id,
            status='draft'
        )
        
        # Create extra good
        good = ExtraGood(
            name="License Fee",
            unit_price=500.00,
            quantity=1,
            created_by=user.id,
            invoice_id=invoice.id,
            category="license"
        )
        db_session.add(good)
        db_session.commit()
        
        # Verify
        assert good.id is not None
        assert good.invoice_id == invoice.id
        assert good.total_amount == Decimal('500.00')
    
    def test_update_total(self, app, db_session):
        """Test updating total when quantity or price changes"""
        user = User(username="testuser", email="test@example.com", role='user')
        user.password_hash = "hash"
        db_session.add(user)
        db_session.commit()
        
        good = ExtraGood(
            name="Test Good",
            unit_price=10.00,
            quantity=2,
            created_by=user.id
        )
        db_session.add(good)
        db_session.commit()
        
        # Change quantity and update total
        good.quantity = Decimal('5')
        good.update_total()
        
        assert good.total_amount == Decimal('50.00')
        
        # Change unit price and update total
        good.unit_price = Decimal('15.00')
        good.update_total()
        
        assert good.total_amount == Decimal('75.00')
    
    def test_to_dict(self, app, db_session):
        """Test converting extra good to dictionary"""
        user = User(username="testuser", email="test@example.com", role='user')
        user.password_hash = "hash"
        db_session.add(user)
        db_session.commit()
        
        good = ExtraGood(
            name="Test Product",
            unit_price=100.00,
            quantity=2,
            created_by=user.id,
            description="Test desc",
            category="product",
            sku="SKU-123"
        )
        db_session.add(good)
        db_session.commit()
        
        data = good.to_dict()
        
        assert data['name'] == "Test Product"
        assert data['quantity'] == 2.0
        assert data['unit_price'] == 100.0
        assert data['total_amount'] == 200.0
        assert data['category'] == "product"
        assert data['sku'] == "SKU-123"
        assert data['creator'] == "testuser"
    
    def test_get_project_goods(self, app, db_session):
        """Test getting goods for a project"""
        client = Client(name="Test Client")
        db_session.add(client)
        db_session.commit()
        
        user = User(username="testuser", email="test@example.com", role='user')
        user.password_hash = "hash"
        db_session.add(user)
        db_session.commit()
        
        project = Project(name="Test Project", client_id=client.id)
        db_session.add(project)
        db_session.commit()
        
        # Create multiple goods
        good1 = ExtraGood(name="Good 1", unit_price=10, quantity=1, created_by=user.id, project_id=project.id, billable=True)
        good2 = ExtraGood(name="Good 2", unit_price=20, quantity=1, created_by=user.id, project_id=project.id, billable=False)
        good3 = ExtraGood(name="Good 3", unit_price=30, quantity=1, created_by=user.id, project_id=project.id, billable=True)
        db_session.add_all([good1, good2, good3])
        db_session.commit()
        
        # Get all goods
        all_goods = ExtraGood.get_project_goods(project.id)
        assert len(all_goods) == 3
        
        # Get only billable goods
        billable_goods = ExtraGood.get_project_goods(project.id, billable_only=True)
        assert len(billable_goods) == 2
    
    def test_get_total_amount(self, app, db_session):
        """Test calculating total amount for goods"""
        client = Client(name="Test Client")
        db_session.add(client)
        db_session.commit()
        
        user = User(username="testuser", email="test@example.com", role='user')
        user.password_hash = "hash"
        db_session.add(user)
        db_session.commit()
        
        project = Project(name="Test Project", client_id=client.id)
        db_session.add(project)
        db_session.commit()
        
        # Create goods with different amounts
        good1 = ExtraGood(name="Good 1", unit_price=100, quantity=2, created_by=user.id, project_id=project.id, billable=True)
        good2 = ExtraGood(name="Good 2", unit_price=50, quantity=3, created_by=user.id, project_id=project.id, billable=False)
        db_session.add_all([good1, good2])
        db_session.commit()
        
        # Total of all goods: 200 + 150 = 350
        total = ExtraGood.get_total_amount(project_id=project.id)
        assert total == 350.0
        
        # Total of billable goods only: 200
        billable_total = ExtraGood.get_total_amount(project_id=project.id, billable_only=True)
        assert billable_total == 200.0
    
    def test_get_goods_by_category(self, app, db_session):
        """Test grouping goods by category"""
        client = Client(name="Test Client")
        db_session.add(client)
        db_session.commit()
        
        user = User(username="testuser", email="test@example.com", role='user')
        user.password_hash = "hash"
        db_session.add(user)
        db_session.commit()
        
        project = Project(name="Test Project", client_id=client.id)
        db_session.add(project)
        db_session.commit()
        
        # Create goods in different categories
        good1 = ExtraGood(name="Product 1", unit_price=100, quantity=1, created_by=user.id, project_id=project.id, category="product")
        good2 = ExtraGood(name="Product 2", unit_price=150, quantity=1, created_by=user.id, project_id=project.id, category="product")
        good3 = ExtraGood(name="Service 1", unit_price=200, quantity=1, created_by=user.id, project_id=project.id, category="service")
        db_session.add_all([good1, good2, good3])
        db_session.commit()
        
        breakdown = ExtraGood.get_goods_by_category(project_id=project.id)
        
        assert len(breakdown) == 2
        
        # Find product category
        product_cat = next((c for c in breakdown if c['category'] == 'product'), None)
        assert product_cat is not None
        assert product_cat['total_amount'] == 250.0
        assert product_cat['count'] == 2
        
        # Find service category
        service_cat = next((c for c in breakdown if c['category'] == 'service'), None)
        assert service_cat is not None
        assert service_cat['total_amount'] == 200.0
        assert service_cat['count'] == 1

