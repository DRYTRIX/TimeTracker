"""Tests for API v1 inventory transfers (list, create, get by reference_id)."""

import json
import pytest

pytestmark = [pytest.mark.api, pytest.mark.integration]

from decimal import Decimal

from app import db
from app.models import (
    User,
    ApiToken,
    Warehouse,
    StockItem,
    WarehouseStock,
    StockMovement,
)


@pytest.fixture
def api_token(db_session, test_user):
    """Create an API token with read and write projects (inventory uses these scopes)."""
    token, plain_token = ApiToken.create_token(
        user_id=test_user.id,
        name="Inventory Transfer Test Token",
        description="For inventory transfer API tests",
        scopes="read:projects,write:projects",
    )
    db.session.add(token)
    db.session.commit()
    return plain_token


@pytest.fixture
def token_read_only(db_session, test_user):
    """Token with read-only scope (no write:projects)."""
    token, plain_token = ApiToken.create_token(
        user_id=test_user.id,
        name="Read Only Token",
        description="Read only",
        scopes="read:projects",
    )
    db.session.add(token)
    db.session.commit()
    return plain_token


@pytest.fixture
def warehouse_from(db_session, test_user):
    """Source warehouse for transfers."""
    wh = Warehouse(name="Warehouse From", code="WH-FROM", created_by=test_user.id)
    db.session.add(wh)
    db.session.commit()
    return wh


@pytest.fixture
def warehouse_to(db_session, test_user):
    """Destination warehouse for transfers."""
    wh = Warehouse(name="Warehouse To", code="WH-TO", created_by=test_user.id)
    db.session.add(wh)
    db.session.commit()
    return wh


@pytest.fixture
def stock_item_trackable(db_session, test_user):
    """Trackable stock item with default cost."""
    item = StockItem(
        sku="TRANSFER-001",
        name="Transfer Test Product",
        created_by=test_user.id,
        default_price=Decimal("10.00"),
        default_cost=Decimal("5.00"),
        is_trackable=True,
    )
    db.session.add(item)
    db.session.commit()
    return item


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


class TestListTransfersAPI:
    """GET /api/v1/inventory/transfers"""

    def test_list_transfers_empty(self, client, api_token):
        """List transfers when none exist returns empty list with pagination."""
        response = client.get("/api/v1/inventory/transfers", headers=_auth_headers(api_token))
        assert response.status_code == 200
        data = response.get_json()
        assert "transfers" in data
        assert data["transfers"] == []
        assert "pagination" in data
        assert data["pagination"]["total"] == 0

    def test_list_transfers_after_create(
        self, client, api_token, stock_item_trackable, warehouse_from, warehouse_to, test_user
    ):
        """Create stock, create transfer via API, then list returns it."""
        # Put stock in source warehouse
        StockMovement.record_movement(
            movement_type="purchase",
            stock_item_id=stock_item_trackable.id,
            warehouse_id=warehouse_from.id,
            quantity=Decimal("20"),
            moved_by=test_user.id,
            update_stock=True,
        )
        db.session.commit()

        # Create transfer via API
        payload = {
            "stock_item_id": stock_item_trackable.id,
            "from_warehouse_id": warehouse_from.id,
            "to_warehouse_id": warehouse_to.id,
            "quantity": 5,
            "notes": "Test transfer",
        }
        create_resp = client.post(
            "/api/v1/inventory/transfers", data=json.dumps(payload), headers=_auth_headers(api_token)
        )
        assert create_resp.status_code == 201
        ref_id = create_resp.get_json()["reference_id"]

        # List transfers
        response = client.get("/api/v1/inventory/transfers", headers=_auth_headers(api_token))
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["transfers"]) == 1
        t = data["transfers"][0]
        assert t["reference_id"] == ref_id
        assert t["stock_item_id"] == stock_item_trackable.id
        assert t["from_warehouse_id"] == warehouse_from.id
        assert t["to_warehouse_id"] == warehouse_to.id
        assert t["quantity"] == 5.0
        assert t["notes"] == "Test transfer"
        assert len(t["movement_ids"]) == 2

    def test_list_transfers_unauthorized(self, client):
        """List without token returns 401."""
        response = client.get("/api/v1/inventory/transfers")
        assert response.status_code == 401


