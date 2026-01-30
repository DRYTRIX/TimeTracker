"""Tests for inventory routes"""

import pytest
from decimal import Decimal
from flask import url_for
from app import db
from app.models import Warehouse, StockItem, WarehouseStock, StockMovement, StockLot, User


@pytest.fixture
def test_user(db_session):
    """Create a test user"""
    user = User(username="testuser", role="admin")
    user.set_password("testpass")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_warehouse(db_session, test_user):
    """Create a test warehouse"""
    warehouse = Warehouse(name="Test Warehouse", code="WH-TEST", created_by=test_user.id)
    db_session.add(warehouse)
    db_session.commit()
    return warehouse


@pytest.fixture
def test_stock_item(db_session, test_user):
    """Create a test stock item (trackable with default_cost for devaluation tests)."""
    item = StockItem(
        sku="TEST-001",
        name="Test Product",
        created_by=test_user.id,
        default_price=Decimal("10.00"),
        default_cost=Decimal("5.00"),
        is_trackable=True,
    )
    db_session.add(item)
    db_session.commit()
    return item


class TestStockItemsRoutes:
    """Test stock items routes"""

    def test_list_stock_items(self, client, test_user, test_stock_item):
        """Test listing stock items"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        response = client.get(url_for("inventory.list_stock_items"))
        assert response.status_code == 200
        assert b"Stock Items" in response.data
        assert b"TEST-001" in response.data

    def test_create_stock_item(self, client, test_user):
        """Test creating a stock item"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        response = client.post(
            url_for("inventory.new_stock_item"),
            data={
                "sku": "NEW-001",
                "name": "New Product",
                "unit": "pcs",
                "default_price": "15.00",
                "is_active": "on",
                "is_trackable": "on",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        # Check if item was created
        item = StockItem.query.filter_by(sku="NEW-001").first()
        assert item is not None
        assert item.name == "New Product"

    def test_view_stock_item(self, client, test_user, test_stock_item):
        """Test viewing stock item details"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        response = client.get(url_for("inventory.view_stock_item", item_id=test_stock_item.id))
        assert response.status_code == 200
        assert b"TEST-001" in response.data
        assert b"Test Product" in response.data

    def test_edit_stock_item(self, client, test_user, test_stock_item):
        """Test editing stock item"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        response = client.post(
            url_for("inventory.edit_stock_item", item_id=test_stock_item.id),
            data={
                "sku": "TEST-001",
                "name": "Updated Product",
                "unit": "pcs",
                "default_price": "20.00",
                "is_active": "on",
                "is_trackable": "on",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        db.session.refresh(test_stock_item)
        assert test_stock_item.name == "Updated Product"


class TestWarehousesRoutes:
    """Test warehouses routes"""

    def test_list_warehouses(self, client, test_user, test_warehouse):
        """Test listing warehouses"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        response = client.get(url_for("inventory.list_warehouses"))
        assert response.status_code == 200
        assert b"Warehouses" in response.data
        assert b"WH-TEST" in response.data

    def test_create_warehouse(self, client, test_user):
        """Test creating a warehouse"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        response = client.post(
            url_for("inventory.new_warehouse"),
            data={"name": "New Warehouse", "code": "WH-NEW", "is_active": "on"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        warehouse = Warehouse.query.filter_by(code="WH-NEW").first()
        assert warehouse is not None
        assert warehouse.name == "New Warehouse"

    def test_view_warehouse(self, client, test_user, test_warehouse):
        """Test viewing warehouse details"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        response = client.get(url_for("inventory.view_warehouse", warehouse_id=test_warehouse.id))
        assert response.status_code == 200
        assert b"WH-TEST" in response.data
        assert b"Test Warehouse" in response.data


class TestStockLevelsRoutes:
    """Test stock levels routes"""

    def test_view_stock_levels(self, client, test_user, test_stock_item, test_warehouse):
        """Test viewing stock levels"""
        # Create stock
        stock = WarehouseStock(
            warehouse_id=test_warehouse.id, stock_item_id=test_stock_item.id, quantity_on_hand=Decimal("100.00")
        )
        db.session.add(stock)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        response = client.get(url_for("inventory.stock_levels"))
        assert response.status_code == 200
        assert b"Stock Levels" in response.data


class TestStockMovementsRoutes:
    """Test stock movements routes"""

    def test_list_movements(self, client, test_user):
        """Test listing stock movements"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        response = client.get(url_for("inventory.list_movements"))
        assert response.status_code == 200
        assert b"Stock Movements" in response.data

    def test_create_movement(self, client, test_user, test_stock_item, test_warehouse):
        """Test creating a stock movement"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        response = client.post(
            url_for("inventory.new_movement"),
            data={
                "movement_type": "adjustment",
                "stock_item_id": test_stock_item.id,
                "warehouse_id": test_warehouse.id,
                "quantity": "50.00",
                "reason": "Initial stock",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        # Check if stock was updated
        stock = WarehouseStock.query.filter_by(warehouse_id=test_warehouse.id, stock_item_id=test_stock_item.id).first()
        assert stock is not None
        assert stock.quantity_on_hand == Decimal("50.00")

    def test_create_return_with_devaluation(self, client, test_user, test_stock_item, test_warehouse):
        """Test recording a return with devaluation creates a devalued lot."""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        response = client.post(
            url_for("inventory.new_movement"),
            data={
                "movement_type": "return",
                "stock_item_id": test_stock_item.id,
                "warehouse_id": test_warehouse.id,
                "quantity": "5.00",
                "devalue_enabled": "on",
                "devalue_method": "fixed",
                "devalue_unit_cost": "2.50",
                "reason": "Returned with damage",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"devaluation" in response.data.lower() or b"success" in response.data.lower()

        stock = WarehouseStock.query.filter_by(
            warehouse_id=test_warehouse.id, stock_item_id=test_stock_item.id
        ).first()
        assert stock is not None
        assert stock.quantity_on_hand == Decimal("5.00")

        lots = StockLot.query.filter_by(
            stock_item_id=test_stock_item.id, warehouse_id=test_warehouse.id
        ).all()
        assert len(lots) >= 1
        devalued = [l for l in lots if l.lot_type == "devalued"]
        assert len(devalued) >= 1
        assert any(Decimal(str(l.quantity_on_hand)) == Decimal("5.00") for l in devalued)
        assert any(Decimal(str(l.unit_cost)) == Decimal("2.50") for l in devalued)

    def test_create_waste_with_devaluation(self, client, test_user, test_stock_item, test_warehouse):
        """Test recording waste with devaluation consumes from a devalued lot."""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        # Create stock first via purchase
        StockMovement.record_movement(
            movement_type="purchase",
            stock_item_id=test_stock_item.id,
            warehouse_id=test_warehouse.id,
            quantity=Decimal("10.00"),
            moved_by=test_user.id,
            unit_cost=Decimal("5.00"),
            update_stock=True,
        )
        db.session.commit()

        response = client.post(
            url_for("inventory.new_movement"),
            data={
                "movement_type": "waste",
                "stock_item_id": test_stock_item.id,
                "warehouse_id": test_warehouse.id,
                "quantity": "-4.00",
                "devalue_enabled": "on",
                "devalue_method": "fixed",
                "devalue_unit_cost": "1.00",
                "reason": "Wasted impaired items",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"devaluation" in response.data.lower() or b"success" in response.data.lower()

        stock = WarehouseStock.query.filter_by(
            warehouse_id=test_warehouse.id, stock_item_id=test_stock_item.id
        ).first()
        assert stock is not None
        assert stock.quantity_on_hand == Decimal("6.00")

        lots = StockLot.query.filter_by(
            stock_item_id=test_stock_item.id, warehouse_id=test_warehouse.id
        ).all()
        devalued = [l for l in lots if l.lot_type == "devalued"]
        assert any(Decimal(str(l.quantity_on_hand)) == Decimal("0.00") for l in devalued)
