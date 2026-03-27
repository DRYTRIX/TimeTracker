"""Issue #572: users with edit_own_time_entries can edit schedule fields on own entries."""

from datetime import datetime

import pytest

from app import db
from app.models import Permission, Role, TimeEntry


def _ensure_edit_own_permission(user):
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
    if role not in user.roles:
        user.add_role(role)
    db.session.commit()
    db.session.refresh(user)


@pytest.mark.integration
@pytest.mark.routes
def test_edit_timer_page_shows_schedule_fields_with_edit_own_permission(app, authenticated_client, user, project):
    """GET /timer/edit shows date/time inputs when user has edit_own_time_entries."""
    with app.app_context():
        _ensure_edit_own_permission(user)
        start = datetime(2020, 6, 1, 9, 0, 0)
        end = datetime(2020, 6, 1, 11, 0, 0)
        entry = TimeEntry(
            user_id=user.id,
            project_id=project.id,
            start_time=start,
            end_time=end,
            source="manual",
        )
        db.session.add(entry)
        db.session.commit()
        eid = entry.id

    response = authenticated_client.get(f"/timer/edit/{eid}")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'name="start_date"' in html
    assert 'id="start_date"' in html


@pytest.mark.integration
@pytest.mark.routes
def test_edit_timer_post_updates_times_with_edit_own_permission(app, authenticated_client, user, project):
    """POST /timer/edit applies new start/end when user has edit_own_time_entries."""
    with app.app_context():
        _ensure_edit_own_permission(user)
        start = datetime(2020, 6, 1, 9, 0, 0)
        end = datetime(2020, 6, 1, 11, 0, 0)
        entry = TimeEntry(
            user_id=user.id,
            project_id=project.id,
            start_time=start,
            end_time=end,
            source="manual",
        )
        db.session.add(entry)
        db.session.commit()
        eid = entry.id

    response = authenticated_client.post(
        f"/timer/edit/{eid}",
        data={
            "project_id": project.id,
            "task_id": "",
            "start_date": "2020-06-01",
            "start_time": "08:00",
            "end_date": "2020-06-01",
            "end_time": "12:00",
            "break_time": "",
            "notes": "",
            "tags": "",
            "billable": "on",
            "paid": "",
            "invoice_number": "",
            "reason": "test correction",
        },
        follow_redirects=False,
    )
    assert response.status_code in (302, 303)

    with app.app_context():
        updated = TimeEntry.query.get(eid)
        # 08:00–12:00 = 4h (timezone parsing may shift wall-clock hours)
        assert (updated.end_time - updated.start_time).total_seconds() == 4 * 3600


@pytest.mark.integration
@pytest.mark.routes
def test_api_entry_put_updates_times_with_edit_own_permission(app, authenticated_client, user, project):
    """PUT /api/entry/<id> accepts start/end for own entry with edit_own_time_entries."""
    with app.app_context():
        _ensure_edit_own_permission(user)
        start = datetime(2020, 6, 2, 9, 0, 0)
        end = datetime(2020, 6, 2, 10, 0, 0)
        entry = TimeEntry(
            user_id=user.id,
            project_id=project.id,
            start_time=start,
            end_time=end,
            source="manual",
        )
        db.session.add(entry)
        db.session.commit()
        eid = entry.id

    response = authenticated_client.put(
        f"/api/entry/{eid}",
        json={
            "start_time": "2020-06-02T08:30",
            "end_time": "2020-06-02T11:00",
        },
        content_type="application/json",
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload.get("success") is True

    with app.app_context():
        updated = TimeEntry.query.get(eid)
        # 08:30–11:00 = 2.5h
        assert (updated.end_time - updated.start_time).total_seconds() == 2.5 * 3600
