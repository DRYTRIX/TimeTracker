"""Tests for Settings.single_active_timer enforcement (DB) vs env defaults."""

import json
from datetime import datetime
from decimal import Decimal

import pytest

from app import db
from app.models import Project, Settings, TimeEntry

pytestmark = [pytest.mark.integration]


def _api_headers(plain_token: str) -> dict:
    return {"Authorization": f"Bearer {plain_token}", "Content-Type": "application/json"}


def _second_project(client_id: int, user_id: int) -> Project:
    p = Project(
        name="Second Timer Project",
        client_id=client_id,
        description="second",
        billable=True,
        hourly_rate=Decimal("80.00"),
        status="active",
        created_by=user_id,
    )
    db.session.add(p)
    db.session.flush()
    return p


def test_single_timer_enforced_when_setting_on(app, client, user, project, api_token):
    _, plain_token = api_token
    p2 = _second_project(project.client_id, user.id)
    db.session.commit()

    with app.app_context():
        settings = Settings.get_settings()
        settings.single_active_timer = True
        db.session.commit()

        running = TimeEntry(
            user_id=user.id,
            project_id=project.id,
            start_time=datetime.utcnow(),
            end_time=None,
            source="manual",
            billable=True,
        )
        db.session.add(running)
        db.session.commit()

    resp = client.post(
        "/api/v1/timer/start",
        json={"project_id": p2.id},
        headers=_api_headers(plain_token),
    )
    assert resp.status_code == 409
    data = json.loads(resp.data)
    assert data.get("success") is False
    assert data.get("error_code") == "timer_already_running"


def test_multiple_timers_allowed_when_setting_off(app, client, user, project, api_token):
    _, plain_token = api_token
    p2 = _second_project(project.client_id, user.id)
    db.session.commit()

    with app.app_context():
        settings = Settings.get_settings()
        settings.single_active_timer = False
        db.session.commit()

    r1 = client.post("/api/v1/timer/start", json={"project_id": project.id}, headers=_api_headers(plain_token))
    assert r1.status_code == 201

    r2 = client.post("/api/v1/timer/start", json={"project_id": p2.id}, headers=_api_headers(plain_token))
    assert r2.status_code == 201

    with app.app_context():
        active = TimeEntry.query.filter_by(user_id=user.id, end_time=None).all()
        assert len(active) == 2


def test_setting_read_from_db_not_env(app, client, user, project, api_token):
    """DB single_active_timer=False must allow a second timer even if env default is restrictive."""
    _, plain_token = api_token
    p2 = _second_project(project.client_id, user.id)
    db.session.commit()

    with app.app_context():
        settings = Settings.get_settings()
        settings.single_active_timer = False
        db.session.commit()

        running = TimeEntry(
            user_id=user.id,
            project_id=project.id,
            start_time=datetime.utcnow(),
            end_time=None,
            source="manual",
            billable=True,
        )
        db.session.add(running)
        db.session.commit()

    resp = client.post(
        "/api/v1/timer/start",
        json={"project_id": p2.id},
        headers=_api_headers(plain_token),
    )
    assert resp.status_code == 201
    with app.app_context():
        assert TimeEntry.query.filter_by(user_id=user.id, end_time=None).count() == 2


def test_both_web_and_api_routes_respect_setting(app, authenticated_client, user, project, api_token):
    _, plain_token = api_token
    p2 = _second_project(project.client_id, user.id)
    db.session.commit()

    with app.app_context():
        settings = Settings.get_settings()
        settings.single_active_timer = False
        db.session.commit()

    web_resp = authenticated_client.post(
        "/timer/start",
        data={"project_id": str(project.id)},
        follow_redirects=True,
    )
    assert web_resp.status_code == 200

    api_resp = authenticated_client.post(
        "/api/v1/timer/start",
        json={"project_id": p2.id},
        headers=_api_headers(plain_token),
    )
    assert api_resp.status_code == 201

    with app.app_context():
        active = TimeEntry.query.filter_by(user_id=user.id, end_time=None).all()
        assert len(active) == 2
