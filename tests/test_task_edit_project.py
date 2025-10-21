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

        # Submit edit form to change the project to project2
        resp = authenticated_client.post(
            f'/tasks/{task.id}/edit',
            data={
                'project_id': project2.id,
                'name': task.name,
                'description': '',
                'priority': 'medium',
                'estimated_hours': '',
                'due_date': '',
                'assigned_to': ''
            },
            follow_redirects=False
        )

        # Expect redirect to task view
        assert resp.status_code in (302, 303)

        # Refresh objects and verify project change persisted
        db.session.refresh(task)
        db.session.refresh(entry)
        assert task.project_id == project2.id
        assert entry.project_id == project2.id


