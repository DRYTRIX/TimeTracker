"""Regression: SCIM writes must not require CSRF (GitHub #909).

IdPs call POST /scim/v2/Users with Bearer tokens and no CSRF header.
"""

import pytest
from sqlalchemy.pool import NullPool

pytestmark = [pytest.mark.integration]


@pytest.fixture
def app_config():
    """Override conftest app_config so CSRF is enabled at create_app time."""
    return {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///pytest_scim_csrf.sqlite",
        "SQLALCHEMY_ENGINE_OPTIONS": {
            "pool_pre_ping": True,
            "connect_args": {"timeout": 30},
            "poolclass": NullPool,
        },
        "FLASK_ENV": "testing",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "WTF_CSRF_ENABLED": True,
        "WTF_CSRF_SSL_STRICT": False,
        "SECRET_KEY": "test-secret-key-do-not-use-in-production",
        "SERVER_NAME": "localhost:5000",
        "APPLICATION_ROOT": "/",
        "PREFERRED_URL_SCHEME": "http",
        "SESSION_COOKIE_HTTPONLY": True,
        "BABEL_DEFAULT_LOCALE": "en",
        "SCIM_ENABLED": True,
        "SCIM_BEARER_TOKEN": "test-scim-secret-token",
    }


def test_scim_post_users_skips_csrf(client):
    """Bearer POST /scim/v2/Users must not fail with csrf_token_missing_or_invalid."""
    resp = client.post(
        "/scim/v2/Users",
        json={
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "scimcsrf1",
            "emails": [{"value": "scimcsrf1@example.com", "primary": True}],
            "active": True,
        },
        headers={
            "Authorization": "Bearer test-scim-secret-token",
            "Content-Type": "application/scim+json",
            "Accept": "application/scim+json",
        },
    )
    body = resp.get_json() or {}
    assert body.get("error") != "csrf_token_missing_or_invalid"
    assert resp.status_code == 201
