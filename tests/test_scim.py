"""SCIM 2.0 Users API tests (bearer auth)."""

from __future__ import annotations

import os
import tempfile
import uuid

import pytest

from app import create_app, db
from app.models import User


@pytest.fixture
def scim_app(app_config):
    unique_db_path = os.path.join(tempfile.gettempdir(), f"pytest_scim_{uuid.uuid4().hex}.sqlite")
    config = dict(app_config)
    config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{unique_db_path}"
    config["SCIM_ENABLED"] = True
    config["SCIM_BEARER_TOKEN"] = "test-scim-secret-token"
    application = create_app(config)
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()
    try:
        os.unlink(unique_db_path)
    except OSError:
        pass


@pytest.fixture
def scim_client(scim_app):
    return scim_app.test_client()


def _auth():
    return {"Authorization": "Bearer test-scim-secret-token", "Content-Type": "application/scim+json"}


def test_scim_unauthorized(scim_client):
    resp = scim_client.get("/scim/v2/Users")
    assert resp.status_code == 401


def test_scim_list_empty(scim_client):
    resp = scim_client.get("/scim/v2/Users", headers=_auth())
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["totalResults"] == 0
    assert body["Resources"] == []


def test_scim_create_get_patch_delete(scim_client, scim_app):
    create = scim_client.post(
        "/scim/v2/Users",
        headers=_auth(),
        json={
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "scimuser1",
            "externalId": "ext-123",
            "name": {"formatted": "SCIM User", "givenName": "SCIM", "familyName": "User"},
            "emails": [{"value": "scimuser1@example.com", "type": "work", "primary": True}],
            "active": True,
        },
    )
    assert create.status_code == 201
    created = create.get_json()
    assert created["userName"] == "scimuser1"
    assert created["externalId"] == "ext-123"
    uid = created["id"]

    get_resp = scim_client.get(f"/scim/v2/Users/{uid}", headers=_auth())
    assert get_resp.status_code == 200
    assert get_resp.get_json()["emails"][0]["value"] == "scimuser1@example.com"

    # Filter by userName
    filt = scim_client.get('/scim/v2/Users?filter=userName eq "scimuser1"', headers=_auth())
    assert filt.status_code == 200
    assert filt.get_json()["totalResults"] == 1

    # Filter by externalId
    filt2 = scim_client.get('/scim/v2/Users?filter=externalId eq "ext-123"', headers=_auth())
    assert filt2.status_code == 200
    assert filt2.get_json()["totalResults"] == 1

    patch = scim_client.patch(
        f"/scim/v2/Users/{uid}",
        headers=_auth(),
        json={
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [{"op": "replace", "path": "active", "value": False}],
        },
    )
    assert patch.status_code == 200
    assert patch.get_json()["active"] is False

    delete = scim_client.delete(f"/scim/v2/Users/{uid}", headers=_auth())
    assert delete.status_code == 204

    with scim_app.app_context():
        user = User.query.get(int(uid))
        assert user is not None
        assert user.is_active is False


def test_scim_discovery(scim_client):
    for path in (
        "/scim/v2/ServiceProviderConfig",
        "/scim/v2/ResourceTypes",
        "/scim/v2/Schemas",
    ):
        resp = scim_client.get(path, headers=_auth())
        assert resp.status_code == 200, path
