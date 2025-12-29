"""
Tests for search API endpoints.
Tests both /api/search (legacy) and /api/v1/search (versioned API).
"""

import pytest
from app.models import Project, Task, Client, TimeEntry, ApiToken


class TestLegacySearchAPI:
    """Tests for legacy /api/search endpoint (session-based auth)"""

    def test_search_with_valid_query(self, authenticated_client, project):
        """Test search with valid query"""
        response = authenticated_client.get("/api/search", query_string={"q": "test"})

        assert response.status_code == 200
        data = response.get_json()
        assert "results" in data
        assert "query" in data
        assert "count" in data
        assert isinstance(data["results"], list)

    def test_search_with_short_query(self, authenticated_client):
        """Test search with query that's too short"""
        response = authenticated_client.get("/api/search", query_string={"q": "a"})

        assert response.status_code == 200
        data = response.get_json()
        assert data["results"] == []
        assert data["count"] == 0

    def test_search_with_empty_query(self, authenticated_client):
        """Test search with empty query"""
        response = authenticated_client.get("/api/search", query_string={"q": ""})

        assert response.status_code == 200
        data = response.get_json()
        assert data["results"] == []

    def test_search_with_limit(self, authenticated_client, project):
        """Test search with custom limit"""
        response = authenticated_client.get("/api/search", query_string={"q": "test", "limit": 5})

        assert response.status_code == 200
        data = response.get_json()
        assert len(data["results"]) <= 5

    def test_search_with_types_filter(self, authenticated_client, project):
        """Test search with types filter"""
        response = authenticated_client.get("/api/search", query_string={"q": "test", "types": "project"})

        assert response.status_code == 200
        data = response.get_json()
        # All results should be projects
        for result in data["results"]:
            assert result["type"] == "project"

    def test_search_projects(self, authenticated_client, project):
        """Test searching for projects"""
        response = authenticated_client.get("/api/search", query_string={"q": project.name[:3]})

        assert response.status_code == 200
        data = response.get_json()
        project_results = [r for r in data["results"] if r["type"] == "project"]
        assert len(project_results) > 0
        assert any(r["id"] == project.id for r in project_results)

    def test_search_requires_authentication(self, client):
        """Test that search requires authentication"""
        response = client.get("/api/search", query_string={"q": "test"})
        # Should redirect to login
        assert response.status_code in [302, 401]


class TestV1SearchAPI:
    """Tests for /api/v1/search endpoint (token-based auth)"""

    @pytest.fixture
    def api_token(self, app, user):
        """Create an API token for testing"""
        token, plain_token = ApiToken.create_token(
            user_id=user.id, name="Test API Token", scopes="read:projects"
        )
        from app import db

        db.session.add(token)
        db.session.commit()
        return token, plain_token

    @pytest.fixture
    def api_client(self, app, api_token):
        """Create a test client with API token"""
        token, plain_token = api_token
        test_client = app.test_client()
        test_client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {plain_token}"
        return test_client

    def test_search_with_valid_query(self, api_client, project):
        """Test search with valid query"""
        response = api_client.get("/api/v1/search", query_string={"q": "test"})

        assert response.status_code == 200
        data = response.get_json()
        assert "results" in data
        assert "query" in data
        assert "count" in data
        assert isinstance(data["results"], list)

    def test_search_with_short_query(self, api_client):
        """Test search with query that's too short"""
        response = api_client.get("/api/v1/search", query_string={"q": "a"})

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "results" in data

    def test_search_with_empty_query(self, api_client):
        """Test search with empty query"""
        response = api_client.get("/api/v1/search", query_string={"q": ""})

        assert response.status_code == 400

    def test_search_requires_authentication(self, app):
        """Test that search requires authentication"""
        test_client = app.test_client()
        response = test_client.get("/api/v1/search", query_string={"q": "test"})

        assert response.status_code == 401
        data = response.get_json()
        assert "error" in data

    def test_search_requires_read_projects_scope(self, app, user):
        """Test that search requires read:projects scope"""
        # Create token without read:projects scope
        token, plain_token = ApiToken.create_token(
            user_id=user.id, name="Test Token", scopes="read:time_entries"
        )
        from app import db

        db.session.add(token)
        db.session.commit()

        test_client = app.test_client()
        test_client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {plain_token}"

        response = test_client.get("/api/v1/search", query_string={"q": "test"})

        assert response.status_code == 403
        data = response.get_json()
        assert "error" in data
        assert "Insufficient permissions" in data["error"]

    def test_search_with_limit(self, api_client, project):
        """Test search with custom limit"""
        response = api_client.get("/api/v1/search", query_string={"q": "test", "limit": 5})

        assert response.status_code == 200
        data = response.get_json()
        # Should respect limit per category, so total might be higher
        assert isinstance(data["results"], list)

    def test_search_with_types_filter(self, api_client, project):
        """Test search with types filter"""
        response = api_client.get("/api/v1/search", query_string={"q": "test", "types": "project"})

        assert response.status_code == 200
        data = response.get_json()
        # All results should be projects
        for result in data["results"]:
            assert result["type"] == "project"

    def test_search_projects(self, api_client, project):
        """Test searching for projects"""
        response = api_client.get("/api/v1/search", query_string={"q": project.name[:3]})

        assert response.status_code == 200
        data = response.get_json()
        project_results = [r for r in data["results"] if r["type"] == "project"]
        assert len(project_results) > 0
        assert any(r["id"] == project.id for r in project_results)

    def test_search_time_entries_respects_user_permissions(self, app, user, project):
        """Test that non-admin users only see their own time entries"""
        from app import db
        from datetime import datetime, timedelta

        # Create API token for user
        token, plain_token = ApiToken.create_token(
            user_id=user.id, name="Test Token", scopes="read:projects"
        )
        db.session.add(token)

        # Create time entry for this user
        entry = TimeEntry(
            user_id=user.id,
            project_id=project.id,
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now(),
            notes="Test search entry",
        )
        db.session.add(entry)
        db.session.commit()

        test_client = app.test_client()
        test_client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {plain_token}"

        response = test_client.get("/api/v1/search", query_string={"q": "Test search", "types": "entry"})

        assert response.status_code == 200
        data = response.get_json()
        # Should find the user's own entry
        entry_results = [r for r in data["results"] if r["type"] == "entry"]
        assert any(r["id"] == entry.id for r in entry_results)

    def test_search_clients(self, api_client, client):
        """Test searching for clients"""
        response = api_client.get("/api/v1/search", query_string={"q": client.name[:3]})

        assert response.status_code == 200
        data = response.get_json()
        client_results = [r for r in data["results"] if r["type"] == "client"]
        assert len(client_results) > 0
        assert any(r["id"] == client.id for r in client_results)

    def test_search_tasks(self, api_client, task):
        """Test searching for tasks"""
        response = api_client.get("/api/v1/search", query_string={"q": task.name[:3]})

        assert response.status_code == 200
        data = response.get_json()
        task_results = [r for r in data["results"] if r["type"] == "task"]
        assert len(task_results) > 0
        assert any(r["id"] == task.id for r in task_results)

