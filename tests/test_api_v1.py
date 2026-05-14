"""Tests for REST API v1"""

import json
import os
import tempfile
import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy.pool import NullPool

from app import create_app, db
from app.models import ApiToken, Client, Project, Settings, Task, TimeEntry, User

pytestmark = [pytest.mark.api, pytest.mark.integration]


@pytest.fixture
def app():
    """Create and configure a test app instance (isolated SQLite, same engine options as main conftest)."""
    unique_db_path = os.path.join(tempfile.gettempdir(), f"pytest_api_v1_{uuid.uuid4().hex}.sqlite")
    app = create_app(
        {
            "TESTING": True,
            "FLASK_ENV": "testing",
            "AI_ENABLED": False,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{unique_db_path}",
            "SQLALCHEMY_ENGINE_OPTIONS": {
                "pool_pre_ping": True,
                "connect_args": {"timeout": 30},
                "poolclass": NullPool,
            },
            "WTF_CSRF_ENABLED": False,
            "SERVER_NAME": "localhost:5000",
        }
    )

    with app.app_context():
        db.create_all()
        settings = Settings()
        db.session.add(settings)
        db.session.commit()
        yield app
        db.session.remove()
        try:
            db.drop_all()
        except Exception:
            pass
        try:
            db.engine.dispose()
        except Exception:
            pass
        try:
            if os.path.exists(unique_db_path):
                os.remove(unique_db_path)
        except Exception:
            pass


@pytest.fixture
def client(app):
    """Test client"""
    return app.test_client()


@pytest.fixture
def test_user(app):
    """Create a test user and return its ID"""
    user = User(username="testuser", email="test@example.com")
    user.set_password("password")
    user.is_active = True
    db.session.add(user)
    db.session.commit()
    # Re-query to avoid relying on possibly expired instance state
    uid = db.session.query(User.id).filter_by(username="testuser").scalar()
    return int(uid)


@pytest.fixture
def admin_user(app):
    """Create an admin user"""
    user = User(username="admin", email="admin@example.com", role="admin")
    user.set_password("password")
    user.is_active = True
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def api_token(app, test_user):
    """Create an API token with full permissions (uses app fixture's application context)."""
    user_id = int(test_user)
    token, plain_token = ApiToken.create_token(
        user_id=user_id,
        name="Test Token",
        description="For testing",
        scopes="read:projects,write:projects,read:time_entries,write:time_entries,read:tasks,write:tasks,read:clients,write:clients,read:reports,read:users,read:ai,write:ai",
    )
    db.session.add(token)
    db.session.commit()
    return plain_token


@pytest.fixture
def test_project(app, test_user, test_client_model):
    """Create a test project"""
    project = Project(
        name="Test Project",
        description="A test project",
        hourly_rate=75.0,
        status="active",
        client_id=test_client_model.id,
    )
    db.session.add(project)
    db.session.commit()
    return project


@pytest.fixture
def test_client_model(app):
    """Create a test client"""
    client_model = Client(name="Test Client", email="client@example.com", company="Test Company")
    db.session.add(client_model)
    db.session.commit()
    return client_model


