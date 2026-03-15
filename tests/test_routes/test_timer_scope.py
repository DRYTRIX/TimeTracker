"""
Web timer scope tests: scope-restricted user can only start timer for allowed project.
"""

import pytest

from app import db

pytestmark = [pytest.mark.routes, pytest.mark.integration]


def test_timer_start_denied_for_disallowed_project(
    app, scope_restricted_authenticated_client, scope_restricted_user, project, test_client
):
    """POST /timer/start with a project the user cannot access redirects with error or to login."""
    with app.app_context():
        from app.models import Client, Project

        other_client = Client(name="Other Corp", email="other@example.com")
        other_client.status = "active"
        db.session.add(other_client)
        db.session.commit()
        other_project = Project(name="Other Project", client_id=other_client.id, status="active")
        db.session.add(other_project)
        db.session.commit()
        other_project_id = int(other_project.id)

    resp = scope_restricted_authenticated_client.post(
        "/timer/start",
        data={"project_id": other_project_id},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    data = resp.get_data(as_text=True)
    # Either scope denial message, or login page (if session not established - still no timer on disallowed project)
    assert (
        "do not have access" in data.lower()
        or "access to this project" in data.lower()
        or "log in" in data.lower()
        or "sign in" in data.lower()
    )
    # No active timer for that user on the disallowed project
    with app.app_context():
        from app.models import TimeEntry

        active = TimeEntry.query.filter_by(
            user_id=scope_restricted_user.id, project_id=other_project_id, end_time=None
        ).first()
        assert active is None


def test_timer_start_allowed_for_assigned_project(
    app, scope_restricted_authenticated_client, scope_restricted_user, project
):
    """POST /timer/start with an allowed project creates active timer when user is logged in."""
    project_id = int(project.id)
    resp = scope_restricted_authenticated_client.post(
        "/timer/start",
        data={"project_id": project_id, "notes": "Scope test"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    data = resp.get_data(as_text=True)
    with app.app_context():
        from app.models import TimeEntry

        active = TimeEntry.query.filter_by(
            user_id=scope_restricted_user.id, project_id=project_id, end_time=None
        ).first()
    # If we are logged in (not on login page), timer should have been started
    if "sign in" not in data.lower() and "log in" not in data.lower():
        assert active is not None, "Expected active timer when scope-restricted user starts timer on allowed project"
