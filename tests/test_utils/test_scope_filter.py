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
    apply_project_scope,
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


def test_get_allowed_client_ids_unrestricted_user(app, admin_user):
    """Admin gets None (full access) from get_allowed_client_ids."""
    with app.app_context():
        result = get_allowed_client_ids(user=admin_user)
        assert result is None


def test_get_allowed_project_ids_unrestricted_user(app, admin_user):
    """Admin gets None (full access) from get_allowed_project_ids."""
    with app.app_context():
        result = get_allowed_project_ids(user=admin_user)
        assert result is None


@pytest.fixture
def client_portal_scoped_user(app, test_client, project):
    """Viewer (or read-only) user with client_portal_enabled and client_id — not a subcontractor."""
    role = Role.query.filter_by(name="viewer").first()
    if not role:
        role = Role(name="viewer", description="Read-only User", is_system_role=True)
        db.session.add(role)
        db.session.flush()

    existing = User.query.filter_by(username="client_portal_scope_user").first()
    if existing:
        existing.client_portal_enabled = True
        existing.client_id = test_client.id
        existing.is_active = True
        existing.set_password("password123")
        if role not in existing.roles:
            existing.roles.append(role)
        db.session.commit()
        db.session.refresh(existing)
        _ = list(existing.roles)
        return existing

    cp_user = User(
        username="client_portal_scope_user",
        email="portalscope@example.com",
        role="viewer",
    )
    cp_user.is_active = True
    cp_user.set_password("password123")
    cp_user.client_portal_enabled = True
    cp_user.client_id = test_client.id
    db.session.add(cp_user)
    db.session.flush()
    if role not in cp_user.roles:
        cp_user.roles.append(role)
    db.session.commit()
    db.session.refresh(cp_user)
    _ = list(cp_user.roles)
    return cp_user


def test_get_allowed_client_ids_client_portal_user(app, client_portal_scoped_user, test_client):
    """Client portal user gets exactly their linked client ID."""
    with app.app_context():
        result = get_allowed_client_ids(user=client_portal_scoped_user)
        assert result == [test_client.id]


def test_get_allowed_project_ids_client_portal_user(app, client_portal_scoped_user, project):
    """Client portal user gets project IDs only for their client."""
    with app.app_context():
        result = get_allowed_project_ids(user=client_portal_scoped_user)
        assert result is not None
        assert project.id in result


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


def test_user_can_access_client_unrestricted(admin_user, test_client):
    """Admin can access any client (full access)."""
    assert user_can_access_client(admin_user, test_client.id) is True


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


def test_user_can_access_client_client_portal_allowed(client_portal_scoped_user, test_client):
    """Client portal user can access their linked client."""
    assert user_can_access_client(client_portal_scoped_user, test_client.id) is True


def test_user_can_access_client_client_portal_denied(app, client_portal_scoped_user):
    """Client portal user cannot access another client."""
    with app.app_context():
        other = Client(name="Portal Other Corp", email="portal_other@example.com")
        db.session.add(other)
        db.session.commit()
        assert user_can_access_client(client_portal_scoped_user, other.id) is False


def test_user_can_access_project_client_portal_allowed(client_portal_scoped_user, project):
    """Client portal user can access a project under their client."""
    assert user_can_access_project(client_portal_scoped_user, project.id) is True


def test_user_can_access_project_client_portal_denied(app, client_portal_scoped_user):
    """Client portal user cannot access a project under another client."""
    with app.app_context():
        other_client = Client(name="Portal Other Client", email="portal_other_client@example.com")
        db.session.add(other_client)
        db.session.commit()
        other_project = Project(name="Portal Other Project", client_id=other_client.id, status="active")
        db.session.add(other_project)
        db.session.commit()
        assert user_can_access_project(client_portal_scoped_user, other_project.id) is False


# ---------------------------------------------------------------------------
# apply_client_scope_to_model / apply_project_scope_to_model
# ---------------------------------------------------------------------------


def test_apply_client_scope_to_model_unrestricted(app, admin_user):
    """Admin: no filter applied (None)."""
    with app.app_context():
        from app.models import Client as ClientModel

        scope = apply_client_scope_to_model(ClientModel, user=admin_user)
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


def test_apply_project_scope_to_model_unrestricted(app, admin_user):
    """Admin: no filter applied (None)."""
    with app.app_context():
        from app.models import Project as ProjectModel

        scope = apply_project_scope_to_model(ProjectModel, user=admin_user)
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


def test_apply_project_scope_query_unrestricted(app, admin_user):
    """apply_project_scope leaves query unchanged for admin users."""
    with app.app_context():
        from app.models import Project as ProjectModel

        base = ProjectModel.query
        scoped = apply_project_scope(ProjectModel, base, user=admin_user)
        assert scoped is base


def test_apply_project_scope_query_restricted(app, scope_restricted_user, project):
    """apply_project_scope filters Project query for scope-restricted users."""
    with app.app_context():
        from app.models import Project as ProjectModel

        base = ProjectModel.query
        scoped = apply_project_scope(ProjectModel, base, user=scope_restricted_user)
        assert scoped is not base
        assert project.id in {p.id for p in scoped.all()}


