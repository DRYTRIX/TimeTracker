"""API tests for purchase order create edge cases."""

import json
from datetime import date
from unittest.mock import patch

import pytest
from sqlalchemy.exc import IntegrityError

pytestmark = [pytest.mark.api, pytest.mark.integration]

from app import db
from app.models import ApiToken, Supplier


@pytest.fixture
def api_token(db_session, test_user):
    token, plain_token = ApiToken.create_token(
        user_id=test_user.id,
        name="Purchase Order API Test Token",
        description="For purchase order API tests",
        scopes="read:projects,write:projects",
    )
    db.session.add(token)
    db.session.commit()
    return plain_token


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture
def test_supplier(db_session, test_user):
    supplier = Supplier(code="SUP-API-001", name="API Supplier", created_by=test_user.id)
    db_session.add(supplier)
    db_session.commit()
    return supplier


class TestPurchaseOrderCreateAPI:
    def test_create_purchase_order_first_record(self, client, api_token, test_supplier):
        payload = {
            "supplier_id": test_supplier.id,
            "order_date": date.today().isoformat(),
            "currency_code": "EUR",
            "items": [{"description": "Cable", "quantity_ordered": "2", "unit_cost": "3.50"}],
        }
        response = client.post(
            "/api/v1/inventory/purchase-orders",
            data=json.dumps(payload),
            headers=_auth_headers(api_token),
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["purchase_order"]["po_number"].startswith("PO-")

    def test_create_purchase_order_rejects_invalid_item(self, client, api_token, test_supplier):
        payload = {
            "supplier_id": test_supplier.id,
            "items": [{"description": "", "quantity_ordered": "0", "unit_cost": "-1"}],
        }
        response = client.post(
            "/api/v1/inventory/purchase-orders",
            data=json.dumps(payload),
            headers=_auth_headers(api_token),
        )
        assert response.status_code == 400

    def test_create_purchase_order_conflict_maps_to_409(self, client, api_token, test_supplier):
        payload = {
            "supplier_id": test_supplier.id,
            "order_date": date.today().isoformat(),
            "items": [{"description": "Item", "quantity_ordered": "1", "unit_cost": "1.00"}],
        }
        with patch(
            "app.routes.api_v1.db.session.commit",
            side_effect=IntegrityError("INSERT", {"po_number": "PO-CONFLICT"}, Exception("duplicate key")),
        ):
            response = client.post(
                "/api/v1/inventory/purchase-orders",
                data=json.dumps(payload),
                headers=_auth_headers(api_token),
            )
        assert response.status_code == 409
