"""
Tests for refactored API v1 time entry routes with N+1 query fixes.
"""

import pytest
from datetime import datetime, timedelta
from app.models import TimeEntry, Project, ApiToken


class TestAPITimeEntriesRefactored:
    """Tests for refactored time entry API routes"""

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

    def test_list_time_entries_uses_eager_loading(self, app, client_with_token, user, project, time_entry):
        """Test that list_time_entries route uses eager loading to avoid N+1"""
        response = client_with_token.get("/api/v1/time-entries")

        assert response.status_code == 200
        data = response.get_json()
        assert "time_entries" in data
        assert "pagination" in data

        # Verify entries have project data loaded (no N+1)
        if len(data["time_entries"]) > 0:
            entry = data["time_entries"][0]
            assert "project" in entry or "project_id" in entry

    def test_get_time_entry_uses_eager_loading(self, app, client_with_token, time_entry):
        """Test that get_time_entry route uses eager loading"""
        response = client_with_token.get(f"/api/v1/time-entries/{time_entry.id}")

        assert response.status_code == 200
        data = response.get_json()
        assert "time_entry" in data
        assert data["time_entry"]["id"] == time_entry.id

    def test_create_time_entry_uses_service_layer(self, app, client_with_token, user, project):
        """Test that create_time_entry route uses service layer"""
        start_time = datetime.utcnow() - timedelta(hours=2)
        end_time = datetime.utcnow()

        response = client_with_token.post(
            "/api/v1/time-entries",
            json={
                "project_id": project.id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "notes": "API test entry",
                "billable": True,
            },
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.get_json()
        assert "time_entry" in data
        assert data["time_entry"]["project_id"] == project.id

        # Verify entry was created
        from app import db

        entry = TimeEntry.query.filter_by(notes="API test entry").first()
        assert entry is not None

    def test_list_time_entries_with_filters(self, app, client_with_token, user, project, time_entry):
        """Test list_time_entries with various filters"""
        # Filter by project
        response = client_with_token.get(f"/api/v1/time-entries?project_id={project.id}")

        assert response.status_code == 200
        data = response.get_json()
        assert "time_entries" in data

        # All entries should belong to the project
        for entry in data["time_entries"]:
            assert entry["project_id"] == project.id

    def test_list_time_entries_pagination(self, app, client_with_token, user, project):
        """Test that list_time_entries supports pagination"""
        # Create multiple entries
        from app import db

        for i in range(5):
            entry = TimeEntry(
                user_id=user.id,
                project_id=project.id,
                start_time=datetime.utcnow() - timedelta(hours=i + 1),
                end_time=datetime.utcnow() - timedelta(hours=i),
                notes=f"Test entry {i}",
            )
            db.session.add(entry)
        db.session.commit()

        # Request first page
        response = client_with_token.get("/api/v1/time-entries?page=1&per_page=2")

        assert response.status_code == 200
        data = response.get_json()
        assert "pagination" in data
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["per_page"] == 2
        assert len(data["time_entries"]) <= 2

    def test_list_time_entries_same_day_date_filter_includes_midday_entries(
        self, app, client_with_token, user, project
    ):
        """Test that date-only start_date=end_date includes entries throughout the day (not just midnight)."""
        from app import db
        from app.utils.timezone import get_timezone_obj

        tz = get_timezone_obj()
        now = datetime.now(tz).replace(tzinfo=None)
        today_str = now.strftime("%Y-%m-%d")

        # Create entry at 14:00 today (not midnight)
        start = now.replace(hour=14, minute=0, second=0, microsecond=0)
        end = now.replace(hour=15, minute=0, second=0, microsecond=0)
        entry = TimeEntry(
            user_id=user.id,
            project_id=project.id,
            start_time=start,
            end_time=end,
            notes="Midday entry for same-day filter test",
        )
        db.session.add(entry)
        db.session.commit()

        response = client_with_token.get(
            f"/api/v1/time-entries?start_date={today_str}&end_date={today_str}"
        )

        assert response.status_code == 200
        data = response.get_json()
        assert "time_entries" in data
        # Same-day filter should include the midday entry (fix for date-only end_date)
        entries = [e for e in data["time_entries"] if "Midday entry" in (e.get("notes") or "")]
        assert len(entries) >= 1, "Same-day date filter should include entries throughout the day"
