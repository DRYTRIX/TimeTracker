"""Tests for admin booking time for other users (Issue #701)."""

from datetime import datetime, timedelta

import pytest
from flask import url_for

from app import db
from app.models import ApiToken, TimeEntry, User

pytestmark = [pytest.mark.routes]


@pytest.mark.routes
def test_admin_manual_entry_shows_user_select(admin_authenticated_client, admin_user, user):
    """Admin GET /timer/manual shows a user select with active users."""
    response = admin_authenticated_client.get(url_for("timer.manual_entry"))
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert 'name="user_id"' in html
    assert 'id="user_id"' in html
    assert admin_user.display_name in html or admin_user.username in html
    assert user.display_name in html or user.username in html


@pytest.mark.routes
def test_non_admin_manual_entry_hides_user_select(authenticated_client):
    """Non-admin GET /timer/manual does not show the user select."""
    response = authenticated_client.get(url_for("timer.manual_entry"))
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert 'name="user_id"' not in html
    assert "Log time for" not in html


@pytest.mark.routes
def test_admin_can_create_manual_entry_for_other_user(admin_authenticated_client, admin_user, user, project, app):
    """Admin POST with user_id creates an entry owned by that user."""
    response = admin_authenticated_client.post(
        "/timer/manual",
        data={
            "user_id": user.id,
            "project_id": project.id,
            "start_date": "2025-06-01",
            "start_time": "09:00",
            "end_date": "2025-06-01",
            "end_time": "10:00",
            "notes": "Booked by admin",
            "billable": "on",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        entry = TimeEntry.query.filter_by(notes="Booked by admin").first()
        assert entry is not None
        assert entry.user_id == user.id
        assert entry.user_id != admin_user.id


@pytest.mark.routes
def test_non_admin_cannot_create_manual_entry_for_other_user(authenticated_client, user, admin_user, project, app):
    """Non-admin POST with foreign user_id still creates as themselves."""
    response = authenticated_client.post(
        "/timer/manual",
        data={
            "user_id": admin_user.id,
            "project_id": project.id,
            "start_date": "2025-06-02",
            "start_time": "09:00",
            "end_date": "2025-06-02",
            "end_time": "10:00",
            "notes": "Forged user_id attempt",
            "billable": "on",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        entry = TimeEntry.query.filter_by(notes="Forged user_id attempt").first()
        assert entry is not None
        assert entry.user_id == user.id
        assert entry.user_id != admin_user.id


@pytest.mark.routes
def test_admin_invalid_user_id_rejected(admin_authenticated_client, project, app):
    """Admin POST with inactive/invalid user_id fails with an error."""
    with app.app_context():
        inactive = User(username="inactive_teammate", role="user", email="inactive@example.com")
        inactive.is_active = False
        inactive.set_password("password123")
        db.session.add(inactive)
        db.session.commit()
        inactive_id = inactive.id

    response = admin_authenticated_client.post(
        "/timer/manual",
        data={
            "user_id": inactive_id,
            "project_id": project.id,
            "start_date": "2025-06-03",
            "start_time": "09:00",
            "end_date": "2025-06-03",
            "end_time": "10:00",
            "notes": "Should not create",
            "billable": "on",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"invalid or inactive" in response.data.lower() or b"Selected user" in response.data

    with app.app_context():
        assert TimeEntry.query.filter_by(notes="Should not create").first() is None


@pytest.mark.routes
def test_admin_bulk_entry_shows_user_select(admin_authenticated_client):
    """Admin GET /timer/bulk shows user select."""
    response = admin_authenticated_client.get(url_for("timer.bulk_entry"))
    assert response.status_code == 200
    assert b'name="user_id"' in response.data


@pytest.mark.api
def test_api_admin_can_create_for_other_user(app, admin_user, user, project):
    """API v1: admin token may pass user_id to create for another user."""
    token, plain = ApiToken.create_token(
        user_id=admin_user.id, name="Admin Token", scopes="read:time_entries,write:time_entries"
    )
    db.session.add(token)
    db.session.commit()

    client = app.test_client()
    start_time = datetime.utcnow() - timedelta(hours=2)
    end_time = datetime.utcnow() - timedelta(hours=1)
    response = client.post(
        "/api/v1/time-entries",
        headers={"Authorization": f"Bearer {plain}"},
        json={
            "user_id": user.id,
            "project_id": project.id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "notes": "API booked for other",
            "billable": True,
        },
        content_type="application/json",
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["time_entry"]["user_id"] == user.id


@pytest.mark.api
def test_api_non_admin_cannot_create_for_other_user(app, user, admin_user, project):
    """API v1: non-admin token gets 403 when requesting another user_id."""
    token, plain = ApiToken.create_token(
        user_id=user.id, name="User Token", scopes="read:time_entries,write:time_entries"
    )
    db.session.add(token)
    db.session.commit()

    client = app.test_client()
    start_time = datetime.utcnow() - timedelta(hours=3)
    end_time = datetime.utcnow() - timedelta(hours=2)
    response = client.post(
        "/api/v1/time-entries",
        headers={"Authorization": f"Bearer {plain}"},
        json={
            "user_id": admin_user.id,
            "project_id": project.id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "notes": "API forge attempt",
            "billable": True,
        },
        content_type="application/json",
    )
    assert response.status_code == 403
    assert TimeEntry.query.filter_by(notes="API forge attempt").first() is None
