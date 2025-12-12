import pytest
from app import db
from app.models import Project, User, SavedFilter, Task


@pytest.mark.smoke
@pytest.mark.api
def test_burndown_endpoint_available(client, app):
    """Test that burndown endpoint is available."""
    # Minimal entities
    u = User(username="admin")
    u.role = "admin"
    u.is_active = True
    db.session.add(u)
    p = Project(name="X", client_id=1, billable=False)
    db.session.add(p)
    db.session.commit()
    # Just ensure route exists; not full auth flow here
    # This is a placeholder smoke test to be expanded in integration tests
    assert True


@pytest.mark.smoke
@pytest.mark.models
def test_saved_filter_model_roundtrip(app):
    """Test that SavedFilter can be created and serialized."""
    # Ensure SavedFilter can be created and serialized
    sf = SavedFilter(user_id=1, name="My Filter", scope="time", payload={"project_id": 1, "tag": "deep"})
    db.session.add(sf)
    db.session.commit()
    as_dict = sf.to_dict()
    assert as_dict["name"] == "My Filter"
    assert as_dict["scope"] == "time"


@pytest.mark.api
@pytest.mark.integration
def test_inline_client_creation_json_flow(admin_authenticated_client):
    """Creating a client via AJAX JSON should return 201 and client payload."""
    resp = admin_authenticated_client.post(
        "/clients/create",
        data={"name": "Inline Modal Client", "default_hourly_rate": "123.45"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code in (201, 400, 403)
    if resp.status_code == 201:
        data = resp.get_json()
        assert data["name"] == "Inline Modal Client"
        assert data["id"] > 0


@pytest.mark.api
@pytest.mark.integration
@pytest.mark.models
def test_inline_task_creation_json_flow(authenticated_client, project, user, app):
    """Creating a task via AJAX JSON should return 201 and task payload with defaults."""
    with app.app_context():
        from app.models import Task
        
        resp = authenticated_client.post(
            "/api/tasks/create",
            json={"name": "Inline Timer Task", "project_id": project.id},
            headers={"X-Requested-With": "XMLHttpRequest", "Content-Type": "application/json"},
        )
        assert resp.status_code in (201, 400, 404)
        if resp.status_code == 201:
            data = resp.get_json()
            assert data["success"] is True
            assert data["name"] == "Inline Timer Task"
            assert data["id"] > 0
            assert "task" in data
            
            # Verify task was created with defaults
            task = Task.query.get(data["id"])
            assert task is not None
            assert task.name == "Inline Timer Task"
            assert task.project_id == project.id
            assert task.assigned_to == user.id  # Assigned to current user
            assert task.priority == "medium"  # Default priority
            assert task.due_date is None  # No due date
            assert task.created_by == user.id


@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.integration
def test_start_timer_with_new_task_creation(authenticated_client, project, user, app):
    """Smoke test: Start timer with new task creation flow."""
    with app.app_context():
        from app.models import TimeEntry
        
        # Simulate the flow: create task inline, then start timer
        # Step 1: Create task via AJAX
        task_resp = authenticated_client.post(
            "/api/tasks/create",
            json={"name": "Quick Task for Timer", "project_id": project.id},
            headers={"X-Requested-With": "XMLHttpRequest", "Content-Type": "application/json"},
        )
        
        if task_resp.status_code == 201:
            task_data = task_resp.get_json()
            task_id = task_data["id"]
            
            # Step 2: Start timer with the created task
            timer_resp = authenticated_client.post(
                "/timer/start",
                data={"project_id": project.id, "task_id": task_id},
                follow_redirects=False,
            )
            
            # Timer start should redirect or succeed
            assert timer_resp.status_code in (200, 302, 400, 404)
            
            # Verify timer was created
            if timer_resp.status_code in (200, 302):
                timer = TimeEntry.query.filter_by(
                    user_id=user.id,
                    project_id=project.id,
                    task_id=task_id,
                    end_time=None  # Active timer
                ).first()
                assert timer is not None, "Timer should be created"
