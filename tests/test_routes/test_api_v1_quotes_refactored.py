"""
Tests for refactored quote API routes.
"""

import pytest
from app.models import Quote, ApiToken, Client


class TestAPIQuotesRefactored:
    """Tests for quote API routes using service layer"""

    @pytest.fixture
    def api_token(self, app, user):
        """Create an API token for testing"""
        token, plain_token = ApiToken.create_token(
            user_id=user.id,
            name="Test API Token",
            scopes="read:quotes,write:quotes"
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
        test_client.environ_base['HTTP_AUTHORIZATION'] = f'Bearer {plain_token}'
        return test_client

    def test_list_quotes_uses_service_layer(self, app, client_with_token, quote):
        """Test that list_quotes route uses service layer"""
        response = client_with_token.get("/api/v1/quotes")
        
        assert response.status_code == 200
        data = response.get_json()
        assert "quotes" in data
        assert "pagination" in data

    def test_get_quote_uses_service_layer(self, app, client_with_token, quote):
        """Test that get_quote route uses service layer"""
        response = client_with_token.get(f"/api/v1/quotes/{quote.id}")
        
        assert response.status_code == 200
        data = response.get_json()
        assert "quote" in data
        assert data["quote"]["id"] == quote.id

    def test_create_quote_uses_service_layer(self, app, client_with_token, client):
        """Test that create_quote route uses service layer"""
        response = client_with_token.post(
            "/api/v1/quotes",
            json={
                "client_id": client.id,
                "title": "Test Quote",
                "description": "Test description",
                "tax_rate": 21.0,
                "currency_code": "EUR"
            },
            content_type="application/json"
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert "quote" in data
        assert data["quote"]["title"] == "Test Quote"

    def test_update_quote_uses_service_layer(self, app, client_with_token, quote):
        """Test that update_quote route uses service layer"""
        response = client_with_token.put(
            f"/api/v1/quotes/{quote.id}",
            json={
                "title": "Updated Quote Title",
                "status": "sent"
            },
            content_type="application/json"
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert "quote" in data
        assert data["quote"]["title"] == "Updated Quote Title"

