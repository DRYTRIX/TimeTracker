"""Tests for API v1 inventory reports (valuation, movement-history, turnover, low-stock)."""

import pytest

pytestmark = [pytest.mark.api, pytest.mark.integration]

from decimal import Decimal

from app import db
from app.models import (
    ApiToken,
    Warehouse,
    StockItem,
    WarehouseStock,
    StockMovement,
)


@pytest.fixture
def api_token(db_session, test_user):
    """Create an API token with read:projects (used for inventory reports)."""
    token, plain_token = ApiToken.create_token(
        user_id=test_user.id,
        name="Inventory Reports Test Token",
        description="For inventory report API tests",
        scopes="read:projects",
    )
    db.session.add(token)
    db.session.commit()
    return plain_token


@pytest.fixture
def warehouse(db_session, test_user):
    """Test warehouse."""
    wh = Warehouse(name="Report Warehouse", code="WH-RPT", created_by=test_user.id)
    db.session.add(wh)
    db.session.commit()
    return wh


@pytest.fixture
def stock_item_with_cost(db_session, test_user):
    """Stock item with default cost for valuation."""
    item = StockItem(
        sku="REPORT-001",
        name="Report Test Item",
        created_by=test_user.id,
        default_price=Decimal("20.00"),
        default_cost=Decimal("8.00"),
        is_trackable=True,
        category="TestCategory",
        currency_code="EUR",
    )
    db.session.add(item)
    db.session.commit()
    return item


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


class TestInventoryScopes:
    """Test read:inventory / write:inventory and backward compatibility with read:projects / write:projects."""

    def test_read_inventory_only_can_access_inventory(self, client, db_session, test_user):
        """Token with only read:inventory can GET inventory endpoints."""
        token, plain = ApiToken.create_token(
            user_id=test_user.id, name="Inv Only", scopes="read:inventory"
        )
        db.session.add(token)
        db.session.commit()
        response = client.get("/api/v1/inventory/reports/valuation", headers=_auth_headers(plain))
        assert response.status_code == 200

    def test_read_inventory_only_cannot_access_projects(self, client, db_session, test_user):
        """Token with only read:inventory cannot GET non-inventory project endpoints."""
        token, plain = ApiToken.create_token(
            user_id=test_user.id, name="Inv Only", scopes="read:inventory"
        )
        db.session.add(token)
        db.session.commit()
        response = client.get("/api/v1/projects", headers=_auth_headers(plain))
        assert response.status_code == 403

    def test_read_projects_still_grants_inventory(self, client, api_token):
        """Token with only read:projects can still GET inventory (backward compatibility)."""
        response = client.get("/api/v1/inventory/reports/valuation", headers=_auth_headers(api_token))
        assert response.status_code == 200


