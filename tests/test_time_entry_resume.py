"""
Tests for time entry resume functionality.
"""

import pytest
from datetime import datetime, timedelta
from app import db
from app.models import User, Project, TimeEntry, Task
from app.models.time_entry import local_now
from factories import TimeEntryFactory


@pytest.mark.unit
@pytest.mark.models
def test_resume_timer_properties(app, user, project):
    """Test that resumed timer copies all properties correctly"""
    with app.app_context():
        # Create original time entry with all properties
        original_timer = TimeEntryFactory(
            user_id=user.id,
            project_id=project.id,
            start_time=local_now() - timedelta(hours=2),
            end_time=local_now() - timedelta(hours=1),
            notes="Working on feature X",
            tags="backend,api",
            billable=True,
            source="manual",
        )
        db.session.add(original_timer)
        db.session.commit()

        # Simulate resume by creating new timer with same properties
        resumed_timer = TimeEntryFactory(
            user_id=original_timer.user_id,
            project_id=original_timer.project_id,
            task_id=original_timer.task_id,
            start_time=local_now(),
            end_time=None,
            notes=original_timer.notes,
            tags=original_timer.tags,
            source="auto",
            billable=original_timer.billable,
        )
        db.session.add(resumed_timer)
        db.session.commit()

        # Verify all properties were copied
        assert resumed_timer.project_id == original_timer.project_id
        assert resumed_timer.task_id == original_timer.task_id
        assert resumed_timer.notes == original_timer.notes
        assert resumed_timer.tags == original_timer.tags
        assert resumed_timer.billable == original_timer.billable
        # Verify it's a new active timer
        assert resumed_timer.id != original_timer.id
        assert resumed_timer.end_time is None
        assert resumed_timer.is_active is True


@pytest.mark.unit
@pytest.mark.models
def test_resume_timer_with_task(app, user, project):
    """Test resuming a timer that has a task"""
    with app.app_context():
        # Create a task
        task = Task(
            name="Test Task", project_id=project.id, status="in_progress", priority="medium", created_by=user.id
        )
        db.session.add(task)
        db.session.commit()

        # Create original time entry with task
        original_timer = TimeEntryFactory(
            user_id=user.id,
            project_id=project.id,
            task_id=task.id,
            start_time=local_now() - timedelta(hours=2),
            end_time=local_now() - timedelta(hours=1),
            notes="Working on task",
            source="manual",
        )
        db.session.add(original_timer)
        db.session.commit()

        # Create resumed timer
        resumed_timer = TimeEntryFactory(
            user_id=original_timer.user_id,
            project_id=original_timer.project_id,
            task_id=original_timer.task_id,
            start_time=local_now(),
            end_time=None,
            notes=original_timer.notes,
            tags=original_timer.tags,
            source="auto",
            billable=original_timer.billable,
        )
        db.session.add(resumed_timer)
        db.session.commit()

        # Verify task was copied
        assert resumed_timer.task_id == original_timer.task_id
        assert resumed_timer.task.name == "Test Task"


@pytest.mark.unit
@pytest.mark.models
def test_resume_timer_without_task(app, user, project):
    """Test resuming a timer that has no task"""
    with app.app_context():
        # Create original time entry without task
        original_timer = TimeEntryFactory(
            user_id=user.id,
            project_id=project.id,
            task_id=None,
            start_time=local_now() - timedelta(hours=2),
            end_time=local_now() - timedelta(hours=1),
            notes="General project work",
            source="manual",
        )
        db.session.add(original_timer)
        db.session.commit()

        # Create resumed timer
        resumed_timer = TimeEntryFactory(
            user_id=original_timer.user_id,
            project_id=original_timer.project_id,
            task_id=original_timer.task_id,
            start_time=local_now(),
            end_time=None,
            notes=original_timer.notes,
            tags=original_timer.tags,
            source="auto",
            billable=original_timer.billable,
        )
        db.session.add(resumed_timer)
        db.session.commit()

        # Verify task_id is None
        assert resumed_timer.task_id is None


