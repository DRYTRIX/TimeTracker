import pytest
from datetime import datetime, timedelta

from app import db
from app.models import Project, Task, TimeEntry


@pytest.mark.smoke
@pytest.mark.routes
def test_edit_task_changes_project_and_updates_time_entries(authenticated_client, app, user, test_client):
    with app.app_context():
        # Create two active projects under the same client
        project1 = Project(name='Project One', client_id=test_client.id, description='P1')
        project1.status = 'active'
        project2 = Project(name='Project Two', client_id=test_client.id, description='P2')
        project2.status = 'active'
        db.session.add_all([project1, project2])
        db.session.commit()

        # Create a task on project1
        task = Task(project_id=project1.id, name='Move Me', created_by=user.id)
        db.session.add(task)
        db.session.commit()

        # Create a time entry associated with this task and project1
        start_time = datetime.utcnow() - timedelta(hours=2)
        end_time = datetime.utcnow() - timedelta(hours=1)
        entry = TimeEntry(
            user_id=user.id,
            project_id=project1.id,
            task_id=task.id,
            start_time=start_time,
            end_time=end_time,
            notes='Work on task before moving'
        )
        db.session.add(entry)
        db.session.commit()

        # Store IDs before POST request
        task_id = task.id
        entry_id = entry.id
        project2_id = project2.id  # Store project2 ID before leaving app context
    
    # Submit edit form to change the project to project2 (POST happens outside app context)
    resp = authenticated_client.post(
        f'/tasks/{task_id}/edit',
        data={
            'project_id': str(project2_id),  # Use stored ID
            'name': 'Move Me',  # Use explicit name
            'description': '',
            'priority': 'medium',
            'status': 'todo',  # Include status to match current task status
            'estimated_hours': '',
            'due_date': '',
            'assigned_to': ''
        },
        follow_redirects=True  # Follow redirects to see final response
    )

    # Expect success (200 after redirect or 302 redirect)
    assert resp.status_code in (200, 302, 303), f"Expected 200/302/303, got {resp.status_code}. Response: {resp.get_data(as_text=True)[:500]}"

    # Re-query objects to verify project change persisted (within app context)
    with app.app_context():
        task = Task.query.get(task_id)
        entry = TimeEntry.query.get(entry_id)
        assert task is not None, "Task should still exist"
        assert entry is not None, "Entry should still exist"
        assert task.project_id == project2_id, f"Task project_id is {task.project_id}, expected {project2_id}"
        assert entry.project_id == project2_id, f"Entry project_id is {entry.project_id}, expected {project2_id}"


