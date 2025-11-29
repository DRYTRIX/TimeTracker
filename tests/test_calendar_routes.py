"""
Test suite for calendar routes and endpoints.
Tests calendar views, event CRUD operations, and API endpoints.
"""

import pytest
import json
from datetime import datetime, timedelta
from app.models import CalendarEvent, Task
from app import db


# ============================================================================
# Calendar View Routes
# ============================================================================


@pytest.mark.smoke
@pytest.mark.routes
def test_calendar_view_accessible(authenticated_client):
    """Test that calendar view is accessible for authenticated users."""
    response = authenticated_client.get("/calendar")
    assert response.status_code == 200
    assert b"Calendar" in response.data or b"calendar" in response.data


@pytest.mark.routes
def test_calendar_view_requires_authentication(client):
    """Test that calendar view requires authentication."""
    response = client.get("/calendar", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.location or "login" in response.location.lower()


@pytest.mark.routes
def test_calendar_day_view(authenticated_client):
    """Test calendar day view."""
    response = authenticated_client.get("/calendar?view=day")
    assert response.status_code == 200


@pytest.mark.routes
def test_calendar_week_view(authenticated_client):
    """Test calendar week view."""
    response = authenticated_client.get("/calendar?view=week")
    assert response.status_code == 200


@pytest.mark.routes
def test_calendar_month_view(authenticated_client):
    """Test calendar month view."""
    response = authenticated_client.get("/calendar?view=month")
    assert response.status_code == 200


@pytest.mark.routes
def test_calendar_with_date_parameter(authenticated_client):
    """Test calendar view with specific date."""
    test_date = "2025-01-15"
    response = authenticated_client.get(f"/calendar?date={test_date}")
    assert response.status_code == 200


# ============================================================================
# Calendar Event API Endpoints
# ============================================================================


@pytest.mark.api
@pytest.mark.routes
def test_get_calendar_events_api(authenticated_client, user, app):
    """Test getting calendar events via API."""
    with app.app_context():
        # Create test event
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=2)
        event = CalendarEvent(
            user_id=user.id, title="Test Event", start_time=start_time, end_time=end_time, event_type="meeting"
        )
        db.session.add(event)
        db.session.commit()

        # Query events
        start_str = (start_time - timedelta(days=1)).isoformat()
        end_str = (end_time + timedelta(days=1)).isoformat()
        response = authenticated_client.get(f"/api/calendar/events?start={start_str}&end={end_str}")

        assert response.status_code == 200
        data = response.get_json()
        assert "events" in data
        assert len(data["events"]) > 0
        assert data["events"][0]["title"] == "Test Event"


@pytest.mark.api
@pytest.mark.routes
def test_get_calendar_events_missing_dates(authenticated_client):
    """Test getting events without required date parameters."""
    response = authenticated_client.get("/api/calendar/events")
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data