@pytest.mark.integration
@pytest.mark.routes
def test_resume_timer_route(client, user, project):
    """Test the resume timer route"""
    with client.application.app_context():
        # Set up authenticated session
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        # Create a completed time entry
        original_timer = TimeEntryFactory(
            user_id=user.id,
            project_id=project.id,
            start_time=local_now() - timedelta(hours=2),
            end_time=local_now() - timedelta(hours=1),
            notes="Original work",
            tags="test",
            billable=True,
            source="manual",
        )
        db.session.add(original_timer)
        db.session.commit()
        timer_id = original_timer.id

        # Resume the timer
        response = client.get(f"/timer/resume/{timer_id}", follow_redirects=True)
        assert response.status_code == 200

        # Verify new timer was created
        active_timer = TimeEntry.query.filter_by(user_id=user.id, end_time=None).first()

        assert active_timer is not None
        assert active_timer.id != timer_id
        assert active_timer.project_id == project.id
        assert active_timer.notes == "Original work"
        assert active_timer.tags == "test"
        assert active_timer.billable is True
        assert active_timer.is_active is True


@pytest.mark.integration
@pytest.mark.routes
def test_resume_timer_blocks_if_active_timer_exists(client, user, project):
    """Test that resume is blocked if user already has an active timer"""
    with client.application.app_context():
        # Set up authenticated session
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        # Create a completed time entry
        completed_timer = TimeEntryFactory(
            user_id=user.id,
            project_id=project.id,
            start_time=local_now() - timedelta(hours=2),
            end_time=local_now() - timedelta(hours=1),
            notes="Completed work",
            source="manual",
        )
        db.session.add(completed_timer)

        # Create an active timer
        active_timer = TimeEntryFactory(
            user_id=user.id,
            project_id=project.id,
            start_time=local_now(),
            end_time=None,
            notes="Active work",
            source="auto",
        )
        db.session.add(active_timer)
        db.session.commit()

        # Try to resume the completed timer
        response = client.get(f"/timer/resume/{completed_timer.id}", follow_redirects=True)
        assert response.status_code == 200
        assert b"already have an active timer" in response.data

        # Verify no new timer was created
        timer_count = TimeEntry.query.filter_by(user_id=user.id).count()
        assert timer_count == 2


@pytest.mark.integration
@pytest.mark.routes
def test_resume_timer_fails_for_archived_project(client, user, project):
    """Test that resume fails if project is archived"""
    # Set up data in app context
    with client.application.app_context():
        # Create a completed time entry
        timer = TimeEntry(
            user_id=user.id,
            project_id=project.id,
            start_time=local_now() - timedelta(hours=2),
            end_time=local_now() - timedelta(hours=1),
            notes="Old work",
            source="manual",
        )
        db.session.add(timer)
        db.session.commit()
        timer_id = timer.id

        # Archive the project
        project.status = "archived"
        db.session.commit()

    # Set up authenticated session
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)

    # Try to resume the timer (this creates a new context and session)
    response = client.get(f"/timer/resume/{timer_id}", follow_redirects=True)
    assert response.status_code == 200
    assert b"archived project" in response.data

    # Verify no new timer was created
    with client.application.app_context():
        active_timers = TimeEntry.query.filter_by(user_id=user.id, end_time=None).all()
        assert len(active_timers) == 0


@pytest.mark.integration
@pytest.mark.routes
def test_resume_timer_permission_check(client, user, project):
    """Test that users can only resume their own timers"""
    with client.application.app_context():
        # Create another user
        other_user = User(username="otheruser", role="user")
        other_user.is_active = True  # Set after creation
        db.session.add(other_user)
        db.session.commit()

        # Create a time entry for other user
        other_timer = TimeEntry(
            user_id=other_user.id,
            project_id=project.id,
            start_time=local_now() - timedelta(hours=2),
            end_time=local_now() - timedelta(hours=1),
            notes="Other user's work",
            source="manual",
        )
        db.session.add(other_timer)
        db.session.commit()
        timer_id = other_timer.id

        # Set up authenticated session as first user
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        # Try to resume other user's timer
        response = client.get(f"/timer/resume/{timer_id}", follow_redirects=True)
        assert response.status_code == 200
        assert b"only resume your own timers" in response.data

        # Verify no new timer was created for current user
        active_timers = TimeEntry.query.filter_by(user_id=user.id, end_time=None).all()
        assert len(active_timers) == 0


