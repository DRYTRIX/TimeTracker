"""CSRF protection for POST /time-entries/bulk-billable (CSRF enabled at create_app time)."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy.pool import NullPool

from app import db
from app.models import TimeEntry

pytestmark = [pytest.mark.routes, pytest.mark.integration]


@pytest.fixture
def app_config():
    """Override conftest app_config so CSRF is enabled at create_app time."""
    return {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///pytest_bulk_billable_csrf.sqlite",
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


def _completed_entry(user_id, project_id):
    start = datetime.utcnow() - timedelta(hours=3)
    entry = TimeEntry(
        user_id=user_id,
        project_id=project_id,
        start_time=start,
        end_time=start + timedelta(hours=1),
        source="manual",
        billable=True,
    )
    db.session.add(entry)
    db.session.commit()
    return entry.id


def _billable(entry_id):
    db.session.expire_all()
    return TimeEntry.query.get(entry_id).billable


def test_bulk_mark_billable_without_csrf_token_is_rejected(app, authenticated_client, user, project):
    entry_id = _completed_entry(user.id, project.id)

    resp = authenticated_client.post(
        "/time-entries/bulk-billable", data={"entry_ids[]": [str(entry_id)], "set_billable": "false"}
    )

    assert resp.status_code in (302, 400)
    assert _billable(entry_id) is True


def test_bulk_mark_billable_with_csrf_token_is_accepted(app, authenticated_client, user, project):
    entry_id = _completed_entry(user.id, project.id)
    token = (authenticated_client.get("/auth/csrf-token").get_json() or {}).get("csrf_token")

    resp = authenticated_client.post(
        "/time-entries/bulk-billable",
        data={"entry_ids[]": [str(entry_id)], "set_billable": "false", "csrf_token": token},
    )

    assert resp.status_code == 302
    assert _billable(entry_id) is False
