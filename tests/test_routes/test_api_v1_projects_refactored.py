"""
Tests for refactored API v1 project routes using service layer.
"""

import pytest
from app.models import Project, Client, ApiToken


class TestAPIProjectsRefactored:
    """Tests for refactored project API routes"""

    @pytest.fixture
    def api_token(self, app, user):
        """Create an API token for testing"""
        token, plain_token = ApiToken.create_token(
            user_id=user.id, name="Test API Token", scopes="read:projects,write:projects"
        )
        from app import db

        db.session.add(token)
        db.session.commit()
        return token, plain_token

    @pytest.fixture
    def client_with_token(self, app, client, api_token):
        """Create a test client with API token"""
        token, plain_token = api_token
        test_client = app.test_client()
        test_client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {plain_token}"
        return test_client

    def test_list_projects_uses_service_layer(self, app, client_with_token, project):
        """Test that list_projects route uses service layer"""
        response = client_with_token.get("/api/v1/projects")

        assert response.status_code == 200
        data = response.get_json()
        assert "projects" in data
        assert "pagination" in data
        assert len(data["projects"]) > 0

    def test_get_project_uses_eager_loading(self, app, client_with_token, project):
        """Test that get_project route uses eager loading to avoid N+1"""
        response = client_with_token.get(f"/api/v1/projects/{project.id}")

        assert response.status_code == 200
        data = response.get_json()
        assert "project" in data
        assert data["project"]["id"] == project.id

    def test_create_project_uses_service_layer(self, app, client_with_token, client):
        """Test that create_project route uses service layer"""
        response = client_with_token.post(
            "/api/v1/projects",
            json={"name": "API Test Project", "client_id": client.id, "billable": True},
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.get_json()
        assert "project" in data
        assert data["project"]["name"] == "API Test Project"

        # Verify project was created
        from app import db

        project = Project.query.filter_by(name="API Test Project").first()
        assert project is not None

    def test_update_project_uses_service_layer(self, app, client_with_token, project):
        """Test that update_project route uses service layer"""
        response = client_with_token.put(
            f"/api/v1/projects/{project.id}",
            json={"name": "Updated Project Name", "description": "Updated description"},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert "project" in data
        assert data["project"]["name"] == "Updated Project Name"

        # Verify project was updated
        from app import db

        db.session.refresh(project)
        assert project.name == "Updated Project Name"

    def test_delete_project_uses_service_layer(self, app, client_with_token, project):
        """Test that delete_project route uses service layer"""
        response = client_with_token.delete(f"/api/v1/projects/{project.id}")

        assert response.status_code == 200
        data = response.get_json()
        assert "message" in data

        # Verify project was archived
        from app import db

        db.session.refresh(project)
        assert project.status == "archived"

    def test_list_projects_with_filters(self, app, client_with_token, project, client):
        """Test list_projects with status and client filters"""
        response = client_with_token.get(f"/api/v1/projects?status=active&client_id={client.id}")

        assert response.status_code == 200
        data = response.get_json()
        assert "projects" in data
        # All returned projects should match filters
        for p in data["projects"]:
            assert p["status"] == "active"
            assert p["client_id"] == client.id