class TestAPIAuthentication:
    """Test API authentication"""

    def test_no_token(self, client):
        """Test request without token"""
        response = client.get("/api/v1/projects")
        assert response.status_code == 401
        data = json.loads(response.data)
        assert "error" in data

    def test_invalid_token(self, client):
        """Test request with invalid token"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/v1/projects", headers=headers)
        assert response.status_code == 401

    def test_valid_bearer_token(self, client, api_token):
        """Test request with valid Bearer token"""
        headers = {"Authorization": f"Bearer {api_token}"}
        response = client.get("/api/v1/projects", headers=headers)
        assert response.status_code == 200

    def test_valid_api_key_header(self, client, api_token):
        """Test request with valid X-API-Key header"""
        headers = {"X-API-Key": api_token}
        response = client.get("/api/v1/projects", headers=headers)
        assert response.status_code == 200

    def test_insufficient_scope(self, app, client, test_user, test_client_model):
        """Test request with insufficient scope"""
        # Create token with limited scope
        token, plain_token = ApiToken.create_token(
            user_id=int(test_user), name="Limited Token", scopes="read:projects"  # Only read access
        )
        db.session.add(token)
        db.session.commit()

        headers = {"Authorization": f"Bearer {plain_token}"}

        # Should work for read
        response = client.get("/api/v1/projects", headers=headers)
        assert response.status_code == 200

        # Should fail for write (include client_id so we hit scope check, not validation)
        response = client.post(
            "/api/v1/projects",
            json={"name": "New Project", "client_id": test_client_model.id},
            headers=headers,
        )
        assert response.status_code == 403
        data = json.loads(response.data)
        assert "Insufficient permissions" in data["error"]


class TestAIHelperAPI:
    """Test shared AI helper API endpoints."""

    def test_ai_context_preview_uses_token_auth(self, app, client, api_token, test_project):
        app.config["AI_ENABLED"] = True
        headers = {"Authorization": f"Bearer {api_token}"}
        response = client.get("/api/v1/ai/context-preview", headers=headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert "context" in data
        assert "provider" in data

    def test_ai_context_preview_returns_503_when_disabled(self, client, api_token):
        headers = {"Authorization": f"Bearer {api_token}"}
        response = client.get("/api/v1/ai/context-preview", headers=headers)
        assert response.status_code == 503
        data = json.loads(response.data)
        assert data["success"] is False
        assert data["error_code"] == "ai_disabled"

    def test_ai_chat_returns_disabled_error_when_not_enabled(self, client, api_token):
        headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
        response = client.post("/api/v1/ai/chat", json={"prompt": "What did I do today?"}, headers=headers)

        assert response.status_code == 503
        data = json.loads(response.data)
        assert data["error_code"] == "ai_disabled"


class TestProjects:
    """Test project endpoints"""

    def test_list_projects(self, client, api_token, test_project):
        """Test listing projects"""
        headers = {"Authorization": f"Bearer {api_token}"}
        response = client.get("/api/v1/projects", headers=headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "projects" in data
        assert "pagination" in data
        assert len(data["projects"]) == 1
        assert data["projects"][0]["name"] == "Test Project"

    def test_get_project(self, client, api_token, test_project):
        """Test getting a single project"""
        headers = {"Authorization": f"Bearer {api_token}"}
        response = client.get(f"/api/v1/projects/{test_project.id}", headers=headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "project" in data
        assert data["project"]["name"] == "Test Project"

    def test_create_project(self, client, api_token, test_client_model):
        """Test creating a project"""
        headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
        project_data = {
            "name": "New Project",
            "description": "A new project",
            "client_id": test_client_model.id,
            "hourly_rate": 100.0,
        }

        response = client.post("/api/v1/projects", json=project_data, headers=headers)

        assert response.status_code == 201
        data = json.loads(response.data)
        assert "project" in data
        assert data["project"]["name"] == "New Project"

    def test_update_project(self, client, api_token, test_project):
        """Test updating a project"""
        headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
        update_data = {"name": "Updated Project", "hourly_rate": 150.0}

        response = client.put(f"/api/v1/projects/{test_project.id}", json=update_data, headers=headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["project"]["name"] == "Updated Project"
        assert data["project"]["hourly_rate"] == 150.0

    def test_delete_project(self, client, api_token, test_project):
        """Test archiving a project"""
        headers = {"Authorization": f"Bearer {api_token}"}
        response = client.delete(f"/api/v1/projects/{test_project.id}", headers=headers)

        assert response.status_code == 200

        # Verify project is archived
        # Ensure we don't read a stale instance from the identity map
        db.session.expire_all()
        project = Project.query.get(test_project.id)
        assert project.status == "archived"


class TestTimeEntries:
    """Test time entry endpoints"""

    def test_list_time_entries(self, client, api_token, test_user, test_project):
        """Test listing time entries"""
        entry = TimeEntry(
            user_id=int(test_user),
            project_id=test_project.id,
            start_time=datetime.utcnow() - timedelta(hours=2),
            end_time=datetime.utcnow(),
            source="api",
            billable=True,
        )
        db.session.add(entry)
        db.session.commit()

        headers = {"Authorization": f"Bearer {api_token}"}
        response = client.get("/api/v1/time-entries", headers=headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "time_entries" in data
        assert len(data["time_entries"]) == 1

    def test_create_time_entry(self, client, api_token, test_project):
        """Test creating a time entry"""
        headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
        entry_data = {
            "project_id": test_project.id,
            "start_time": "2024-01-15T09:00:00Z",
            "end_time": "2024-01-15T17:00:00Z",
            "notes": "Development work",
            "billable": True,
        }

        response = client.post("/api/v1/time-entries", json=entry_data, headers=headers)

        assert response.status_code == 201
        data = json.loads(response.data)
        assert "time_entry" in data
        assert data["time_entry"]["notes"] == "Development work"

    def test_update_time_entry(self, client, api_token, test_user, test_project):
        """Test updating a time entry"""
        entry = TimeEntry(
            user_id=int(test_user),
            project_id=test_project.id,
            start_time=datetime.utcnow() - timedelta(hours=2),
            end_time=datetime.utcnow(),
            notes="Original notes",
            source="api",
            billable=True,
        )
        db.session.add(entry)
        db.session.commit()
        entry_id = entry.id

        headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
        update_data = {"notes": "Updated notes", "billable": False}

        response = client.put(f"/api/v1/time-entries/{entry_id}", json=update_data, headers=headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["time_entry"]["notes"] == "Updated notes"
        assert data["time_entry"]["billable"] is False


class TestTimer:
    """Test timer control endpoints"""

    def test_get_timer_status_no_active(self, client, api_token):
        """Test getting timer status when no timer is active"""
        headers = {"Authorization": f"Bearer {api_token}"}
        response = client.get("/api/v1/timer/status", headers=headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["active"] == False
        assert data["timer"] is None

    def test_start_timer(self, client, api_token, test_project):
        """Test starting a timer"""
        headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
        timer_data = {"project_id": test_project.id}

        response = client.post("/api/v1/timer/start", json=timer_data, headers=headers)

        assert response.status_code == 201
        data = json.loads(response.data)
        assert "timer" in data
        assert data["timer"]["project_id"] == test_project.id

    def test_stop_timer(self, client, api_token, test_user, test_project):
        """Test stopping a timer"""
        timer = TimeEntry(
            user_id=int(test_user),
            project_id=test_project.id,
            start_time=datetime.utcnow(),
            end_time=None,
            source="api",
            billable=True,
        )
        db.session.add(timer)
        db.session.commit()

        headers = {"Authorization": f"Bearer {api_token}"}
        response = client.post("/api/v1/timer/stop", headers=headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "time_entry" in data
        assert data["time_entry"]["end_time"] is not None


class TestTasks:
    """Test task endpoints"""

    def test_list_tasks(self, client, api_token, test_user, test_project):
        """Test listing tasks"""
        task = Task(
            name="Test Task",
            project_id=test_project.id,
            status="todo",
            priority="medium",
            created_by=int(test_user),
        )
        db.session.add(task)
        db.session.commit()

        headers = {"Authorization": f"Bearer {api_token}"}
        response = client.get(f"/api/v1/tasks?project_id={test_project.id}", headers=headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "tasks" in data
        assert len(data["tasks"]) == 1

    def test_create_task(self, client, api_token, test_project):
        """Test creating a task"""
        headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
        task_data = {
            "name": "New Task",
            "description": "Task description",
            "project_id": test_project.id,
            "status": "todo",
            "priority": "medium",
        }

        response = client.post("/api/v1/tasks", json=task_data, headers=headers)

        assert response.status_code == 201
        data = json.loads(response.data)
        assert "task" in data
        assert data["task"]["name"] == "New Task"


class TestClients:
    """Test client endpoints"""

    def test_list_clients(self, client, api_token, test_client_model):
        """Test listing clients"""
        headers = {"Authorization": f"Bearer {api_token}"}
        response = client.get("/api/v1/clients", headers=headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "clients" in data
        assert len(data["clients"]) == 1

    def test_create_client(self, client, api_token):
        """Test creating a client"""
        headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
        client_data = {"name": "New Client", "email": "newclient@example.com", "company": "New Company"}

        response = client.post("/api/v1/clients", json=client_data, headers=headers)

        assert response.status_code == 201
        data = json.loads(response.data)
        assert "client" in data
        assert data["client"]["name"] == "New Client"


class TestReports:
    """Test report endpoints"""

    def test_summary_report(self, client, api_token, test_user, test_project):
        """Test getting summary report"""
        now = datetime.utcnow()
        entry1 = TimeEntry(
            user_id=int(test_user),
            project_id=test_project.id,
            start_time=now - timedelta(hours=10),
            end_time=now - timedelta(hours=8),
            source="api",
            billable=True,
        )
        entry2 = TimeEntry(
            user_id=int(test_user),
            project_id=test_project.id,
            start_time=now - timedelta(hours=5),
            end_time=now - timedelta(hours=3),
            billable=True,
            source="api",
        )
        db.session.add_all([entry1, entry2])
        db.session.commit()

        headers = {"Authorization": f"Bearer {api_token}"}
        response = client.get("/api/v1/reports/summary", headers=headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "summary" in data
        assert data["summary"]["total_entries"] == 2


class TestPagination:
    """Test pagination"""

    def test_pagination_params(self, client, api_token, test_project, test_client_model):
        """Test pagination parameters"""
        for i in range(15):
            project = Project(
                name=f"Paginate Project {i}",
                status="active",
                client_id=test_client_model.id,
            )
            db.session.add(project)
        db.session.commit()

        headers = {"Authorization": f"Bearer {api_token}"}

        # Test per_page (1 from test_project fixture + 15 new = 16 active projects)
        response = client.get("/api/v1/projects?per_page=5", headers=headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data["projects"]) == 5
        assert data["pagination"]["per_page"] == 5

        # Test page
        response = client.get("/api/v1/projects?page=2&per_page=5", headers=headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["pagination"]["page"] == 2


class TestSystemEndpoints:
    """Test system endpoints"""

    def test_api_info(self, client):
        """Test API info endpoint (no auth required)"""
        response = client.get("/api/v1/info")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "api_version" in data
        assert "endpoints" in data
        assert "setup_required" in data
        assert isinstance(data["setup_required"], bool)

    def test_health_check(self, client):
        """Test health check endpoint (no auth required)"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "healthy"
