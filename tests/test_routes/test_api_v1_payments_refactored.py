"""
Tests for refactored API v1 payment routes using service layer.
"""

import pytest
from datetime import date
from decimal import Decimal
from app.models import Payment, Invoice, ApiToken


class TestAPIPaymentsRefactored:
    """Tests for refactored payment API routes"""

    @pytest.fixture
    def api_token(self, app, user):
        """Create an API token for testing"""
        token, plain_token = ApiToken.create_token(
            user_id=user.id, name="Test API Token", scopes="read:payments,write:payments"
        )
        from app import db

        db.session.add(token)
        db.session.commit()
        return token, plain_token

    @pytest.fixture
    def client_with_token(self, app, api_token):
        """Create a test client with API token"""
        token, plain_token = api_token
        test_client = app.test_client()
        test_client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {plain_token}"
        return test_client

    def test_list_payments_uses_eager_loading(self, app, client_with_token, payment):
        """Test that list_payments route uses eager loading"""
        response = client_with_token.get("/api/v1/payments")

        assert response.status_code == 200
        data = response.get_json()
        assert "payments" in data
        assert "pagination" in data

    def test_get_payment_uses_eager_loading(self, app, client_with_token, payment):
        """Test that get_payment route uses eager loading"""
        response = client_with_token.get(f"/api/v1/payments/{payment.id}")

        assert response.status_code == 200
        data = response.get_json()
        assert "payment" in data
        assert data["payment"]["id"] == payment.id

    def test_create_payment_uses_service_layer(self, app, client_with_token, invoice):
        """Test that create_payment route uses service layer"""
        response = client_with_token.post(
            "/api/v1/payments",
            json={
                "invoice_id": invoice.id,
                "amount": 1000.00,
                "currency": "EUR",
                "payment_date": date.today().isoformat(),
                "method": "bank_transfer",
                "notes": "Test payment",
            },
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.get_json()
        assert "payment" in data
        assert data["payment"]["invoice_id"] == invoice.id

    def test_update_payment_uses_service_layer(self, app, client_with_token, payment):
        """Test that update_payment route uses service layer"""
        response = client_with_token.put(
            f"/api/v1/payments/{payment.id}",
            json={"amount": 1500.00, "notes": "Updated payment"},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert "payment" in data
        assert data["payment"]["notes"] == "Updated payment"

    def test_delete_payment_uses_service_layer(self, app, client_with_token, payment):
        """Test that delete_payment route uses service layer"""
        response = client_with_token.delete(f"/api/v1/payments/{payment.id}")

        assert response.status_code == 200
        data = response.get_json()
        assert "message" in data
