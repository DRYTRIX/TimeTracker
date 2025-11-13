"""
Test suite for CalendarEvent model.
Tests model creation, relationships, properties, and business logic.
"""

import pytest
from datetime import datetime, timedelta
from app.models import CalendarEvent, User, Project, Task, Client, TimeEntry
from app import db


# ============================================================================
# CalendarEvent Model Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.models
@pytest.mark.smoke
def test_calendar_event_creation(app, user, project):
    """Test basic calendar event creation."""
    import os
    with app.app_context():
        # Ensure Settings exists and is loaded into the session before creating event
        # This prevents Settings.get_settings() from being called during flush
        from app.models import Settings
        
        # Ensure Settings exists - try get_settings() first (it should find existing Settings)
        # If it tries to commit, that's okay since we're not in a flush yet
        try:
            settings = Settings.get_settings()
            # Settings should now be in the session
        except Exception:
            # If get_settings() failed, ensure Settings exists using direct query
            settings = db.session.query(Settings).first()
            if not settings:
                settings = Settings()
                db.session.add(settings)
                db.session.commit()
        
        # Ensure Settings is definitely found by Settings.query (used by get_settings())
        # by refreshing it into the session
        db.session.refresh(settings)
        
        # Temporarily set TZ environment variable as a fallback
        # This ensures get_app_timezone() has a fallback if Settings.get_settings() fails
        old_tz = os.environ.get('TZ')
        os.environ['TZ'] = 'Europe/Rome'  # Set a default timezone
        
        try:
            start_time = datetime.now()
            end_time = start_time + timedelta(hours=2)
            
            # Store user.id to avoid accessing user object after potential cleanup
            user_id = user.id
            
            event = CalendarEvent(
                user_id=user_id,
                title="Team Meeting",
                start_time=start_time,
                end_time=end_time,
                description="Weekly team sync",
                location="Conference Room A",
                event_type="meeting"
            )
            db.session.add(event)
            # Flush first to assign PK, then store ID before commit to avoid reloads
            db.session.flush()
            event_id = event.id
            db.session.commit()
            assert event_id is not None, "Event should have an ID after commit"
            
            # Verify properties on the event object immediately after commit
            assert event.title == "Team Meeting"
            assert event.user_id == user_id
            assert event.start_time == start_time
            assert event.end_time == end_time
            assert event.description == "Weekly team sync"
            assert event.location == "Conference Room A"
            assert event.event_type == "meeting"
            assert event.all_day is False
            assert event.is_private is False
            assert event.is_recurring is False
            assert event.created_at is not None
            assert event.updated_at is not None
            
            # Verify persistence using a direct SQL query with a fresh connection
            # This avoids session state and cascade delete issues
            from sqlalchemy import text
            with db.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT id, title, user_id, event_type, description, location FROM calendar_events WHERE id = :event_id"),
                    {"event_id": event_id}
                ).first()
                assert result is not None, f"Event should exist in database (ID: {event_id})"
                assert result[1] == "Team Meeting"  # title
                assert result[2] == user_id  # user_id
                assert result[3] == "meeting"  # event_type
                assert result[4] == "Weekly team sync"  # description
                assert result[5] == "Conference Room A"  # location
        finally:
            # Restore original TZ environment variable
            if old_tz is not None:
                os.environ['TZ'] = old_tz
            elif 'TZ' in os.environ:
                del os.environ['TZ']


@pytest.mark.unit
@pytest.mark.models
def test_calendar_event_all_day(app, user):
    """Test all-day calendar event."""
    with app.app_context():
        start_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time.replace(hour=23, minute=59, second=59)
        
        event = CalendarEvent(
            user_id=user.id,
            title="Holiday",
            start_time=start_time,
            end_time=end_time,
            all_day=True,
            event_type="event"
        )
        db.session.add(event)
        db.session.commit()
        
        assert event.all_day is True


@pytest.mark.unit
@pytest.mark.models
def test_calendar_event_with_project(app, user, project):
    """Test calendar event associated with a project."""
    with app.app_context():
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        
        event = CalendarEvent(
            user_id=user.id,
            title="Project Review",
            start_time=start_time,
            end_time=end_time,
            project_id=project.id,
            event_type="meeting"
        )
        db.session.add(event)
        db.session.commit()
        
        db.session.refresh(event)
        assert event.project is not None
        assert event.project.id == project.id
        assert event.project.name == project.name


