"""Tests for PurchaseOrder model"""

import pytest
from decimal import Decimal
from datetime import date, datetime
from app import db
from app.models import PurchaseOrder, PurchaseOrderItem, Supplier, StockItem, Warehouse, User


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
    supplier = Supplier(code="SUP-001", name="Test Supplier", created_by=test_user.id)
    db_session.add(supplier)
    db_session.commit()
    return supplier


@pytest.fixture
def test_warehouse(db_session, test_user):
    """Create a test warehouse"""
    warehouse = Warehouse(name="Test Warehouse", code="WH-001", created_by=test_user.id)
    db_session.add(warehouse)
    db_session.commit()
    return warehouse


@pytest.fixture
def test_stock_item(db_session, test_user):
    """Create a test stock item"""
    item = StockItem(sku="ITEM-001", name="Test Item", created_by=test_user.id, default_cost=Decimal("5.00"))
    db_session.add(item)
    db_session.commit()
    return item


@pytest.fixture
def test_purchase_order(db_session, test_supplier, test_user):
    """Create a test purchase order"""
    po = PurchaseOrder(
        po_number="PO-TEST-001",
        supplier_id=test_supplier.id,
        order_date=date.today(),
        created_by=test_user.id,
        currency_code="EUR",
    )
    db_session.add(po)
    db_session.commit()
    return po


class TestPurchaseOrder:
    """Test PurchaseOrder model"""

    def test_create_purchase_order(self, db_session, test_supplier, test_user):
        """Test creating a purchase order"""
        po = PurchaseOrder(
            po_number="PO-001",
            supplier_id=test_supplier.id,
            order_date=date.today(),
            created_by=test_user.id,
            currency_code="EUR",
        )
        db_session.add(po)
        db_session.commit()

        assert po.id is not None
        assert po.po_number == "PO-001"
        assert po.status == "draft"
        assert po.supplier_id == test_supplier.id

    def test_purchase_order_with_items(self, db_session, test_purchase_order, test_stock_item, test_warehouse):
        """Test purchase order with items"""
        item = PurchaseOrderItem(
            purchase_order_id=test_purchase_order.id,
            description="Test Item",
            quantity_ordered=Decimal("10.00"),
            unit_cost=Decimal("5.00"),
            stock_item_id=test_stock_item.id,
            warehouse_id=test_warehouse.id,
        )
        db_session.add(item)
        test_purchase_order.calculate_totals()
        db_session.commit()

        assert len(test_purchase_order.items) == 1
        assert test_purchase_order.total_amount == Decimal("50.00")

    def test_purchase_order_receive(self, db_session, test_purchase_order, test_stock_item, test_warehouse):
        """Test receiving a purchase order"""
        # Add item to PO
        item = PurchaseOrderItem(
            purchase_order_id=test_purchase_order.id,
            description="Test Item",
            quantity_ordered=Decimal("10.00"),
            unit_cost=Decimal("5.00"),
            stock_item_id=test_stock_item.id,
            warehouse_id=test_warehouse.id,
        )
        db_session.add(item)
        test_purchase_order.calculate_totals()
        db_session.commit()

        # Receive the PO
        test_purchase_order.mark_as_received(date.today())
        db_session.commit()

        assert test_purchase_order.status == "received"
        assert test_purchase_order.received_date == date.today()

    def test_purchase_order_cancel(self, db_session, test_purchase_order):
        """Test cancelling a purchase order"""
        test_purchase_order.cancel()
        db_session.commit()

        assert test_purchase_order.status == "cancelled"

    def test_purchase_order_to_dict(self, db_session, test_purchase_order):
        """Test purchase order to_dict method"""
        data = test_purchase_order.to_dict()
        assert data["po_number"] == "PO-TEST-001"
        assert data["status"] == "draft"
        assert "created_at" in data
        assert "items" in data
