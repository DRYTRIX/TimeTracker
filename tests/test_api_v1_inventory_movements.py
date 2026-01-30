"""Tests for API v1 inventory movements (including return/waste with devaluation)."""

import json
import pytest
from decimal import Decimal
from flask import url_for
from app import db
from app.models import (
    User,
    ApiToken,
    Warehouse,
    StockItem,
    WarehouseStock,
    StockMovement,
    StockLot,
)


@pytest.fixture
def api_token(db_session, test_user):
    """Create an API token with write:projects (used for inventory movements)."""
    token, plain_token = ApiToken.create_token(
        user_id=test_user.id,
        name="Inventory Test Token",
        description="For inventory API tests",
        scopes="read:projects,write:projects",
    )
    db.session.add(token)
    db.session.commit()
    return plain_token


@pytest.fixture
def test_warehouse(db_session, test_user):
    """Create a test warehouse."""
    warehouse = Warehouse(name="API Test Warehouse", code="WH-API", created_by=test_user.id)
    db.session.add(warehouse)
    db.session.commit()
    return warehouse


@pytest.fixture
def test_stock_item_trackable(db_session, test_user):
    """Create a trackable stock item with default_cost for devaluation tests."""
    item = StockItem(
        sku="API-TEST-001",
        name="API Test Product",
        created_by=test_user.id,
        default_price=Decimal("10.00"),
        default_cost=Decimal("5.00"),
        is_trackable=True,
    )
    db.session.add(item)
    db.session.commit()
    return item


class TestInventoryMovementsAPI:
    """Test POST /api/v1/inventory/movements with return/waste devaluation."""

    def test_create_return_with_devaluation(
        self, client, test_user, api_token, test_stock_item_trackable, test_warehouse
    ):
        """POST return movement with devalue_enabled creates a devalued lot."""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
        payload = {
            "movement_type": "return",
            "stock_item_id": test_stock_item_trackable.id,
            "warehouse_id": test_warehouse.id,
            "quantity": "5.00",
            "devalue_enabled": True,
            "devalue_method": "fixed",
            "devalue_unit_cost": "2.50",
            "reason": "Returned with damage (API)",
        }

        response = client.post("/api/v1/inventory/movements", data=json.dumps(payload), headers=headers)

        assert response.status_code == 201
        data = response.get_json()
        assert "message" in data
        assert "movement" in data
        assert data["movement"]["movement_type"] == "return"
        assert float(data["movement"]["quantity"]) == 5.0

        stock = WarehouseStock.query.filter_by(
            warehouse_id=test_warehouse.id, stock_item_id=test_stock_item_trackable.id
        ).first()
        assert stock is not None
        assert stock.quantity_on_hand == Decimal("5.00")

        lots = StockLot.query.filter_by(
            stock_item_id=test_stock_item_trackable.id, warehouse_id=test_warehouse.id
        ).all()
        assert len(lots) >= 1
        devalued = [l for l in lots if l.lot_type == "devalued"]
        assert len(devalued) >= 1
        assert any(Decimal(str(l.quantity_on_hand)) == Decimal("5.00") for l in devalued)
        assert any(Decimal(str(l.unit_cost)) == Decimal("2.50") for l in devalued)

    def test_create_waste_with_devaluation(
        self, client, test_user, api_token, test_stock_item_trackable, test_warehouse
    ):
        """POST waste movement with devalue_enabled consumes from a devalued lot."""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        # Create stock first via model (no API for simple purchase in this test)
        StockMovement.record_movement(
            movement_type="purchase",
            stock_item_id=test_stock_item_trackable.id,
            warehouse_id=test_warehouse.id,
            quantity=Decimal("10.00"),
            moved_by=test_user.id,
            unit_cost=Decimal("5.00"),
            update_stock=True,
        )
        db.session.commit()

        headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
        payload = {
            "movement_type": "waste",
            "stock_item_id": test_stock_item_trackable.id,
            "warehouse_id": test_warehouse.id,
            "quantity": "-4.00",
            "devalue_enabled": True,
            "devalue_method": "fixed",
            "devalue_unit_cost": "1.00",
            "reason": "Wasted impaired items (API)",
        }

        response = client.post("/api/v1/inventory/movements", data=json.dumps(payload), headers=headers)

        assert response.status_code == 201
        data = response.get_json()
        assert "message" in data
        assert "movement" in data
        assert data["movement"]["movement_type"] == "waste"
        assert float(data["movement"]["quantity"]) == -4.0

        stock = WarehouseStock.query.filter_by(
            warehouse_id=test_warehouse.id, stock_item_id=test_stock_item_trackable.id
        ).first()
        assert stock is not None
        assert stock.quantity_on_hand == Decimal("6.00")

        lots = StockLot.query.filter_by(
            stock_item_id=test_stock_item_trackable.id, warehouse_id=test_warehouse.id
        ).all()
        devalued = [l for l in lots if l.lot_type == "devalued"]
        assert any(Decimal(str(l.quantity_on_hand)) == Decimal("0.00") for l in devalued)
