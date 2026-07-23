"""Regression tests for CSRF path exemption on /api/v1 (GitHub #695).

Mobile/desktop clients call POST /api/v1/timer/start with Bearer tokens and no
CSRF header. CSRF must stay enabled for browser session routes under /api/kiosk.
"""

from sqlalchemy.pool import NullPool

import pytest

pytestmark = [pytest.mark.integration]


@pytest.fixture
def app_config():
    """Override conftest app_config so CSRF is enabled at create_app time."""
    return {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///pytest_csrf.sqlite",
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
    }


def test_api_v1_timer_start_skips_csrf_with_bearer(client, project, api_token):
    """Bearer POST /api/v1/timer/start must not fail with csrf_token_missing_or_invalid."""
    _, plain_token = api_token
    resp = client.post(
        "/api/v1/timer/start",
        json={"project_id": project.id},
        headers={
            "Authorization": f"Bearer {plain_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    body = resp.get_json() or {}
    assert body.get("error") != "csrf_token_missing_or_invalid"
    assert resp.status_code == 201
    assert "timer" in body


def test_api_kiosk_still_requires_csrf(client):
    """Path exemption must not blanket-exempt all /api/* routes."""
    resp = client.post(
        "/api/kiosk/start-timer",
        json={"project_id": 1},
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    assert resp.status_code == 400
    assert (resp.get_json() or {}).get("error") == "csrf_token_missing_or_invalid"
