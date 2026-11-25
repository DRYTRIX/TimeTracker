"""Tests for timer calendar snap interval wiring (GitHub #893)."""

from datetime import datetime, timedelta

import pytest

from app import db
from app.models import CalendarEvent, TimeEntry


@pytest.mark.routes
def test_timer_calendar_accessible(authenticated_client):
    """GET /timer/calendar returns 200 for authenticated users."""
    response = authenticated_client.get("/timer/calendar")
    assert response.status_code == 200
    assert b"calendarPrefs" in response.data


@pytest.mark.routes
def test_sidebar_calendar_includes_snap_minutes(authenticated_client, user, app):
    """GET /calendar (sidebar Calendar View) exposes snapMinutes for DnD."""
    with app.app_context():
        user.time_rounding_enabled = True
        user.time_rounding_minutes = 10
        db.session.commit()

    response = authenticated_client.get("/calendar?view=week")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "snapMinutes: 10" in html
    assert "timeEntryCreateModal" in html
    assert "calendar.js" in html


@pytest.mark.routes
def test_timer_calendar_requires_authentication(client):
    """GET /timer/calendar redirects unauthenticated users."""
    response = client.get("/timer/calendar")
    assert response.status_code in (302, 401)


@pytest.mark.routes
def test_timer_calendar_default_snap_minutes(authenticated_client, user, app):
    """When rounding is off / 1-minute, calendar uses 15-minute snap default."""
    with app.app_context():
        user.time_rounding_enabled = False
        user.time_rounding_minutes = 1
        db.session.commit()

    response = authenticated_client.get("/timer/calendar")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "snapMinutes: 15" in html


@pytest.mark.routes
def test_timer_calendar_snap_follows_user_rounding(authenticated_client, user, app):
    """When user rounding is 30 minutes, calendar snapMinutes is 30."""
    with app.app_context():
        user.time_rounding_enabled = True
        user.time_rounding_minutes = 30
        db.session.commit()

    response = authenticated_client.get("/timer/calendar")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "snapMinutes: 30" in html


@pytest.mark.api
@pytest.mark.routes
def test_calendar_events_feed_marks_planning_events_not_editable(authenticated_client, user, app):
    """Planning calendar events in the shared feed are not editable (timer DnD is time-entry only)."""
    with app.app_context():
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        event = CalendarEvent(
            user_id=user.id,
            title="Planning Meeting",
            start_time=start_time,
            end_time=end_time,
            event_type="meeting",
        )
        db.session.add(event)
        db.session.commit()

        start_str = (start_time - timedelta(days=1)).isoformat()
        end_str = (end_time + timedelta(days=1)).isoformat()
        response = authenticated_client.get(f"/api/calendar/events?start={start_str}&end={end_str}")

        assert response.status_code == 200
        data = response.get_json()
        planning = [
            e
            for e in data.get("events", [])
            if (e.get("extendedProps") or {}).get("item_type") == "event" or e.get("title") == "Planning Meeting"
        ]
        assert planning, "expected at least one planning calendar event in feed"
        for item in planning:
            assert item.get("editable") is False


@pytest.mark.api
@pytest.mark.routes
def test_api_entry_put_accepts_fullcalendar_iso_z(authenticated_client, user, project, app):
    """PUT /api/entry/<id> must accept FullCalendar toISOString() payloads (…Z), used by drag/resize."""
    with app.app_context():
        entry = TimeEntry(
            user_id=user.id,
            project_id=project.id,
            start_time=datetime(2020, 6, 2, 9, 0, 0),
            end_time=datetime(2020, 6, 2, 10, 0, 0),
            source="manual",
        )
        db.session.add(entry)
        db.session.commit()
        eid = entry.id

    response = authenticated_client.put(
        f"/api/entry/{eid}",
        json={
            "start_time": "2020-06-02T10:00:00.000Z",
            "end_time": "2020-06-02T11:30:00.000Z",
        },
        content_type="application/json",
    )
    assert response.status_code == 200, response.get_json()
    payload = response.get_json()
    assert payload.get("success") is True

    with app.app_context():
        updated = TimeEntry.query.get(eid)
        # Times must actually change (duration 1.5h); previously …Z was silently ignored.
        assert (updated.end_time - updated.start_time).total_seconds() == 1.5 * 3600


@pytest.mark.api
@pytest.mark.routes
def test_api_entry_put_rejects_unparseable_times(authenticated_client, user, project, app):
    """Invalid start_time from the calendar must 400 instead of silently succeeding."""
    with app.app_context():
        entry = TimeEntry(
            user_id=user.id,
            project_id=project.id,
            start_time=datetime(2020, 6, 2, 9, 0, 0),
            end_time=datetime(2020, 6, 2, 10, 0, 0),
            source="manual",
        )
        db.session.add(entry)
        db.session.commit()
        eid = entry.id

    response = authenticated_client.put(
        f"/api/entry/{eid}",
        json={"start_time": "not-a-datetime", "end_time": "2020-06-02T11:00"},
        content_type="application/json",
    )
    assert response.status_code == 400