@pytest.mark.unit
@pytest.mark.models
def test_calendar_event_with_task(app, user, project):
    """Test calendar event associated with a task."""
    with app.app_context():
        # Create a task
        task = Task(
            project_id=project.id,
            name="Complete documentation",
            created_by=user.id,
            assigned_to=user.id
        )
        db.session.add(task)
        db.session.commit()
        
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=3)
        
        event = CalendarEvent(
            user_id=user.id,
            title="Work on documentation",
            start_time=start_time,
            end_time=end_time,
            task_id=task.id,
            event_type="deadline"
        )
        db.session.add(event)
        db.session.commit()
        
        db.session.refresh(event)
        assert event.task is not None
        assert event.task.id == task.id
        assert event.task.name == "Complete documentation"


@pytest.mark.unit
@pytest.mark.models
def test_calendar_event_with_client(app, user, test_client):
    """Test calendar event associated with a client."""
    with app.app_context():
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        
        event = CalendarEvent(
            user_id=user.id,
            title="Client Meeting",
            start_time=start_time,
            end_time=end_time,
            client_id=test_client.id,
            event_type="appointment"
        )
        db.session.add(event)
        db.session.commit()
        
        db.session.refresh(event)
        assert event.client is not None
        assert event.client.id == test_client.id


@pytest.mark.unit
@pytest.mark.models
def test_calendar_event_recurring(app, user):
    """Test recurring calendar event."""
    with app.app_context():
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        recurrence_end = start_time + timedelta(days=90)
        
        event = CalendarEvent(
            user_id=user.id,
            title="Weekly Standup",
            start_time=start_time,
            end_time=end_time,
            is_recurring=True,
            recurrence_rule="FREQ=WEEKLY;BYDAY=MO,WE,FR",
            recurrence_end_date=recurrence_end,
            event_type="meeting"
        )
        db.session.add(event)
        db.session.commit()
        
        assert event.is_recurring is True
        assert event.recurrence_rule == "FREQ=WEEKLY;BYDAY=MO,WE,FR"
        assert event.recurrence_end_date == recurrence_end


@pytest.mark.unit
@pytest.mark.models
def test_calendar_event_with_reminder(app, user):
    """Test calendar event with reminder."""
    with app.app_context():
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        
        event = CalendarEvent(
            user_id=user.id,
            title="Important Meeting",
            start_time=start_time,
            end_time=end_time,
            reminder_minutes=30,
            event_type="meeting"
        )
        db.session.add(event)
        db.session.commit()
        
        assert event.reminder_minutes == 30


@pytest.mark.unit
@pytest.mark.models
def test_calendar_event_with_color(app, user):
    """Test calendar event with custom color."""
    with app.app_context():
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        
        event = CalendarEvent(
            user_id=user.id,
            title="Colored Event",
            start_time=start_time,
            end_time=end_time,
            color="#FF5733",
            event_type="event"
        )
        db.session.add(event)
        db.session.commit()
        
        assert event.color == "#FF5733"


@pytest.mark.unit
@pytest.mark.models
def test_calendar_event_private(app, user):
    """Test private calendar event."""
    with app.app_context():
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        
        event = CalendarEvent(
            user_id=user.id,
            title="Private Event",
            start_time=start_time,
            end_time=end_time,
            is_private=True,
            event_type="event"
        )
        db.session.add(event)
        db.session.commit()
        
        assert event.is_private is True


@pytest.mark.unit
@pytest.mark.models
def test_calendar_event_duration_hours(app, user):
    """Test calendar event duration calculation."""
    with app.app_context():
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=2, minutes=30)
        
        event = CalendarEvent(
            user_id=user.id,
            title="Test Event",
            start_time=start_time,
            end_time=end_time,
            event_type="event"
        )
        db.session.add(event)
        db.session.commit()
        
        assert event.duration_hours() == 2.5


@pytest.mark.unit
@pytest.mark.models
def test_calendar_event_to_dict(app, user, project):
    """Test calendar event serialization to dictionary."""
    with app.app_context():
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        
        event = CalendarEvent(
            user_id=user.id,
            title="Test Event",
            start_time=start_time,
            end_time=end_time,
            description="Test description",
            location="Office",
            event_type="meeting",
            project_id=project.id,
            all_day=False,
            is_private=False,
            color="#3b82f6",
            reminder_minutes=15
        )
        db.session.add(event)
        db.session.commit()
        
        event_dict = event.to_dict()
        
        assert 'id' in event_dict
        assert 'title' in event_dict
        assert 'description' in event_dict
        assert 'start' in event_dict
        assert 'end' in event_dict
        assert 'allDay' in event_dict
        assert 'location' in event_dict
        assert 'eventType' in event_dict
        assert 'projectId' in event_dict
        assert 'color' in event_dict
        assert 'isPrivate' in event_dict
        assert 'reminderMinutes' in event_dict
        
        assert event_dict['title'] == "Test Event"
        assert event_dict['description'] == "Test description"
        assert event_dict['location'] == "Office"
        assert event_dict['eventType'] == "meeting"
        assert event_dict['projectId'] == project.id
        assert event_dict['color'] == "#3b82f6"
        assert event_dict['reminderMinutes'] == 15


