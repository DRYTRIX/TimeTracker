"""
Comprehensive tests for refactored time entry API routes including update/delete.
"""

import pytest
from datetime import datetime, timedelta
from app.models import TimeEntry, Project, ApiToken


class TestAPITimeEntriesComplete:
    """Complete tests for time entry API routes"""

    @pytest.fixture
    def api_token(self, app, user):
        """Create an API token for testing"""
        token, plain_token = ApiToken.create_token(
            user_id=user.id, name="Test API Token", scopes="read:time_entries,write:time_entries"
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

    def test_update_time_entry_uses_service_layer(self, app, client_with_token, time_entry):
        """Test that update_time_entry route uses service layer"""
        response = client_with_token.put(
            f"/api/v1/time-entries/{time_entry.id}",
            json={"notes": "Updated notes", "billable": False},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert "time_entry" in data
        assert data["time_entry"]["notes"] == "Updated notes"

    def test_delete_time_entry_uses_service_layer(self, app, client_with_token, time_entry):
        """Test that delete_time_entry route uses service layer"""
        # Ensure entry is not active
        time_entry.end_time = datetime.utcnow()
        from app import db

        db.session.commit()

        response = client_with_token.delete(f"/api/v1/time-entries/{time_entry.id}")

        assert response.status_code == 200
        data = response.get_json()
        assert "message" in data

    def test_start_timer_uses_service_layer(self, app, client_with_token, project):
        """Test that start_timer route uses service layer"""
        response = client_with_token.post(
            "/api/v1/timer/start",
            json={"project_id": project.id, "notes": "API test timer"},
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.get_json()
        assert "timer" in data
        assert data["timer"]["project_id"] == project.id

    def test_stop_timer_uses_service_layer(self, app, client_with_token, user, project):
        """Test that stop_timer route uses service layer"""
        # First start a timer
        from app.models import TimeEntry
        from app import db

        timer = TimeEntry(user_id=user.id, project_id=project.id, start_time=datetime.utcnow())
        db.session.add(timer)
        db.session.commit()

        response = client_with_token.post("/api/v1/timer/stop")

        assert response.status_code == 200
        data = response.get_json()
        assert "time_entry" in data
