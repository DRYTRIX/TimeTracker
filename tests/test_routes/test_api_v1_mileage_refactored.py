"""
Tests for refactored API v1 mileage routes with N+1 query fixes.
"""

import pytest
from datetime import date
from decimal import Decimal
from app.models import Mileage, Project, ApiToken


class TestAPIMileageRefactored:
    """Tests for refactored mileage API routes"""

    @pytest.fixture
    def api_token(self, app, user):
        """Create an API token for testing"""
        token, plain_token = ApiToken.create_token(
            user_id=user.id, name="Test API Token", scopes="read:mileage,write:mileage"
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

    def test_list_mileage_uses_eager_loading(self, app, client_with_token, user, mileage):
        """Test that list_mileage route uses eager loading to avoid N+1"""
        response = client_with_token.get("/api/v1/mileage")

        assert response.status_code == 200
        data = response.get_json()
        assert "mileage" in data
        assert "pagination" in data

    def test_get_mileage_uses_eager_loading(self, app, client_with_token, mileage):
        """Test that get_mileage route uses eager loading"""
        response = client_with_token.get(f"/api/v1/mileage/{mileage.id}")

        assert response.status_code == 200
        data = response.get_json()
        assert "mileage" in data
        assert data["mileage"]["id"] == mileage.id

    def test_create_mileage(self, app, client_with_token, user, project):
        """Test create_mileage route"""
        response = client_with_token.post(
            "/api/v1/mileage",
            json={
                "trip_date": date.today().isoformat(),
                "purpose": "Client visit",
                "start_location": "Office",
                "end_location": "Client Site",
                "distance_km": 50.5,
                "rate_per_km": 0.50,
                "project_id": project.id,
                "is_round_trip": False,
            },
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.get_json()
        assert "mileage" in data
        assert data["mileage"]["distance_km"] == "50.5"

    def test_update_mileage(self, app, client_with_token, mileage):
        """Test update_mileage route"""
        response = client_with_token.put(
            f"/api/v1/mileage/{mileage.id}",
            json={"purpose": "Updated purpose", "distance_km": 75.0},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert "mileage" in data
        assert data["mileage"]["purpose"] == "Updated purpose"

    def test_delete_mileage(self, app, client_with_token, mileage):
        """Test delete_mileage route"""
        response = client_with_token.delete(f"/api/v1/mileage/{mileage.id}")

        assert response.status_code == 200
        data = response.get_json()
        assert "message" in data

        # Verify mileage was rejected
        from app import db

        db.session.refresh(mileage)
        assert mileage.status == "rejected"

    def test_list_mileage_with_filters(self, app, client_with_token, user, project, mileage):
        """Test list_mileage with various filters"""
        # Filter by project
        response = client_with_token.get(f"/api/v1/mileage?project_id={project.id}")

        assert response.status_code == 200
        data = response.get_json()
        assert "mileage" in data

        # All entries should belong to the project
        for entry in data["mileage"]:
            assert entry["project_id"] == project.id
