"""Tests for purchase order routes"""

import pytest
from decimal import Decimal
from datetime import date
from flask import url_for
from app import db
from app.models import PurchaseOrder, PurchaseOrderItem, Supplier, StockItem, Warehouse, User


@pytest.fixture
def test_user(db_session):
    """Create a test user"""
    user = User(username="testuser", role="admin")
    user.set_password("testpass")
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


class TestPurchaseOrderRoutes:
    """Test purchase order routes"""

    def test_list_purchase_orders(self, client, test_user, test_purchase_order):
        """Test listing purchase orders"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        response = client.get(url_for("inventory.list_purchase_orders"))
        assert response.status_code == 200
        assert b"Purchase Orders" in response.data
        assert b"PO-TEST-001" in response.data

    def test_create_purchase_order(self, client, test_user, test_supplier, test_stock_item, test_warehouse):
        """Test creating a purchase order"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        response = client.post(
            url_for("inventory.new_purchase_order"),
            data={
                "supplier_id": test_supplier.id,
                "order_date": date.today().isoformat(),
                "currency_code": "EUR",
                "items-0-description": "Test Item",
                "items-0-quantity_ordered": "10",
                "items-0-unit_cost": "5.00",
                "items-0-stock_item_id": str(test_stock_item.id),
                "items-0-warehouse_id": str(test_warehouse.id),
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        # Check if PO was created
        po = PurchaseOrder.query.filter_by(supplier_id=test_supplier.id).order_by(PurchaseOrder.id.desc()).first()
        assert po is not None
        assert po.status == "draft"

    def test_view_purchase_order(self, client, test_user, test_purchase_order):
        """Test viewing purchase order details"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        response = client.get(url_for("inventory.view_purchase_order", po_id=test_purchase_order.id))
        assert response.status_code == 200
        assert b"PO-TEST-001" in response.data

    def test_edit_purchase_order(self, client, test_user, test_purchase_order):
        """Test editing a draft purchase order"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        response = client.post(
            url_for("inventory.edit_purchase_order", po_id=test_purchase_order.id),
            data={
                "order_date": date.today().isoformat(),
                "notes": "Updated notes",
                "currency_code": "EUR",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        # Check if PO was updated
        db.session.refresh(test_purchase_order)
        assert test_purchase_order.notes == "Updated notes"

    def test_receive_purchase_order(self, client, test_user, test_purchase_order, test_stock_item, test_warehouse):
        """Test receiving a purchase order"""
        # Add item to PO first
        item = PurchaseOrderItem(
            purchase_order_id=test_purchase_order.id,
            description="Test Item",
            quantity_ordered=Decimal("10.00"),
            unit_cost=Decimal("5.00"),
            stock_item_id=test_stock_item.id,
            warehouse_id=test_warehouse.id,
        )
        db.session.add(item)
        test_purchase_order.calculate_totals()
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        response = client.post(
            url_for("inventory.receive_purchase_order", po_id=test_purchase_order.id),
            data={"received_date": date.today().isoformat()},
            follow_redirects=True,
        )

        assert response.status_code == 200
        # Check if PO was received
        db.session.refresh(test_purchase_order)
        assert test_purchase_order.status == "received"

    def test_cancel_purchase_order(self, client, test_user, test_purchase_order):
        """Test cancelling a purchase order"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        response = client.post(
            url_for("inventory.cancel_purchase_order", po_id=test_purchase_order.id),
            follow_redirects=True,
        )

        assert response.status_code == 200
        # Check if PO was cancelled
        db.session.refresh(test_purchase_order)
        assert test_purchase_order.status == "cancelled"

    def test_delete_purchase_order(self, client, test_user, test_purchase_order):
        """Test deleting a draft purchase order"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        response = client.post(
            url_for("inventory.delete_purchase_order", po_id=test_purchase_order.id),
            follow_redirects=True,
        )

        assert response.status_code == 200
        # Check if PO was deleted
        po = PurchaseOrder.query.get(test_purchase_order.id)
        assert po is None