class TestValuationReportAPI:
    """GET /api/v1/inventory/reports/valuation"""

    def test_valuation_report_empty(self, client, api_token):
        """Valuation with no stock returns zero total and empty details."""
        response = client.get("/api/v1/inventory/reports/valuation", headers=_auth_headers(api_token))
        assert response.status_code == 200
        data = response.get_json()
        assert "total_value" in data
        assert data["total_value"] == 0.0 or data["total_value"] >= 0
        assert "item_details" in data
        assert "by_warehouse" in data
        assert "by_category" in data

    def test_valuation_report_with_stock(
        self, client, api_token, stock_item_with_cost, warehouse, test_user
    ):
        """Valuation with stock returns total_value and item_details."""
        StockMovement.record_movement(
            movement_type="purchase",
            stock_item_id=stock_item_with_cost.id,
            warehouse_id=warehouse.id,
            quantity=Decimal("10"),
            moved_by=test_user.id,
            unit_cost=Decimal("8.00"),
            update_stock=True,
        )
        db.session.commit()

        response = client.get("/api/v1/inventory/reports/valuation", headers=_auth_headers(api_token))
        assert response.status_code == 200
        data = response.get_json()
        assert data["total_value"] == 80.0  # 10 * 8
        assert len(data["item_details"]) >= 1
        detail = next((d for d in data["item_details"] if d["item_id"] == stock_item_with_cost.id), None)
        assert detail is not None
        assert detail["quantity"] == 10.0
        assert detail["value"] == 80.0

    def test_valuation_report_filter_warehouse(
        self, client, api_token, stock_item_with_cost, warehouse, test_user
    ):
        """Valuation with warehouse_id filter returns only that warehouse."""
        StockMovement.record_movement(
            movement_type="purchase",
            stock_item_id=stock_item_with_cost.id,
            warehouse_id=warehouse.id,
            quantity=Decimal("5"),
            moved_by=test_user.id,
            update_stock=True,
        )
        db.session.commit()

        response = client.get(
            f"/api/v1/inventory/reports/valuation?warehouse_id={warehouse.id}",
            headers=_auth_headers(api_token),
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["warehouse_id"] == warehouse.id
        assert all(d["warehouse_id"] == warehouse.id for d in data["item_details"])

    def test_valuation_unauthorized(self, client):
        """Valuation without token returns 401."""
        response = client.get("/api/v1/inventory/reports/valuation")
        assert response.status_code == 401

    def test_valuation_invalid_warehouse_id(self, client, api_token):
        """Valuation with invalid warehouse_id (e.g. non-numeric) returns 200 with full data or 400."""
        response = client.get(
            "/api/v1/inventory/reports/valuation?warehouse_id=invalid",
            headers=_auth_headers(api_token),
        )
        assert response.status_code in (200, 400)
        if response.status_code == 200:
            data = response.get_json()
            assert "total_value" in data
            assert "item_details" in data


class TestMovementHistoryReportAPI:
    """GET /api/v1/inventory/reports/movement-history"""

    def test_movement_history_empty(self, client, api_token):
        """Movement history with no movements returns empty list."""
        response = client.get(
            "/api/v1/inventory/reports/movement-history",
            headers=_auth_headers(api_token),
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "movements" in data
        assert data["movements"] == []
        assert data["total_movements"] == 0

    def test_movement_history_with_data(
        self, client, api_token, stock_item_with_cost, warehouse, test_user
    ):
        """Movement history returns movements after recording one."""
        StockMovement.record_movement(
            movement_type="adjustment",
            stock_item_id=stock_item_with_cost.id,
            warehouse_id=warehouse.id,
            quantity=Decimal("5"),
            moved_by=test_user.id,
            reason="Test",
            update_stock=True,
        )
        db.session.commit()

        response = client.get(
            "/api/v1/inventory/reports/movement-history",
            headers=_auth_headers(api_token),
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["total_movements"] >= 1
        assert len(data["movements"]) >= 1
        m = data["movements"][0]
        assert "id" in m
        assert "date" in m
        assert m["item_id"] == stock_item_with_cost.id
        assert m["quantity"] == 5.0
        assert m["type"] == "adjustment"

    def test_movement_history_paginated(self, client, api_token):
        """Movement history with page and per_page returns pagination."""
        response = client.get(
            "/api/v1/inventory/reports/movement-history?page=1&per_page=5",
            headers=_auth_headers(api_token),
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "movements" in data
        assert "pagination" in data
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["per_page"] == 5

    def test_movement_history_unauthorized(self, client):
        """Movement history without token returns 401."""
        response = client.get("/api/v1/inventory/reports/movement-history")
        assert response.status_code == 401

    def test_movement_history_invalid_pagination(self, client, api_token):
        """Movement history with invalid page/per_page returns 200 with safe defaults or 400."""
        response = client.get(
            "/api/v1/inventory/reports/movement-history?page=x&per_page=y",
            headers=_auth_headers(api_token),
        )
        assert response.status_code in (200, 400)
        if response.status_code == 200:
            data = response.get_json()
            assert "movements" in data
            assert "total_movements" in data or "pagination" in data


class TestTurnoverReportAPI:
    """GET /api/v1/inventory/reports/turnover"""

    def test_turnover_report_structure(self, client, api_token):
        """Turnover report returns start_date, end_date, items."""
        response = client.get("/api/v1/inventory/reports/turnover", headers=_auth_headers(api_token))
        assert response.status_code == 200
        data = response.get_json()
        assert "start_date" in data
        assert "end_date" in data
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_turnover_report_with_dates(self, client, api_token):
        """Turnover with start_date and end_date returns in range."""
        response = client.get(
            "/api/v1/inventory/reports/turnover?start_date=2024-01-01&end_date=2024-12-31",
            headers=_auth_headers(api_token),
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "2024-01-01" in data["start_date"] or data["start_date"].startswith("2024")
        assert "2024-12-31" in data["end_date"] or data["end_date"].startswith("2024")

    def test_turnover_unauthorized(self, client):
        """Turnover without token returns 401."""
        response = client.get("/api/v1/inventory/reports/turnover")
        assert response.status_code == 401

    def test_turnover_invalid_dates(self, client, api_token):
        """Turnover with invalid start_date/end_date returns 200 with defaults or 400."""
        response = client.get(
            "/api/v1/inventory/reports/turnover?start_date=not-a-date&end_date=invalid",
            headers=_auth_headers(api_token),
        )
        assert response.status_code in (200, 400)
        if response.status_code == 200:
            data = response.get_json()
            assert "items" in data
            assert "start_date" in data
            assert "end_date" in data


class TestLowStockReportAPI:
    """GET /api/v1/inventory/reports/low-stock"""

    def test_low_stock_report_empty(self, client, api_token):
        """Low-stock with no items below reorder returns empty or list."""
        response = client.get("/api/v1/inventory/reports/low-stock", headers=_auth_headers(api_token))
        assert response.status_code == 200
        data = response.get_json()
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_low_stock_report_with_reorder(
        self, client, api_token, stock_item_with_cost, warehouse, test_user
    ):
        """Item with reorder_point and stock below it appears in low-stock."""
        stock_item_with_cost.reorder_point = Decimal("20")
        stock_item_with_cost.reorder_quantity = Decimal("50")
        db.session.commit()

        StockMovement.record_movement(
            movement_type="purchase",
            stock_item_id=stock_item_with_cost.id,
            warehouse_id=warehouse.id,
            quantity=Decimal("5"),
            moved_by=test_user.id,
            update_stock=True,
        )
        db.session.commit()

        response = client.get("/api/v1/inventory/reports/low-stock", headers=_auth_headers(api_token))
        assert response.status_code == 200
        data = response.get_json()
        assert "items" in data
        low = [i for i in data["items"] if i["item_id"] == stock_item_with_cost.id]
        assert len(low) >= 1
        assert low[0]["quantity_on_hand"] == 5.0
        assert low[0]["reorder_point"] == 20.0
        assert low[0]["shortfall"] == 15.0

    def test_low_stock_filter_warehouse(
        self, client, api_token, stock_item_with_cost, warehouse, test_user
    ):
        """Low-stock with warehouse_id filters by warehouse."""
        stock_item_with_cost.reorder_point = Decimal("10")
        db.session.commit()
        StockMovement.record_movement(
            movement_type="purchase",
            stock_item_id=stock_item_with_cost.id,
            warehouse_id=warehouse.id,
            quantity=Decimal("2"),
            moved_by=test_user.id,
            update_stock=True,
        )
        db.session.commit()

        response = client.get(
            f"/api/v1/inventory/reports/low-stock?warehouse_id={warehouse.id}",
            headers=_auth_headers(api_token),
        )
        assert response.status_code == 200
        data = response.get_json()
        assert all(i["warehouse_id"] == warehouse.id for i in data["items"])

    def test_low_stock_unauthorized(self, client):
        """Low-stock without token returns 401."""
        response = client.get("/api/v1/inventory/reports/low-stock")
        assert response.status_code == 401

    def test_low_stock_invalid_warehouse_id(self, client, api_token):
        """Low-stock with invalid warehouse_id returns 200 with all items or 400."""
        response = client.get(
            "/api/v1/inventory/reports/low-stock?warehouse_id=invalid",
            headers=_auth_headers(api_token),
        )
        assert response.status_code in (200, 400)
        if response.status_code == 200:
            data = response.get_json()
            assert "items" in data
            assert isinstance(data["items"], list)
