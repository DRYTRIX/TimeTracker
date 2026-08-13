"""Issue #728: client-only time entry edit must not force a project."""

from datetime import datetime

import pytest

from app import db
from app.models import Client, Permission, Role, TimeEntry, User


def _ensure_edit_own_permission(user_id):
    perm = Permission.query.filter_by(name="edit_own_time_entries").first()
    if not perm:
        perm = Permission(
            name="edit_own_time_entries",
            description="Edit own time entries",
            category="time_entries",
        )
        db.session.add(perm)
        db.session.flush()
    role = Role.query.filter_by(name="user").first()
    if not role:
        role = Role(name="user", description="User", is_system_role=True)
        db.session.add(role)
        db.session.flush()
    role.add_permission(perm)
    user = User.query.get(user_id)
    if role not in user.roles:
        user.add_role(role)
    db.session.commit()


@pytest.mark.integration
@pytest.mark.routes
def test_edit_client_only_entry_keeps_project_null(app, authenticated_client, user, project):
    """Saving a client-only entry without selecting a project must keep project_id NULL."""
    with app.app_context():
        _ensure_edit_own_permission(user.id)
        client = Client(name="Placeholder Client", email="placeholder@example.com", created_by=user.id)
        client.status = "active"
        db.session.add(client)
        db.session.flush()
        # Ensure at least one project exists (would previously be auto-selected)
        assert project.id is not None
        entry = TimeEntry(
            user_id=user.id,
            client_id=client.id,
            project_id=None,
            start_time=datetime(2026, 8, 12, 9, 0, 0),
            end_time=datetime(2026, 8, 12, 10, 0, 0),
            source="manual",
            notes="client only placeholder",
        )
        db.session.add(entry)
        db.session.commit()
        eid = entry.id
        cid = client.id

    # GET edit page: must offer empty project option and not auto-select first project
    response = authenticated_client.get(f"/timer/edit/{eid}")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "No project (client only)" in html
    assert 'data-searchable-select="project"' in html
    # Malformed bug was value="">selected>… — selected must be an attribute
    assert 'value="">selected>' not in html
    assert 'value="" selected>' in html or 'value=""\n selected>' in html or 'value="" selected >' in html

    # POST without project_id (empty) keeps client-only
    response = authenticated_client.post(
        f"/timer/edit/{eid}",
        data={
            "client_id": str(cid),
            "project_id": "",
            "task_id": "",
            "start_date": "2026-08-12",
            "start_time": "09:00",
            "end_date": "2026-08-12",
            "end_time": "10:00",
            "notes": "still client only",
            "billable": "on",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        refreshed = TimeEntry.query.get(eid)
        assert refreshed is not None
        assert refreshed.project_id is None
        assert refreshed.client_id == cid


@pytest.mark.unit
def test_searchable_select_source_present():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    content = (root / "app" / "static" / "searchable-select.js").read_text(encoding="utf-8")
    assert "data-searchable-select" in content
    assert "data-create" in content
    assert "Create client" in content or "openCreateModal" in content