@pytest.mark.api
@pytest.mark.routes
def test_create_calendar_event_api(authenticated_client, app):
    """Test creating a calendar event via API."""
    with app.app_context():
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)

        event_data = {
            "title": "New Meeting",
            "description": "Team sync",
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "allDay": False,
            "location": "Office",
            "eventType": "meeting",
        }

        response = authenticated_client.post(
            "/api/calendar/events", data=json.dumps(event_data), content_type="application/json"
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert "event" in data
        assert data["event"]["title"] == "New Meeting"

        # Verify event was created in database
        event = CalendarEvent.query.filter_by(title="New Meeting").first()
        assert event is not None
        assert event.description == "Team sync"


@pytest.mark.api
@pytest.mark.routes
def test_create_calendar_event_missing_required_fields(authenticated_client):
    """Test creating event without required fields."""
    event_data = {"description": "Missing title"}

    response = authenticated_client.post(
        "/api/calendar/events", data=json.dumps(event_data), content_type="application/json"
    )

    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data


@pytest.mark.api
@pytest.mark.routes
def test_get_single_event_api(authenticated_client, user, app):
    """Test getting a single calendar event."""
    with app.app_context():
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        event = CalendarEvent(
            user_id=user.id, title="Test Event", start_time=start_time, end_time=end_time, event_type="event"
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id

        response = authenticated_client.get(f"/api/calendar/events/{event_id}")

        assert response.status_code == 200
        data = response.get_json()
        assert data["title"] == "Test Event"


@pytest.mark.api
@pytest.mark.routes
def test_get_nonexistent_event(authenticated_client):
    """Test getting a non-existent event."""
    response = authenticated_client.get("/api/calendar/events/99999")
    assert response.status_code == 404


@pytest.mark.api
@pytest.mark.routes
def test_update_calendar_event_api(authenticated_client, user, app):
    """Test updating a calendar event via API."""
    with app.app_context():
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        event = CalendarEvent(
            user_id=user.id, title="Original Title", start_time=start_time, end_time=end_time, event_type="event"
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id

        update_data = {"title": "Updated Title", "description": "Updated description"}

        response = authenticated_client.put(
            f"/api/calendar/events/{event_id}", data=json.dumps(update_data), content_type="application/json"
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["event"]["title"] == "Updated Title"

        # Verify in database
        db.session.refresh(event)
        assert event.title == "Updated Title"
        assert event.description == "Updated description"


@pytest.mark.api
@pytest.mark.routes
def test_update_event_permission_denied(authenticated_client, admin_user, app):
    """Test that users cannot update other users' events."""
    with app.app_context():
        # Create event for admin user
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        event = CalendarEvent(
            user_id=admin_user.id, title="Admin Event", start_time=start_time, end_time=end_time, event_type="event"
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id

        # Try to update as regular user
        update_data = {"title": "Hacked Title"}
        response = authenticated_client.put(
            f"/api/calendar/events/{event_id}", data=json.dumps(update_data), content_type="application/json"
        )

        assert response.status_code == 403


@pytest.mark.api
@pytest.mark.routes
def test_delete_calendar_event_api(authenticated_client, user, app):
    """Test deleting a calendar event via API."""
    with app.app_context():
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        event = CalendarEvent(
            user_id=user.id, title="Event to Delete", start_time=start_time, end_time=end_time, event_type="event"
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id

        response = authenticated_client.delete(f"/api/calendar/events/{event_id}")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

        # Verify deletion in database
        deleted_event = CalendarEvent.query.get(event_id)
        assert deleted_event is None


@pytest.mark.api
@pytest.mark.routes
def test_delete_event_permission_denied(authenticated_client, admin_user, app):
    """Test that users cannot delete other users' events."""
    with app.app_context():
        # Create event for admin user
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        event = CalendarEvent(
            user_id=admin_user.id, title="Admin Event", start_time=start_time, end_time=end_time, event_type="event"
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id

        # Try to delete as regular user
        response = authenticated_client.delete(f"/api/calendar/events/{event_id}")

        assert response.status_code == 403


@pytest.mark.api
@pytest.mark.routes
def test_move_calendar_event_api(authenticated_client, user, app):
    """Test moving a calendar event (drag and drop)."""
    with app.app_context():
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        event = CalendarEvent(
            user_id=user.id, title="Event to Move", start_time=start_time, end_time=end_time, event_type="event"
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id

        new_start = start_time + timedelta(days=1)
        new_end = end_time + timedelta(days=1)

        move_data = {"start": new_start.isoformat(), "end": new_end.isoformat()}

        response = authenticated_client.post(
            f"/api/calendar/events/{event_id}/move", data=json.dumps(move_data), content_type="application/json"
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

        # Verify in database
        db.session.refresh(event)
        assert event.start_time.date() == new_start.date()


@pytest.mark.api
@pytest.mark.routes
def test_resize_calendar_event_api(authenticated_client, user, app):
    """Test resizing a calendar event."""
    with app.app_context():
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        event = CalendarEvent(
            user_id=user.id, title="Event to Resize", start_time=start_time, end_time=end_time, event_type="event"
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id

        new_end = end_time + timedelta(hours=1)

        resize_data = {"end": new_end.isoformat()}

        response = authenticated_client.post(
            f"/api/calendar/events/{event_id}/resize", data=json.dumps(resize_data), content_type="application/json"
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

        # Verify duration changed
        db.session.refresh(event)
        assert event.duration_hours() == 2.0


# ============================================================================
# Calendar Event Form Routes
# ============================================================================


@pytest.mark.routes
def test_new_event_form_accessible(authenticated_client):
    """Test that new event form is accessible."""
    response = authenticated_client.get("/calendar/event/new")
    assert response.status_code == 200
    assert b"New Event" in response.data or b"new event" in response.data.lower()


@pytest.mark.routes
def test_edit_event_form_accessible(authenticated_client, user, app):
    """Test that edit event form is accessible."""
    with app.app_context():
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        event = CalendarEvent(
            user_id=user.id, title="Test Event", start_time=start_time, end_time=end_time, event_type="event"
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id

        response = authenticated_client.get(f"/calendar/event/{event_id}/edit")
        assert response.status_code == 200
        assert b"Edit" in response.data or b"edit" in response.data.lower()


@pytest.mark.routes
def test_edit_event_form_permission_denied(authenticated_client, admin_user, app):
    """Test that users cannot access edit form for other users' events."""
    with app.app_context():
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        event = CalendarEvent(
            user_id=admin_user.id, title="Admin Event", start_time=start_time, end_time=end_time, event_type="event"
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id

        response = authenticated_client.get(f"/calendar/event/{event_id}/edit", follow_redirects=False)
        assert response.status_code == 302  # Redirected


@pytest.mark.routes
def test_view_event_detail(authenticated_client, user, app):
    """Test viewing event detail page."""
    with app.app_context():
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        event = CalendarEvent(
            user_id=user.id,
            title="Test Event",
            start_time=start_time,
            end_time=end_time,
            description="Test description",
            location="Test location",
            event_type="meeting",
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id

        response = authenticated_client.get(f"/calendar/event/{event_id}")
        assert response.status_code == 200
        assert b"Test Event" in response.data
        assert b"Test description" in response.data


# ============================================================================
# Calendar Integration Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.routes
def test_calendar_shows_tasks(authenticated_client, user, project, app):
    """Test that calendar includes tasks with due dates."""
    with app.app_context():
        # Create task with due date
        task = Task(
            project_id=project.id,
            name="Task with due date",
            created_by=user.id,
            assigned_to=user.id,
            due_date=datetime.now().date() + timedelta(days=3),
            status="todo",
        )
        db.session.add(task)
        db.session.commit()

        # Query calendar events API
        start_str = datetime.now().isoformat()
        end_str = (datetime.now() + timedelta(days=7)).isoformat()
        response = authenticated_client.get(f"/api/calendar/events?start={start_str}&end={end_str}&include_tasks=true")

        assert response.status_code == 200
        data = response.get_json()
        # The API combines everything into the 'events' array and provides a 'summary'
        assert "events" in data
        assert "summary" in data
        assert data["summary"]["tasks"] > 0
        # Check that there's at least one task in the events array
        task_events = [e for e in data["events"] if e.get("extendedProps", {}).get("item_type") == "task"]
        assert len(task_events) > 0


@pytest.mark.integration
@pytest.mark.routes
def test_calendar_with_project_filter(authenticated_client, user, project, app):
    """Test creating event with project association."""
    with app.app_context():
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)

        event_data = {
            "title": "Project Meeting",
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "projectId": project.id,
            "eventType": "meeting",
        }

        response = authenticated_client.post(
            "/api/calendar/events", data=json.dumps(event_data), content_type="application/json"
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["event"]["projectId"] == project.id


@pytest.mark.smoke
@pytest.mark.routes
def test_calendar_event_creation_workflow(authenticated_client, user, app):
    """Test complete workflow of creating and viewing an event."""
    with app.app_context():
        # Create event
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=2)

        event_data = {
            "title": "Complete Workflow Test",
            "description": "Testing full workflow",
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "location": "Test Location",
            "eventType": "meeting",
            "color": "#3b82f6",
            "reminderMinutes": 30,
        }

        # Create via API
        response = authenticated_client.post(
            "/api/calendar/events", data=json.dumps(event_data), content_type="application/json"
        )
        assert response.status_code == 201
        event_id = response.get_json()["event"]["id"]

        # Retrieve via API
        response = authenticated_client.get(f"/api/calendar/events/{event_id}")
        assert response.status_code == 200
        event = response.get_json()
        assert event["title"] == "Complete Workflow Test"
        assert event["reminderMinutes"] == 30

        # View detail page
        response = authenticated_client.get(f"/calendar/event/{event_id}")
        assert response.status_code == 200
        assert b"Complete Workflow Test" in response.data
