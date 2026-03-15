"""
Tests for scope_filter utilities (issue access helper).
"""

from datetime import datetime

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.utils]

from app.utils.scope_filter import (
    get_accessible_project_and_client_ids_for_user,
    get_allowed_client_ids,
    get_allowed_project_ids,
    apply_client_scope_to_model,
    apply_project_scope_to_model,
    user_can_access_client,
    user_can_access_project,
)
from app.models import User, Project, Task, Client, Role, UserClient
from app import db
from app.repositories import TimeEntryRepository


# ---------------------------------------------------------------------------
# get_accessible_project_and_client_ids_for_user (existing)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_get_accessible_project_and_client_ids_for_user_empty(db_session):
    """User with no time entries and no task assignments gets empty sets."""
    user = User(username="noprojects", role="user")
    db_session.add(user)
    db_session.commit()

    project_ids, client_ids = get_accessible_project_and_client_ids_for_user(user.id)
    assert project_ids == set()
    assert client_ids == set()


@pytest.mark.integration
def test_get_accessible_project_and_client_ids_for_user_via_time_entries(db_session):
    """User with time entries gets those projects and their clients."""
    user = User(username="timer_user", role="user")
    db_session.add(user)
    client = Client(name="Acme")
    db_session.add(client)
    db_session.commit()
    project = Project(name="P1", client_id=client.id, status="active")
    db_session.add(project)
    db_session.commit()

    repo = TimeEntryRepository()
    repo.create_manual_entry(
        user_id=user.id,
        project_id=project.id,
        start_time=datetime.now(),
        end_time=datetime.now(),
    )
    db_session.commit()

    project_ids, client_ids = get_accessible_project_and_client_ids_for_user(user.id)
    assert project_ids == {project.id}
    assert client_ids == {client.id}


# ---------------------------------------------------------------------------
# get_allowed_client_ids / get_allowed_project_ids
# ---------------------------------------------------------------------------


def test_get_allowed_client_ids_unrestricted_user(app, user):
    """Non-scope-restricted user gets None (full access) from get_allowed_client_ids when passed explicitly."""
    with app.app_context():
        # user fixture has no subcontractor role
        result = get_allowed_client_ids(user=user)
        assert result is None


def test_get_allowed_project_ids_unrestricted_user(app, user):
    """Non-scope-restricted user gets None (full access) from get_allowed_project_ids when passed explicitly."""
    with app.app_context():
        result = get_allowed_project_ids(user=user)
        assert result is None


def test_get_allowed_client_ids_scope_restricted(app, scope_restricted_user, test_client):
    """Scope-restricted user gets list of allowed client IDs."""
    with app.app_context():
        result = get_allowed_client_ids(user=scope_restricted_user)
        assert result is not None
        assert test_client.id in result


def test_get_allowed_project_ids_scope_restricted(app, scope_restricted_user, project):
    """Scope-restricted user gets list of allowed project IDs (projects under assigned clients)."""
    with app.app_context():
        result = get_allowed_project_ids(user=scope_restricted_user)
        assert result is not None
        assert project.id in result


# ---------------------------------------------------------------------------
# user_can_access_client / user_can_access_project
# ---------------------------------------------------------------------------


def test_user_can_access_client_admin(admin_user, test_client):
    """Admin can access any client."""
    assert user_can_access_client(admin_user, test_client.id) is True


def test_user_can_access_client_unrestricted(user, test_client):
    """Non-scope-restricted user can access any client."""
    assert user_can_access_client(user, test_client.id) is True


def test_user_can_access_client_scope_restricted_allowed(scope_restricted_user, test_client):
    """Scope-restricted user can access assigned client."""
    assert user_can_access_client(scope_restricted_user, test_client.id) is True


def test_user_can_access_client_scope_restricted_denied(app, scope_restricted_user, test_client):
    """Scope-restricted user cannot access non-assigned client."""
    with app.app_context():
        other = Client(name="Other Corp", email="other@example.com")
        db.session.add(other)
        db.session.commit()
        assert user_can_access_client(scope_restricted_user, other.id) is False


def test_user_can_access_project_scope_restricted_allowed(scope_restricted_user, project):
    """Scope-restricted user can access project under assigned client."""
    assert user_can_access_project(scope_restricted_user, project.id) is True


def test_user_can_access_project_scope_restricted_denied(app, scope_restricted_user, project, test_client):
    """Scope-restricted user cannot access project under another client."""
    with app.app_context():
        other_client = Client(name="Other Corp", email="other@example.com")
        db.session.add(other_client)
        db.session.commit()
        other_project = Project(name="Other Project", client_id=other_client.id, status="active")
        db.session.add(other_project)
        db.session.commit()
        assert user_can_access_project(scope_restricted_user, other_project.id) is False


# ---------------------------------------------------------------------------
# apply_client_scope_to_model / apply_project_scope_to_model
# ---------------------------------------------------------------------------


def test_apply_client_scope_to_model_unrestricted(app, user):
    """Unrestricted user: no filter applied (None)."""
    with app.app_context():
        from app.models import Client as ClientModel

        scope = apply_client_scope_to_model(ClientModel, user=user)
        assert scope is None


def test_apply_client_scope_to_model_scope_restricted(app, scope_restricted_user, test_client):
    """Scope-restricted user: filter restricts to assigned clients only."""
    with app.app_context():
        from app.models import Client as ClientModel

        scope = apply_client_scope_to_model(ClientModel, user=scope_restricted_user)
        assert scope is not None
        q = ClientModel.query.filter(scope)
        assert q.count() >= 1
        ids = [c.id for c in q.all()]
        assert test_client.id in ids


def test_apply_project_scope_to_model_unrestricted(app, user):
    """Unrestricted user: no filter applied (None)."""
    with app.app_context():
        from app.models import Project as ProjectModel

        scope = apply_project_scope_to_model(ProjectModel, user=user)
        assert scope is None


def test_apply_project_scope_to_model_scope_restricted(app, scope_restricted_user, project):
    """Scope-restricted user: filter restricts to projects under assigned clients."""
    with app.app_context():
        from app.models import Project as ProjectModel

        scope = apply_project_scope_to_model(ProjectModel, user=scope_restricted_user)
        assert scope is not None
        q = ProjectModel.query.filter(scope)
        assert q.count() >= 1
        ids = [p.id for p in q.all()]
        assert project.id in ids


# ---------------------------------------------------------------------------
# Integration: API list filtered by scope-restricted user
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.api
def test_api_projects_list_filtered_by_scope(app, scope_restricted_user, project, test_client):
    """Scope-restricted user calling GET /api/v1/projects sees only projects for assigned client."""
    with app.app_context():
        other_client = Client(name="Other Corp", email="other@example.com")
        db.session.add(other_client)
        db.session.commit()
        other_project = Project(name="Other Project", client_id=other_client.id, status="active")
        db.session.add(other_project)
        db.session.commit()
        allowed_project_id = int(project.id)
        other_project_id = int(other_project.id)

        from app.models import ApiToken

        token, plain = ApiToken.create_token(
            user_id=scope_restricted_user.id,
            name="Sub token",
            scopes="read:projects",
            expires_days=30,
        )
        db.session.add(token)
        db.session.commit()

    client = app.test_client()
    client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {plain}"
    resp = client.get("/api/v1/projects")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "projects" in data
    project_ids = [p["id"] for p in data["projects"]]
    assert allowed_project_id in project_ids
    assert other_project_id not in project_ids