def test_apply_project_scope_to_model_client_portal(app, client_portal_scoped_user, project):
    """Client portal user: project scope filter includes only their client's projects."""
    with app.app_context():
        from app.models import Project as ProjectModel

        scope = apply_project_scope_to_model(ProjectModel, user=client_portal_scoped_user)
        assert scope is not None
        q = ProjectModel.query.filter(scope)
        ids = {p.id for p in q.all()}
        assert project.id in ids


def test_apply_project_scope_query_client_portal(app, client_portal_scoped_user, project):
    """apply_project_scope filters Project query for client portal users."""
    with app.app_context():
        from app.models import Project as ProjectModel

        base = ProjectModel.query
        scoped = apply_project_scope(ProjectModel, base, user=client_portal_scoped_user)
        assert scoped is not base
        assert project.id in {p.id for p in scoped.all()}


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


@pytest.mark.integration
@pytest.mark.api
def test_api_projects_list_filtered_by_client_portal(app, client_portal_scoped_user, project, test_client):
    """Client portal user calling GET /api/v1/projects sees only projects for their linked client."""
    with app.app_context():
        other_client = Client(name="Portal API Other Corp", email="portal_api_other@example.com")
        db.session.add(other_client)
        db.session.commit()
        other_project = Project(name="Portal API Other Project", client_id=other_client.id, status="active")
        db.session.add(other_project)
        db.session.commit()
        allowed_project_id = int(project.id)
        other_project_id = int(other_project.id)

        from app.models import ApiToken

        token, plain = ApiToken.create_token(
            user_id=client_portal_scoped_user.id,
            name="Portal scope token",
            scopes="read:projects",
            expires_days=30,
        )
        db.session.add(token)
        db.session.commit()

    tc = app.test_client()
    tc.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {plain}"
    resp = tc.get("/api/v1/projects")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "projects" in data
    project_ids = [p["id"] for p in data["projects"]]
    assert allowed_project_id in project_ids
    assert other_project_id not in project_ids


# ---------------------------------------------------------------------------
# Own-scope (issue #641): created_by workspace isolation
# ---------------------------------------------------------------------------


@pytest.fixture
def own_scope_user(app):
    """User with view_own_clients / view_own_projects only (standard user role after #641)."""
    from app.models import Role
    from app.utils.permissions_seed import seed_permissions, seed_roles

    with app.app_context():
        seed_permissions()
        seed_roles(silent=True)
        role = Role.query.filter_by(name="user").first()
        user = User.query.filter_by(username="own_scope_user").first()
        if not user:
            user = User(username="own_scope_user", email="ownscope@example.com", role="user")
            user.is_active = True
            user.set_password("password123")
            db.session.add(user)
        if role and role not in user.roles:
            user.roles.append(role)
        db.session.commit()
        db.session.refresh(user)
        return user


@pytest.mark.integration
def test_own_scope_client_ids(app, own_scope_user, db_session):
    """User with view_own_clients sees only clients they created; legacy NULL rows are hidden."""
    with app.app_context():
        other_user = User(username="other_scope_client", email="otherc@example.com", role="user")
        other_user.is_active = True
        db_session.add(other_user)
        db_session.flush()

        mine = Client(name="Mine Corp", created_by=own_scope_user.id)
        other = Client(name="Other Corp", created_by=other_user.id)
        legacy = Client(name="Legacy Corp", created_by=None)
        db_session.add_all([mine, other, legacy])
        db_session.commit()

        allowed = get_allowed_client_ids(user=own_scope_user)
        assert allowed is not None
        assert mine.id in allowed
        assert other.id not in allowed
        assert legacy.id not in allowed


@pytest.mark.integration
def test_own_scope_project_ids(app, own_scope_user, db_session, test_client):
    """User with view_own_projects sees only projects they created."""
    with app.app_context():
        mine = Project(
            name="My Project",
            client_id=test_client.id,
            status="active",
            created_by=own_scope_user.id,
        )
        other_user = User(username="other_scope_proj", email="otherp@example.com", role="user")
        db_session.add(other_user)
        db_session.flush()
        other = Project(
            name="Other Project",
            client_id=test_client.id,
            status="active",
            created_by=other_user.id,
        )
        db_session.add_all([mine, other])
        db_session.commit()

        allowed = get_allowed_project_ids(user=own_scope_user)
        assert allowed is not None
        assert mine.id in allowed
        assert other.id not in allowed


@pytest.mark.integration
def test_legacy_client_visible_to_view_all_role(app, db_session):
    """Legacy client (created_by NULL) is visible to users with view_all_clients."""
    from app.models import Role
    from app.utils.permissions_seed import seed_permissions, seed_roles

    with app.app_context():
        seed_permissions()
        seed_roles(silent=True)
        manager_role = Role.query.filter_by(name="manager").first()
        mgr = User.query.filter_by(username="mgr_scope_test").first()
        if not mgr:
            mgr = User(username="mgr_scope_test", email="mgr@example.com", role="manager")
            mgr.is_active = True
            mgr.set_password("password123")
            db.session.add(mgr)
        if manager_role and manager_role not in mgr.roles:
            mgr.roles.append(manager_role)
        legacy = Client(name="Legacy Visible", created_by=None)
        db_session.add(legacy)
        db.session.commit()

        allowed = get_allowed_client_ids(user=mgr)
        assert allowed is None
