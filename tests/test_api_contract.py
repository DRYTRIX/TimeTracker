"""
API contract tests: assert standardized response shapes for errors, pagination, and validation.
See docs/api/API_CONSISTENCY_AUDIT.md for the contract.

Uses app and client from conftest to avoid duplicate DB setup and schema issues.
"""

import pytest

pytestmark = [pytest.mark.api, pytest.mark.integration]

import json
from app import db
from app.models import User, Project, Client, ApiToken


@pytest.fixture
def contract_user_id(app):
    """Create user for contract tests; return id to avoid detached instance."""
    with app.app_context():
        user = User(username="contractuser", email="contract@example.com")
        user.set_password("password")
        user.is_active = True
        db.session.add(user)
        db.session.commit()
        return int(user.id)


@pytest.fixture
def api_token_read_only(app, contract_user_id):
    """Token with read:projects only (no write)."""
    with app.app_context():
        token, plain = ApiToken.create_token(
            user_id=contract_user_id, name="Read only", scopes="read:projects"
        )
        db.session.add(token)
        db.session.commit()
        return plain


@pytest.fixture
def api_token_time_entries_only(app, contract_user_id):
    """Token with read:time_entries, write:time_entries only (no projects scope)."""
    with app.app_context():
        token, plain = ApiToken.create_token(
            user_id=contract_user_id,
            name="Time entries only",
            scopes="read:time_entries,write:time_entries",
        )
        db.session.add(token)
        db.session.commit()
        return plain


@pytest.fixture
def api_token_full(app, contract_user_id):
    """Token with read/write for projects and time_entries."""
    with app.app_context():
        token, plain = ApiToken.create_token(
            user_id=contract_user_id,
            name="Full",
            scopes="read:projects,write:projects,read:time_entries,write:time_entries",
        )
        db.session.add(token)
        db.session.commit()
        return plain


@pytest.fixture
def test_project(app, contract_user_id):
    with app.app_context():
        client_model = Client(name="Contract Client", email="c@example.com")
        db.session.add(client_model)
        db.session.commit()
        project = Project(
            name="Contract Project",
            status="active",
            client_id=client_model.id,
        )
        db.session.add(project)
        db.session.commit()
        return project


class TestErrorResponseContract:
    """Error responses MUST include error, message, and optional error_code."""

    def test_401_includes_error_message_and_error_code(self, client):
        response = client.get("/api/v1/projects")
        assert response.status_code == 401
        data = json.loads(response.data)
        assert "error" in data
        assert "message" in data
        assert data.get("error_code") == "unauthorized"

    def test_403_scope_includes_error_message_and_error_code(self, client, api_token_read_only):
        headers = {"Authorization": f"Bearer {api_token_read_only}"}
        response = client.post(
            "/api/v1/projects",
            json={"name": "New"},
            headers=headers,
            content_type="application/json",
        )
        assert response.status_code == 403
        data = json.loads(response.data)
        assert "error" in data
        assert "message" in data
        assert data.get("error_code") == "forbidden"
        assert "required_scope" in data
        assert "available_scopes" in data

    def test_403_get_projects_with_time_entries_only_token(self, client, api_token_time_entries_only):
        """GET /api/v1/projects with token that has only read:time_entries returns 403 (requires read:projects)."""
        headers = {"Authorization": f"Bearer {api_token_time_entries_only}"}
        response = client.get("/api/v1/projects", headers=headers)
        assert response.status_code == 403
        data = json.loads(response.data)
        assert data.get("error_code") == "forbidden"
        assert "required_scope" in data
        assert "available_scopes" in data
        assert "read:projects" in str(data.get("required_scope", ""))

    def test_400_validation_includes_error_code_and_errors(self, client, api_token_full):
        """Creating a project without name returns validation_error and errors dict."""
        headers = {"Authorization": f"Bearer {api_token_full}"}
        response = client.post(
            "/api/v1/projects",
            json={},
            headers=headers,
            content_type="application/json",
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
        assert "message" in data
        assert data.get("error_code") == "validation_error"
        assert "errors" in data
        assert "name" in data["errors"]

    def test_404_not_found_includes_error_code(self, client, api_token_full):
        headers = {"Authorization": f"Bearer {api_token_full}"}
        response = client.get("/api/v1/projects/999999", headers=headers)
        assert response.status_code == 404
        data = json.loads(response.data)
        assert "error" in data
        assert "message" in data
        assert data.get("error_code") == "not_found"


class TestPaginationContract:
    """List responses MUST use resource-named key + pagination with standard keys."""

    def test_projects_list_has_projects_and_pagination(self, client, api_token_full, test_project):
        headers = {"Authorization": f"Bearer {api_token_full}"}
        response = client.get("/api/v1/projects", headers=headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "projects" in data
        assert "pagination" in data
        pag = data["pagination"]
        for key in ("page", "per_page", "total", "pages", "has_next", "has_prev", "next_page", "prev_page"):
            assert key in pag, f"pagination must include {key}"

    def test_pagination_default_per_page(self, client, api_token_full):
        headers = {"Authorization": f"Bearer {api_token_full}"}
        response = client.get("/api/v1/projects", headers=headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["pagination"]["per_page"] == 50
