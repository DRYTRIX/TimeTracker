"""Tests for Supplier model"""

import pytest
from decimal import Decimal
from app import db
from app.models import Supplier, SupplierStockItem, StockItem, User


@pytest.fixture
def test_user(db_session):
    """Create a test user"""
    user = User(username="testuser", role="admin")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_supplier(db_session, test_user):
    """Create a test supplier"""
    supplier = Supplier(
        code="SUP-001",
        name="Test Supplier",
        created_by=test_user.id,
        email="supplier@test.com",
        phone="+1234567890",
    )
    db_session.add(supplier)
    db_session.commit()
    return supplier


@pytest.fixture
def test_stock_item(db_session, test_user):
    """Create a test stock item"""
    item = StockItem(
        sku="ITEM-001",
        name="Test Item",
        created_by=test_user.id,
        default_price=Decimal("10.00"),
    )
    db_session.add(item)
    db_session.commit()
    return item


class TestSupplier:
    """Test Supplier model"""

    def test_create_supplier(self, db_session, test_user):
        """Test creating a supplier"""
        supplier = Supplier(
            code="SUP-TEST",
            name="Test Supplier",
            created_by=test_user.id,
            email="test@supplier.com",
        )
        db_session.add(supplier)
        db_session.commit()

        assert supplier.id is not None
        assert supplier.code == "SUP-TEST"
        assert supplier.name == "Test Supplier"
        assert supplier.is_active is True

    def test_supplier_code_uppercase(self, db_session, test_user):
        """Test that supplier code is automatically uppercased"""
        supplier = Supplier(name="Test", code="sup-test", created_by=test_user.id)
        assert supplier.code == "SUP-TEST"

    def test_supplier_to_dict(self, db_session, test_supplier):
        """Test supplier to_dict method"""
        data = test_supplier.to_dict()
        assert data["code"] == "SUP-001"
        assert data["name"] == "Test Supplier"
        assert "created_at" in data

    def test_supplier_stock_items_relationship(self, db_session, test_supplier, test_stock_item):
        """Test supplier stock items relationship"""
        supplier_item = SupplierStockItem(
            supplier_id=test_supplier.id,
            stock_item_id=test_stock_item.id,
            supplier_sku="SUP-SKU-001",
            unit_cost=Decimal("8.00"),
        )
        db_session.add(supplier_item)
        db_session.commit()

        assert len(test_supplier.stock_items) == 1
        assert test_supplier.stock_items[0].stock_item_id == test_stock_item.id

    def test_supplier_deactivation(self, db_session, test_supplier):
        """Test supplier deactivation (soft delete)"""
        test_supplier.is_active = False
        db_session.commit()

        assert test_supplier.is_active is False
        # Supplier should still exist in database
        supplier = Supplier.query.get(test_supplier.id)
        assert supplier is not None
        assert supplier.is_active is False