@pytest.mark.integration
@pytest.mark.routes
def test_resume_timer_handles_deleted_task(client, user, project):
    """Test that resume works even if task was deleted"""
    # Set up data in app context
    with client.application.app_context():
        # Create a task
        task = Task(
            name="Temporary Task", project_id=project.id, status="in_progress", priority="medium", created_by=user.id
        )
        db.session.add(task)
        db.session.commit()
        task_id = task.id

        # Create a time entry with task
        timer = TimeEntry(
            user_id=user.id,
            project_id=project.id,
            task_id=task_id,
            start_time=local_now() - timedelta(hours=2),
            end_time=local_now() - timedelta(hours=1),
            notes="Task work",
            source="manual",
        )
        db.session.add(timer)
        db.session.commit()
        timer_id = timer.id

        # Delete the task
        db.session.delete(task)
        db.session.commit()

    # Set up authenticated session
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)

    # Resume the timer (should work without task)
    response = client.get(f"/timer/resume/{timer_id}", follow_redirects=True)
    assert response.status_code == 200

    # Verify new timer was created without task
    with client.application.app_context():
        active_timer = TimeEntry.query.filter_by(user_id=user.id, end_time=None).first()

        assert active_timer is not None
        assert active_timer.task_id is None
        assert active_timer.notes == "Task work"


@pytest.mark.smoke
def test_resume_timer_smoke(client, user, project):
    """Smoke test for resume timer functionality"""
    with client.application.app_context():
        # Create and complete a time entry
        timer = TimeEntry(
            user_id=user.id,
            project_id=project.id,
            start_time=local_now() - timedelta(hours=1),
            end_time=local_now(),
            notes="Test work",
            source="manual",
        )
        db.session.add(timer)
        db.session.commit()
        timer_id = timer.id

    # Login using the login endpoint (after creating timer)
    client.post("/login", data={"username": user.username, "password": "password123"}, follow_redirects=True)

    # Resume the timer
    response = client.get(f"/timer/resume/{timer_id}", follow_redirects=True)

    # Basic assertions
    assert response.status_code == 200
    assert b"Timer resumed" in response.data

    # Verify active timer exists
    with client.application.app_context():
        active_timer = TimeEntry.query.filter_by(user_id=user.id, end_time=None).first()
        assert active_timer is not None


@pytest.mark.unit
@pytest.mark.models
def test_resume_preserves_billable_status(app, user, project):
    """Test that billable status is preserved when resuming"""
    with app.app_context():
        # Create non-billable timer
        original_timer = TimeEntry(
            user_id=user.id,
            project_id=project.id,
            start_time=local_now() - timedelta(hours=2),
            end_time=local_now() - timedelta(hours=1),
            notes="Non-billable work",
            billable=False,
            source="manual",
        )
        db.session.add(original_timer)
        db.session.commit()

        # Resume timer
        resumed_timer = TimeEntry(
            user_id=original_timer.user_id,
            project_id=original_timer.project_id,
            task_id=original_timer.task_id,
            start_time=local_now(),
            notes=original_timer.notes,
            tags=original_timer.tags,
            source="auto",
            billable=original_timer.billable,
        )
        db.session.add(resumed_timer)
        db.session.commit()

        # Verify billable status was preserved
        assert resumed_timer.billable is False


@pytest.mark.unit
@pytest.mark.models
def test_resume_preserves_tags(app, user, project):
    """Test that tags are preserved when resuming"""
    with app.app_context():
        # Create timer with tags
        original_timer = TimeEntry(
            user_id=user.id,
            project_id=project.id,
            start_time=local_now() - timedelta(hours=2),
            end_time=local_now() - timedelta(hours=1),
            notes="Tagged work",
            tags="urgent,client-request,backend",
            source="manual",
        )
        db.session.add(original_timer)
        db.session.commit()

        # Resume timer
        resumed_timer = TimeEntry(
            user_id=original_timer.user_id,
            project_id=original_timer.project_id,
            task_id=original_timer.task_id,
            start_time=local_now(),
            notes=original_timer.notes,
            tags=original_timer.tags,
            source="auto",
            billable=original_timer.billable,
        )
        db.session.add(resumed_timer)
        db.session.commit()

        # Verify tags were preserved
        assert resumed_timer.tags == "urgent,client-request,backend"
        assert resumed_timer.tag_list == ["urgent", "client-request", "backend"]