@pytest.mark.unit
@pytest.mark.models
def test_calendar_event_user_relationship(app, user):
    """Test calendar event user relationship."""
    with app.app_context():
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        
        event = CalendarEvent(
            user_id=user.id,
            title="Test Event",
            start_time=start_time,
            end_time=end_time,
            event_type="event"
        )
        db.session.add(event)
        db.session.flush()
        ev_id = event.id
        db.session.commit()
        persisted = CalendarEvent.query.get(ev_id)
        assert persisted is not None
        assert persisted.user is not None
        assert persisted.user.id == user.id
        assert persisted.user.username == user.username


@pytest.mark.unit
@pytest.mark.models
def test_calendar_event_parent_child_relationship(app, user):
    """Test recurring calendar event parent-child relationship."""
    with app.app_context():
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        
        # Create parent event
        parent_event = CalendarEvent(
            user_id=user.id,
            title="Recurring Meeting",
            start_time=start_time,
            end_time=end_time,
            is_recurring=True,
            recurrence_rule="FREQ=WEEKLY",
            event_type="meeting"
        )
        db.session.add(parent_event)
        db.session.commit()
        
        # Create child event (instance of recurring event)
        child_start = start_time + timedelta(days=7)
        child_end = child_start + timedelta(hours=1)
        child_event = CalendarEvent(
            user_id=user.id,
            title="Recurring Meeting",
            start_time=child_start,
            end_time=child_end,
            parent_event_id=parent_event.id,
            event_type="meeting"
        )
        db.session.add(child_event)
        db.session.commit()
        
        db.session.refresh(parent_event)
        db.session.refresh(child_event)
        
        assert child_event.parent_event is not None
        assert child_event.parent_event.id == parent_event.id
        assert parent_event.child_events.count() == 1


@pytest.mark.unit
@pytest.mark.models
def test_get_events_in_range(app, user):
    """Test getting events in a date range."""
    with app.app_context():
        # Create events
        now = datetime.now()
        
        # Event within range
        event1 = CalendarEvent(
            user_id=user.id,
            title="Event 1",
            start_time=now,
            end_time=now + timedelta(hours=1),
            event_type="event"
        )
        
        # Event outside range
        event2 = CalendarEvent(
            user_id=user.id,
            title="Event 2",
            start_time=now + timedelta(days=30),
            end_time=now + timedelta(days=30, hours=1),
            event_type="event"
        )
        
        db.session.add_all([event1, event2])
        db.session.commit()
        
        # Get events in range
        start_date = now - timedelta(days=1)
        end_date = now + timedelta(days=7)
        result = CalendarEvent.get_events_in_range(
            user_id=user.id,
            start_date=start_date,
            end_date=end_date,
            include_tasks=False,
            include_time_entries=False
        )
        
        assert len(result['events']) == 1
        assert result['events'][0]['title'] == "Event 1"


@pytest.mark.unit
@pytest.mark.models
def test_get_events_in_range_with_tasks(app, user, project):
    """Test getting events with tasks in date range."""
    with app.app_context():
        # Create event
        now = datetime.now()
        event = CalendarEvent(
            user_id=user.id,
            title="Event",
            start_time=now,
            end_time=now + timedelta(hours=1),
            event_type="event"
        )
        db.session.add(event)
        
        # Create task with due date
        task = Task(
            project_id=project.id,
            name="Task with due date",
            created_by=user.id,
            assigned_to=user.id,
            due_date=now.date() + timedelta(days=3),
            status='todo'
        )
        db.session.add(task)
        db.session.commit()
        
        # Get events including tasks
        start_date = now - timedelta(days=1)
        end_date = now + timedelta(days=7)
        result = CalendarEvent.get_events_in_range(
            user_id=user.id,
            start_date=start_date,
            end_date=end_date,
            include_tasks=True,
            include_time_entries=False
        )
        
        assert len(result['events']) == 1
        assert len(result['tasks']) == 1
        assert result['tasks'][0]['title'] == "Task with due date"