class TestCreateTransferAPI:
    """POST /api/v1/inventory/transfers"""

    def test_create_transfer_success(
        self, client, api_token, stock_item_trackable, warehouse_from, warehouse_to, test_user
    ):
        """POST with valid data creates two movements and returns 201."""
        StockMovement.record_movement(
            movement_type="purchase",
            stock_item_id=stock_item_trackable.id,
            warehouse_id=warehouse_from.id,
            quantity=Decimal("15"),
            moved_by=test_user.id,
            update_stock=True,
        )
        db.session.commit()

        payload = {
            "stock_item_id": stock_item_trackable.id,
            "from_warehouse_id": warehouse_from.id,
            "to_warehouse_id": warehouse_to.id,
            "quantity": 4,
            "notes": "API transfer",
        }
        response = client.post(
            "/api/v1/inventory/transfers", data=json.dumps(payload), headers=_auth_headers(api_token)
        )
        assert response.status_code == 201
        data = response.get_json()
        assert "reference_id" in data
        assert "transfers" in data
        assert len(data["transfers"]) == 2
        assert data["message"] == "Stock transfer completed successfully"

        # Verify DB: two movements with same reference_id
        ref_id = data["reference_id"]
        movements = StockMovement.query.filter_by(
            movement_type="transfer", reference_type="transfer", reference_id=ref_id
        ).all()
        assert len(movements) == 2
        qty_out = [m for m in movements if m.quantity < 0][0]
        qty_in = [m for m in movements if m.quantity > 0][0]
        assert float(qty_out.quantity) == -4.0
        assert float(qty_in.quantity) == 4.0
        assert qty_out.warehouse_id == warehouse_from.id
        assert qty_in.warehouse_id == warehouse_to.id

        # Stock levels updated
        from_stock = WarehouseStock.query.filter_by(
            warehouse_id=warehouse_from.id, stock_item_id=stock_item_trackable.id
        ).first()
        to_stock = WarehouseStock.query.filter_by(
            warehouse_id=warehouse_to.id, stock_item_id=stock_item_trackable.id
        ).first()
        assert from_stock.quantity_on_hand == Decimal("11")
        assert to_stock.quantity_on_hand == Decimal("4")

    def test_create_transfer_missing_fields(self, client, api_token):
        """POST with missing required fields returns 400."""
        response = client.post(
            "/api/v1/inventory/transfers",
            data=json.dumps({"stock_item_id": 1}),
            headers=_auth_headers(api_token),
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data or "errors" in data

    def test_create_transfer_invalid_json_returns_400(self, client, api_token):
        """POST with invalid JSON body returns 400 (missing fields or parse error)."""
        response = client.post(
            "/api/v1/inventory/transfers",
            data="not valid json {",
            headers={**_auth_headers(api_token), "Content-Type": "application/json"},
        )
        assert response.status_code == 400

    def test_create_transfer_invalid_id_types(
        self, client, api_token, stock_item_trackable, warehouse_from, warehouse_to, test_user
    ):
        """POST with non-numeric ID (e.g. string) for stock_item_id yields 400 or 404, not 500."""
        StockMovement.record_movement(
            movement_type="purchase",
            stock_item_id=stock_item_trackable.id,
            warehouse_id=warehouse_from.id,
            quantity=Decimal("10"),
            moved_by=test_user.id,
            update_stock=True,
        )
        db.session.commit()
        payload = {
            "stock_item_id": "not_an_int",
            "from_warehouse_id": warehouse_from.id,
            "to_warehouse_id": warehouse_to.id,
            "quantity": 2,
        }
        response = client.post(
            "/api/v1/inventory/transfers",
            data=json.dumps(payload),
            headers=_auth_headers(api_token),
        )
        assert response.status_code in (400, 404)
        if response.status_code == 400:
            data = response.get_json()
            assert data is not None

    def test_create_transfer_same_warehouse(
        self, client, api_token, stock_item_trackable, warehouse_from, test_user
    ):
        """POST with from_warehouse_id == to_warehouse_id returns 400."""
        StockMovement.record_movement(
            movement_type="purchase",
            stock_item_id=stock_item_trackable.id,
            warehouse_id=warehouse_from.id,
            quantity=Decimal("10"),
            moved_by=test_user.id,
            update_stock=True,
        )
        db.session.commit()

        payload = {
            "stock_item_id": stock_item_trackable.id,
            "from_warehouse_id": warehouse_from.id,
            "to_warehouse_id": warehouse_from.id,
            "quantity": 2,
        }
        response = client.post(
            "/api/v1/inventory/transfers", data=json.dumps(payload), headers=_auth_headers(api_token)
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "different" in (data.get("error") or data.get("message") or "").lower()

    def test_create_transfer_insufficient_stock(
        self, client, api_token, stock_item_trackable, warehouse_from, warehouse_to
    ):
        """POST when source has no stock or less than quantity returns 400."""
        payload = {
            "stock_item_id": stock_item_trackable.id,
            "from_warehouse_id": warehouse_from.id,
            "to_warehouse_id": warehouse_to.id,
            "quantity": 10,
        }
        response = client.post(
            "/api/v1/inventory/transfers", data=json.dumps(payload), headers=_auth_headers(api_token)
        )
        assert response.status_code in (400, 404)
        data = response.get_json()
        assert "error" in data or "message" in data

    def test_create_transfer_forbidden_without_write_scope(
        self, client, token_read_only, stock_item_trackable, warehouse_from, warehouse_to, test_user
    ):
        """POST with read-only token returns 403."""
        StockMovement.record_movement(
            movement_type="purchase",
            stock_item_id=stock_item_trackable.id,
            warehouse_id=warehouse_from.id,
            quantity=Decimal("10"),
            moved_by=test_user.id,
            update_stock=True,
        )
        db.session.commit()
        payload = {
            "stock_item_id": stock_item_trackable.id,
            "from_warehouse_id": warehouse_from.id,
            "to_warehouse_id": warehouse_to.id,
            "quantity": 2,
        }
        response = client.post(
            "/api/v1/inventory/transfers",
            data=json.dumps(payload),
            headers=_auth_headers(token_read_only),
        )
        assert response.status_code == 403

    def test_create_transfer_unauthorized(self, client, stock_item_trackable, warehouse_from, warehouse_to):
        """POST without token returns 401."""
        payload = {
            "stock_item_id": stock_item_trackable.id,
            "from_warehouse_id": warehouse_from.id,
            "to_warehouse_id": warehouse_to.id,
            "quantity": 1,
        }
        response = client.post(
            "/api/v1/inventory/transfers", data=json.dumps(payload), headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 401


class TestGetTransferAPI:
    """GET /api/v1/inventory/transfers/<reference_id>"""

    def test_get_transfer_success(
        self, client, api_token, stock_item_trackable, warehouse_from, warehouse_to, test_user
    ):
        """GET by reference_id returns the transfer with two movements."""
        StockMovement.record_movement(
            movement_type="purchase",
            stock_item_id=stock_item_trackable.id,
            warehouse_id=warehouse_from.id,
            quantity=Decimal("10"),
            moved_by=test_user.id,
            update_stock=True,
        )
        db.session.commit()

        payload = {
            "stock_item_id": stock_item_trackable.id,
            "from_warehouse_id": warehouse_from.id,
            "to_warehouse_id": warehouse_to.id,
            "quantity": 3,
        }
        create_resp = client.post(
            "/api/v1/inventory/transfers", data=json.dumps(payload), headers=_auth_headers(api_token)
        )
        assert create_resp.status_code == 201
        ref_id = create_resp.get_json()["reference_id"]

        response = client.get(f"/api/v1/inventory/transfers/{ref_id}", headers=_auth_headers(api_token))
        assert response.status_code == 200
        data = response.get_json()
        assert "transfer" in data
        t = data["transfer"]
        assert t["reference_id"] == ref_id
        assert t["stock_item_id"] == stock_item_trackable.id
        assert t["from_warehouse_id"] == warehouse_from.id
        assert t["to_warehouse_id"] == warehouse_to.id
        assert t["quantity"] == 3.0
        assert len(t["movements"]) == 2

    def test_get_transfer_not_found(self, client, api_token):
        """GET with non-existent reference_id returns 404."""
        response = client.get("/api/v1/inventory/transfers/999999999999", headers=_auth_headers(api_token))
        assert response.status_code == 404

    def test_get_transfer_non_integer_reference_id_returns_404(self, client, api_token):
        """GET with non-integer reference_id (e.g. 'abc') returns 404 (no matching route)."""
        response = client.get(
            "/api/v1/inventory/transfers/notanumber",
            headers=_auth_headers(api_token),
        )
        assert response.status_code == 404
