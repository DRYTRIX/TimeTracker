"""
Tests for search API endpoints.
Tests both /api/search (legacy) and /api/v1/search (versioned API).
"""

from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy.exc import SQLAlchemyError


class _FailingProjectQuery:
    """Minimal query stand-in so Project.query.filter(...).limit(...).all() raises."""

    def filter(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        raise SQLAlchemyError("simulated project search failure")


pytestmark = [pytest.mark.api, pytest.mark.integration]

from app import db
from app.models import ApiToken, Client, Project, Task, TimeEntry
from app.services import global_search_service as global_search_service_module


@pytest.fixture
def out_of_scope_entities(app, user):
    """Client, project, and task that no scope-restricted user should see (different client)."""
    with app.app_context():
        marker = "ZetaScopeMarkerXq7"
        other_client = Client(
            name=f"Other {marker} Corp",
            email="other-zeta@example.com",
            default_hourly_rate=Decimal("80.00"),
        )
        other_client.status = "active"
        db.session.add(other_client)
        db.session.flush()
        other_project = Project(
            name=f"{marker} Hidden Project",
            client_id=other_client.id,
            description="out of scope",
            billable=True,
            hourly_rate=Decimal("75.00"),
            status="active",
        )
        db.session.add(other_project)
        db.session.flush()
        other_task = Task(
            other_project.id,
            f"{marker} Hidden Task",
            description="out of scope task",
            priority="medium",
            created_by=user.id,
            status="todo",
        )
        db.session.add(other_task)
        db.session.commit()
        return {
            "marker": marker,
            "client_id": other_client.id,
            "project_id": other_project.id,
            "task_id": other_task.id,
        }


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
        assert data.get("partial") is False
        assert data.get("errors") == {}

    def test_search_with_short_query(self, authenticated_client):
        """Test search with query that's too short"""
        response = authenticated_client.get("/api/search", query_string={"q": "a"})

        assert response.status_code == 200
        data = response.get_json()
        assert data["results"] == []
        assert data["count"] == 0
        assert data.get("partial") is False
        assert data.get("errors") == {}

    def test_search_with_empty_query(self, authenticated_client):
        """Test search with empty query"""
        response = authenticated_client.get("/api/search", query_string={"q": ""})

        assert response.status_code == 200
        data = response.get_json()
        assert data["results"] == []
        assert data.get("partial") is False
        assert data.get("errors") == {}

    def test_search_partial_when_projects_domain_db_error(self, authenticated_client):
        """Project search SQLAlchemy errors surface as partial response; other domains still run."""
        with patch.object(global_search_service_module.Project, "query", _FailingProjectQuery()):
            response = authenticated_client.get("/api/search", query_string={"q": "te"})
        assert response.status_code == 200
        data = response.get_json()
        assert data["partial"] is True
        assert "projects" in data["errors"]
        # Service returns a generic message (does not leak exception text).
        assert data["errors"]["projects"] == "Search failed"
        assert data["errors"].get("tasks") is None
        assert isinstance(data["results"], list)

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

    def test_search_scope_restricted_excludes_other_client_entities(
        self, scope_restricted_authenticated_client, project, task, out_of_scope_entities
    ):
        """Subcontractor search must not return projects/tasks/clients outside assigned clients."""
        marker = out_of_scope_entities["marker"]
        resp = scope_restricted_authenticated_client.get(
            "/api/search", query_string={"q": marker, "types": "project,task,client"}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        proj_ids = {r["id"] for r in data["results"] if r["type"] == "project"}
        task_ids = {r["id"] for r in data["results"] if r["type"] == "task"}
        client_ids = {r["id"] for r in data["results"] if r["type"] == "client"}
        assert out_of_scope_entities["project_id"] not in proj_ids
        assert out_of_scope_entities["task_id"] not in task_ids
        assert out_of_scope_entities["client_id"] not in client_ids

    def test_search_scope_restricted_still_finds_assigned_project_and_task(
        self, scope_restricted_authenticated_client, project, task
    ):
        """Subcontractor still sees entities under assigned client."""
        resp = scope_restricted_authenticated_client.get(
            "/api/search", query_string={"q": project.name[:4], "types": "project"}
        )
        assert resp.status_code == 200
        proj_ids = [r["id"] for r in resp.get_json()["results"] if r["type"] == "project"]
        assert project.id in proj_ids

        resp_t = scope_restricted_authenticated_client.get(
            "/api/search", query_string={"q": task.name[:4], "types": "task"}
        )
        assert resp_t.status_code == 200
        task_ids = [r["id"] for r in resp_t.get_json()["results"] if r["type"] == "task"]
        assert task.id in task_ids

    def test_search_admin_sees_out_of_scope_project(self, admin_authenticated_client, out_of_scope_entities):
        """Admin global search includes projects outside any subcontractor scope."""
        marker = out_of_scope_entities["marker"]
        resp = admin_authenticated_client.get("/api/search", query_string={"q": marker, "types": "project"})
        assert resp.status_code == 200
        proj_ids = [r["id"] for r in resp.get_json()["results"] if r["type"] == "project"]
        assert out_of_scope_entities["project_id"] in proj_ids


class TestV1SearchAPI:
    """Tests for /api/v1/search endpoint (token-based auth)"""

    @pytest.fixture
    def api_token(self, app, user):
        """Create an API token for testing"""
        token, plain_token = ApiToken.create_token(user_id=user.id, name="Test API Token", scopes="read:projects")
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
        assert data.get("partial") is False
        assert data.get("errors") == {}

    def test_search_with_short_query(self, api_client):
        """Test search with query that's too short"""
        response = api_client.get("/api/v1/search", query_string={"q": "a"})

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "results" in data
        assert data.get("partial") is False
        assert data.get("errors") == {}

    def test_search_with_empty_query(self, api_client):
        """Test search with empty query"""
        response = api_client.get("/api/v1/search", query_string={"q": ""})

        assert response.status_code == 400
        data = response.get_json()
        assert data.get("partial") is False
        assert data.get("errors") == {}

    def test_v1_search_partial_when_projects_domain_db_error(self, api_client):
        """v1: project search DB errors are reported in errors.projects; other domains still run."""
        with patch.object(global_search_service_module.Project, "query", _FailingProjectQuery()):
            response = api_client.get("/api/v1/search", query_string={"q": "te"})
        assert response.status_code == 200
        data = response.get_json()
        assert data["partial"] is True
        assert "projects" in data["errors"]
        # Service returns a generic message (does not leak exception text).
        assert data["errors"]["projects"] == "Search failed"
        assert isinstance(data["results"], list)

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
        token, plain_token = ApiToken.create_token(user_id=user.id, name="Test Token", scopes="read:time_entries")
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
        from datetime import datetime, timedelta

        from app import db

        # Create API token for user
        token, plain_token = ApiToken.create_token(user_id=user.id, name="Test Token", scopes="read:projects")
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

    def test_search_clients(self, api_client, test_client):
        """Test searching for clients (test_client is the Client model fixture, not the HTTP client)."""
        response = api_client.get("/api/v1/search", query_string={"q": test_client.name[:3]})

        assert response.status_code == 200
        data = response.get_json()
        client_results = [r for r in data["results"] if r["type"] == "client"]
        assert len(client_results) > 0
        assert any(r["id"] == test_client.id for r in client_results)

    def test_search_tasks(self, api_client, task):
        """Test searching for tasks"""
        response = api_client.get("/api/v1/search", query_string={"q": task.name[:3]})

        assert response.status_code == 200
        data = response.get_json()
        task_results = [r for r in data["results"] if r["type"] == "task"]
        assert len(task_results) > 0
        assert any(r["id"] == task.id for r in task_results)

    def test_v1_search_scope_restricted_excludes_other_client_entities(
        self, app, scope_restricted_user, project, task, out_of_scope_entities
    ):
        """v1 search applies the same project/task/client scope as legacy session search."""
        token, plain = ApiToken.create_token(
            user_id=scope_restricted_user.id, name="Sub search token", scopes="read:projects"
        )
        db.session.add(token)
        db.session.commit()

        marker = out_of_scope_entities["marker"]
        test_client = app.test_client()
        test_client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {plain}"
        resp = test_client.get("/api/v1/search", query_string={"q": marker, "types": "project,task,client"})
        assert resp.status_code == 200
        data = resp.get_json()
        proj_ids = {r["id"] for r in data["results"] if r["type"] == "project"}
        task_ids = {r["id"] for r in data["results"] if r["type"] == "task"}
        client_ids = {r["id"] for r in data["results"] if r["type"] == "client"}
        assert out_of_scope_entities["project_id"] not in proj_ids
        assert out_of_scope_entities["task_id"] not in task_ids
        assert out_of_scope_entities["client_id"] not in client_ids

        resp_ok = test_client.get("/api/v1/search", query_string={"q": project.name[:4], "types": "project"})
        assert resp_ok.status_code == 200
        proj_ok = [r["id"] for r in resp_ok.get_json()["results"] if r["type"] == "project"]
        assert project.id in proj_ok
