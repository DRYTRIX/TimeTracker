"""API v1 CRUD for project rate overrides."""

import os
import tempfile
import uuid
from datetime import date
from decimal import Decimal

import pytest

from app import create_app, db
from app.models import ApiToken, Client, Project, RateOverride, User

pytestmark = [pytest.mark.api, pytest.mark.integration]


@pytest.fixture
def app():
    unique_db_path = os.path.join(tempfile.gettempdir(), f"test_api_rate_overrides_{uuid.uuid4().hex}.sqlite")

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{unique_db_path}",
            "WTF_CSRF_ENABLED": False,
        }
    )
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user(app):
    u = User(username="rateuser", email="rate@example.com", role="admin")
    u.is_active = True
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def other_user(app):
    u = User(username="otherperson", email="other@example.com", role="user")
    u.is_active = True
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def api_token(app, user):
    token, plain = ApiToken.create_token(
        user_id=user.id, name="RateOverrides Token", scopes="read:projects,write:projects"
    )
    db.session.add(token)
    db.session.commit()
    return plain


@pytest.fixture
def read_only_token(app, user):
    token, plain = ApiToken.create_token(user_id=user.id, name="Read Only", scopes="read:projects")
    db.session.add(token)
    db.session.commit()
    return plain


@pytest.fixture
def project(app):
    c = Client(name="Rate Client")
    db.session.add(c)
    db.session.commit()
    p = Project(name="Rate Project", client_id=c.id, status="active", hourly_rate=Decimal("50.00"))
    db.session.add(p)
    db.session.commit()
    return p


def _auth(t):
    return {"Authorization": f"Bearer {t}", "Content-Type": "application/json"}


def test_rate_overrides_crud(client, api_token, project, other_user):
    r = client.get(f"/api/v1/projects/{project.id}/rate-overrides", headers=_auth(api_token))
    assert r.status_code == 200
    assert r.get_json()["rate_overrides"] == []

    r = client.post(
        f"/api/v1/projects/{project.id}/rate-overrides",
        headers=_auth(api_token),
        json={
            "user_id": other_user.id,
            "hourly_rate": 120.5,
            "effective_from": "2024-01-01",
            "effective_to": "2024-06-30",
        },
    )
    assert r.status_code == 201
    body = r.get_json()["rate_override"]
    assert body["hourly_rate"] == 120.5
    assert body["user_id"] == other_user.id
    assert body["effective_from"] == "2024-01-01"
    override_id = body["id"]

    r = client.get(f"/api/v1/rate-overrides/{override_id}", headers=_auth(api_token))
    assert r.status_code == 200
    assert r.get_json()["rate_override"]["id"] == override_id

    r = client.patch(
        f"/api/v1/rate-overrides/{override_id}",
        headers=_auth(api_token),
        json={"hourly_rate": 130},
    )
    assert r.status_code == 200
    assert r.get_json()["rate_override"]["hourly_rate"] == 130.0

    r = client.delete(f"/api/v1/rate-overrides/{override_id}", headers=_auth(api_token))
    assert r.status_code == 200
    assert RateOverride.query.get(override_id) is None


def test_create_project_wide_override(client, api_token, project):
    r = client.post(
        f"/api/v1/projects/{project.id}/rate-overrides",
        headers=_auth(api_token),
        json={"hourly_rate": 90, "user_id": None},
    )
    assert r.status_code == 201
    body = r.get_json()["rate_override"]
    assert body["user_id"] is None
    assert body["hourly_rate"] == 90.0


def test_write_requires_write_scope(client, read_only_token, project):
    r = client.post(
        f"/api/v1/projects/{project.id}/rate-overrides",
        headers=_auth(read_only_token),
        json={"hourly_rate": 100},
    )
    assert r.status_code == 403


def test_rejects_negative_rate(client, api_token, project):
    r = client.post(
        f"/api/v1/projects/{project.id}/rate-overrides",
        headers=_auth(api_token),
        json={"hourly_rate": -5},
    )
    assert r.status_code == 400
    errors = r.get_json().get("errors") or {}
    assert "hourly_rate" in errors


def test_rejects_inverted_dates(client, api_token, project):
    r = client.post(
        f"/api/v1/projects/{project.id}/rate-overrides",
        headers=_auth(api_token),
        json={"hourly_rate": 80, "effective_from": "2024-06-01", "effective_to": "2024-01-01"},
    )
    assert r.status_code == 400
    errors = r.get_json().get("errors") or {}
    assert "effective_to" in errors


def test_rejects_overlapping_windows(client, api_token, project, other_user):
    first = RateOverride(
        project_id=project.id,
        user_id=other_user.id,
        hourly_rate=Decimal("100"),
        effective_from=date(2024, 1, 1),
        effective_to=date(2024, 6, 30),
    )
    db.session.add(first)
    db.session.commit()

    r = client.post(
        f"/api/v1/projects/{project.id}/rate-overrides",
        headers=_auth(api_token),
        json={
            "user_id": other_user.id,
            "hourly_rate": 110,
            "effective_from": "2024-06-01",
            "effective_to": "2024-12-31",
        },
    )
    assert r.status_code == 400
    errors = r.get_json().get("errors") or {}
    assert "effective_from" in errors


def test_allows_non_overlapping_windows(client, api_token, project, other_user):
    first = RateOverride(
        project_id=project.id,
        user_id=other_user.id,
        hourly_rate=Decimal("100"),
        effective_from=date(2024, 1, 1),
        effective_to=date(2024, 6, 30),
    )
    db.session.add(first)
    db.session.commit()

    r = client.post(
        f"/api/v1/projects/{project.id}/rate-overrides",
        headers=_auth(api_token),
        json={
            "user_id": other_user.id,
            "hourly_rate": 110,
            "effective_from": "2024-07-01",
            "effective_to": "2024-12-31",
        },
    )
    assert r.status_code == 201