@pytest.mark.unit
@pytest.mark.models
def test_get_events_in_range_with_time_entries(app, user, project):
    """Test getting events with time entries in date range."""
    with app.app_context():
        # Create event
        now = datetime.now()
        event = CalendarEvent(
            user_id=user.id,
            title="Event",
            start_time=now,
            end_time=now + timedelta(hours=1),
            event_type="event"
        )
        db.session.add(event)
        
        # Create time entry
        time_entry = TimeEntry(
            user_id=user.id,
            project_id=project.id,
            start_time=now + timedelta(hours=2),
            end_time=now + timedelta(hours=4),
            notes="Working on feature"
        )
        db.session.add(time_entry)
        db.session.commit()
        
        # Get events including time entries
        start_date = now - timedelta(days=1)
        end_date = now + timedelta(days=1)
        result = CalendarEvent.get_events_in_range(
            user_id=user.id,
            start_date=start_date,
            end_date=end_date,
            include_tasks=False,
            include_time_entries=True
        )
        
        assert len(result['events']) == 1
        assert len(result['time_entries']) == 1


@pytest.mark.unit
@pytest.mark.models
def test_calendar_event_repr(app, user):
    """Test calendar event string representation."""
    with app.app_context():
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        
        event = CalendarEvent(
            user_id=user.id,
            title="Test Event",
            start_time=start_time,
            end_time=end_time,
            event_type="event"
        )
        db.session.add(event)
        db.session.commit()
        
        repr_str = repr(event)
        assert 'CalendarEvent' in repr_str
        assert 'Test Event' in repr_str


@pytest.mark.unit
@pytest.mark.models
def test_calendar_event_cascade_delete_with_user(app, user):
    """Test that events are deleted when user is deleted."""
    with app.app_context():
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        
        # Re-query the user to attach to current session
        from app.models.user import User
        user_in_session = User.query.get(user.id)
        
        event = CalendarEvent(
            user_id=user_in_session.id,
            title="Test Event",
            start_time=start_time,
            end_time=end_time,
            event_type="event"
        )
        db.session.add(event)
        db.session.commit()
        
        event_id = event.id
        
        # Delete user
        db.session.delete(user_in_session)
        db.session.commit()
        
        # Event should be deleted
        deleted_event = CalendarEvent.query.get(event_id)
        assert deleted_event is None


@pytest.mark.unit
@pytest.mark.models
def test_calendar_event_cascade_delete_with_parent(app, user):
    """Test that child events are deleted when parent is deleted."""
    with app.app_context():
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        
        # Create parent event
        parent_event = CalendarEvent(
            user_id=user.id,
            title="Parent Event",
            start_time=start_time,
            end_time=end_time,
            is_recurring=True,
            event_type="meeting"
        )
        db.session.add(parent_event)
        db.session.commit()
        
        # Create child event
        child_start = start_time + timedelta(days=7)
        child_end = child_start + timedelta(hours=1)
        child_event = CalendarEvent(
            user_id=user.id,
            title="Child Event",
            start_time=child_start,
            end_time=child_end,
            parent_event_id=parent_event.id,
            event_type="meeting"
        )
        db.session.add(child_event)
        db.session.commit()
        
        child_id = child_event.id
        
        # Delete parent
        db.session.delete(parent_event)
        db.session.commit()
        
        # Child should be deleted
        deleted_child = CalendarEvent.query.get(child_id)
        assert deleted_child is None


@pytest.mark.unit
@pytest.mark.models
def test_calendar_event_different_types(app, user):
    """Test calendar events with different types."""
    with app.app_context():
        now = datetime.now()
        event_types = ['event', 'meeting', 'appointment', 'reminder', 'deadline']
        
        events = []
        for event_type in event_types:
            event = CalendarEvent(
                user_id=user.id,
                title=f"Test {event_type}",
                start_time=now,
                end_time=now + timedelta(hours=1),
                event_type=event_type
            )
            events.append(event)
        
        db.session.add_all(events)
        db.session.commit()
        
        for idx, event_type in enumerate(event_types):
            assert events[idx].event_type == event_type


@pytest.mark.unit
@pytest.mark.models
def test_calendar_event_user_has_events_relationship(app, user):
    """Test that user has calendar_events relationship."""
    with app.app_context():
        now = datetime.now()
        
        # Re-query the user to attach to current session
        from app.models.user import User
        user_in_session = User.query.get(user.id)
        
        event1 = CalendarEvent(
            user_id=user_in_session.id,
            title="Event 1",
            start_time=now,
            end_time=now + timedelta(hours=1),
            event_type="event"
        )
        event2 = CalendarEvent(
            user_id=user_in_session.id,
            title="Event 2",
            start_time=now + timedelta(days=1),
            end_time=now + timedelta(days=1, hours=1),
            event_type="meeting"
        )
        db.session.add_all([event1, event2])
        db.session.commit()
        
        db.session.refresh(user_in_session)
        assert user_in_session.calendar_events.count() == 2

