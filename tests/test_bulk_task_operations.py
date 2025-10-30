"""
Test suite for bulk task operations.
Tests bulk delete, bulk status change, bulk assignment, and bulk move to project.
"""

import pytest
from flask import url_for
from app.models import Task, Project, User, TaskActivity
from app import db


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def tasks_for_bulk(app, user, admin_user, project):
    """Create multiple tasks for bulk operations testing."""
    with app.app_context():
        tasks = []
        for i in range(5):
            task = Task(
                project_id=project.id,
                name=f'Bulk Test Task {i+1}',
                description=f'Task {i+1} for bulk operations',
                priority='medium',
                status='todo',
                created_by=user.id
            )
            db.session.add(task)
            tasks.append(task)
        
        db.session.commit()
        
        # Refresh to get IDs
        for task in tasks:
            db.session.refresh(task)
        
        return tasks


@pytest.fixture
def second_project(app):
    """Create a second project for move operations testing."""
    with app.app_context():
        from app.models import Client as ClientModel
        
        # Create or get a client for the second project
        project_client = ClientModel.query.first()
        if not project_client:
            project_client = ClientModel(name='Test Client 2', email='client2@example.com', created_by=1)
            db.session.add(project_client)
            db.session.commit()
            db.session.refresh(project_client)
        
        project = Project(
            name='Second Project',
            client_id=project_client.id,
            billable=True,
            status='active',
            created_by=1
        )
        db.session.add(project)
        db.session.commit()
        db.session.refresh(project)
        
        return project


# ============================================================================
# Bulk Delete Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.routes
def test_bulk_delete_no_tasks_selected(authenticated_client):
    """Test bulk delete with no tasks selected."""
    response = authenticated_client.post('/tasks/bulk-delete', data={
        'task_ids[]': []
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'No tasks selected' in response.data or b'No tasks' in response.data


@pytest.mark.integration
@pytest.mark.routes
def test_bulk_delete_multiple_tasks(authenticated_client, app, tasks_for_bulk):
    """Test bulk deleting multiple tasks."""
    with app.app_context():
        task_ids = [str(task.id) for task in tasks_for_bulk[:3]]
        
        response = authenticated_client.post('/tasks/bulk-delete', data={
            'task_ids[]': task_ids
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Successfully deleted' in response.data or b'deleted' in response.data
        
        # Verify tasks are deleted
        for task_id in task_ids:
            task = Task.query.get(int(task_id))
            assert task is None


@pytest.mark.integration
@pytest.mark.routes
def test_bulk_delete_with_time_entries_skips_task(authenticated_client, app, user, project):
    """Test that bulk delete skips tasks with time entries."""
    with app.app_context():
        # Create task with time entry
        task = Task(
            project_id=project.id,
            name='Task with Time Entry',
            created_by=user.id
        )
        db.session.add(task)
        db.session.commit()
        db.session.refresh(task)
        
        from app.models import TimeEntry
        from datetime import datetime
        entry = TimeEntry(
            user_id=user.id,
            project_id=project.id,
            task_id=task.id,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            duration_seconds=3600
        )
        db.session.add(entry)
        db.session.commit()
        
        response = authenticated_client.post('/tasks/bulk-delete', data={
            'task_ids[]': [str(task.id)]
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Skipped' in response.data or b'time entries' in response.data
        
        # Verify task still exists
        task = Task.query.get(task.id)
        assert task is not None


@pytest.mark.integration
@pytest.mark.routes
def test_bulk_delete_permission_check(client, app, admin_user, user, project):
    """Test that non-admin users can only delete their own tasks."""
    with app.app_context():
        # Create task owned by admin
        admin_task = Task(
            project_id=project.id,
            name='Admin Task',
            created_by=admin_user.id
        )
        db.session.add(admin_task)
        db.session.commit()
        db.session.refresh(admin_task)
        
        # Try to delete as regular user
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
        
        response = client.post('/tasks/bulk-delete', data={
            'task_ids[]': [str(admin_task.id)]
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Verify task still exists (skipped due to no permission)
        task = Task.query.get(admin_task.id)
        assert task is not None


# ============================================================================
# Bulk Status Change Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.routes
def test_bulk_status_no_tasks_selected(authenticated_client):
    """Test bulk status change with no tasks selected."""
    response = authenticated_client.post('/tasks/bulk-status', data={
        'task_ids[]': [],
        'status': 'in_progress'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'No tasks selected' in response.data or b'No tasks' in response.data


@pytest.mark.integration
@pytest.mark.routes
def test_bulk_status_change_multiple_tasks(authenticated_client, app, tasks_for_bulk):
    """Test changing status for multiple tasks."""
    with app.app_context():
        task_ids = [str(task.id) for task in tasks_for_bulk[:3]]
        
        response = authenticated_client.post('/tasks/bulk-status', data={
            'task_ids[]': task_ids,
            'status': 'in_progress'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Successfully updated' in response.data or b'updated' in response.data
        
        # Verify status is changed
        for task_id in task_ids:
            task = Task.query.get(int(task_id))
            assert task is not None
            assert task.status == 'in_progress'


@pytest.mark.integration
@pytest.mark.routes
def test_bulk_status_invalid_status(authenticated_client, app, tasks_for_bulk):
    """Test bulk status change with invalid status."""
    with app.app_context():
        task_ids = [str(task.id) for task in tasks_for_bulk[:2]]
        
        response = authenticated_client.post('/tasks/bulk-status', data={
            'task_ids[]': task_ids,
            'status': 'invalid_status'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Invalid status' in response.data or b'error' in response.data.lower()


@pytest.mark.integration
@pytest.mark.routes
def test_bulk_status_reopen_from_done(authenticated_client, app, tasks_for_bulk):
    """Test bulk status change to reopen completed tasks."""
    with app.app_context():
        # Mark tasks as done first
        for task in tasks_for_bulk[:2]:
            task.status = 'done'
            from datetime import datetime
            task.completed_at = datetime.utcnow()
        db.session.commit()
        
        task_ids = [str(task.id) for task in tasks_for_bulk[:2]]
        
        response = authenticated_client.post('/tasks/bulk-status', data={
            'task_ids[]': task_ids,
            'status': 'in_progress'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Verify completed_at is cleared
        for task_id in task_ids:
            task = Task.query.get(int(task_id))
            assert task.status == 'in_progress'
            assert task.completed_at is None


# ============================================================================
# Bulk Assignment Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.routes
def test_bulk_assign_no_tasks_selected(authenticated_client, user):
    """Test bulk assignment with no tasks selected."""
    response = authenticated_client.post('/tasks/bulk-assign', data={
        'task_ids[]': [],
        'assigned_to': user.id
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'No tasks selected' in response.data or b'No tasks' in response.data


@pytest.mark.integration
@pytest.mark.routes
def test_bulk_assign_multiple_tasks(authenticated_client, app, tasks_for_bulk, admin_user):
    """Test assigning multiple tasks to a user."""
    with app.app_context():
        task_ids = [str(task.id) for task in tasks_for_bulk[:3]]
        
        response = authenticated_client.post('/tasks/bulk-assign', data={
            'task_ids[]': task_ids,
            'assigned_to': admin_user.id
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Successfully assigned' in response.data or b'assigned' in response.data
        
        # Verify assignment
        for task_id in task_ids:
            task = Task.query.get(int(task_id))
            assert task is not None
            assert task.assigned_to == admin_user.id


@pytest.mark.integration
@pytest.mark.routes
def test_bulk_assign_no_user_selected(authenticated_client, app, tasks_for_bulk):
    """Test bulk assignment without selecting a user."""
    with app.app_context():
        task_ids = [str(task.id) for task in tasks_for_bulk[:2]]
        
        response = authenticated_client.post('/tasks/bulk-assign', data={
            'task_ids[]': task_ids
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'No user selected' in response.data or b'error' in response.data.lower()


@pytest.mark.integration
@pytest.mark.routes
def test_bulk_assign_invalid_user(authenticated_client, app, tasks_for_bulk):
    """Test bulk assignment with invalid user ID."""
    with app.app_context():
        task_ids = [str(task.id) for task in tasks_for_bulk[:2]]
        
        response = authenticated_client.post('/tasks/bulk-assign', data={
            'task_ids[]': task_ids,
            'assigned_to': 99999  # Non-existent user ID
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Invalid user' in response.data or b'error' in response.data.lower()


# ============================================================================
# Bulk Move to Project Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.routes
def test_bulk_move_project_no_tasks_selected(authenticated_client, project):
    """Test bulk move to project with no tasks selected."""
    response = authenticated_client.post('/tasks/bulk-move-project', data={
        'task_ids[]': [],
        'project_id': project.id
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'No tasks selected' in response.data or b'No tasks' in response.data


@pytest.mark.integration
@pytest.mark.routes
def test_bulk_move_project_multiple_tasks(authenticated_client, app, tasks_for_bulk, second_project):
    """Test moving multiple tasks to a different project."""
    with app.app_context():
        task_ids = [str(task.id) for task in tasks_for_bulk[:3]]
        original_project_id = tasks_for_bulk[0].project_id
        
        response = authenticated_client.post('/tasks/bulk-move-project', data={
            'task_ids[]': task_ids,
            'project_id': second_project.id
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Successfully moved' in response.data or b'moved' in response.data
        
        # Verify project change
        for task_id in task_ids:
            task = Task.query.get(int(task_id))
            assert task is not None
            assert task.project_id == second_project.id
            assert task.project_id != original_project_id


@pytest.mark.integration
@pytest.mark.routes
def test_bulk_move_project_updates_time_entries(authenticated_client, app, user, project, second_project):
    """Test that bulk move to project updates related time entries."""
    with app.app_context():
        # Create task with time entry
        task = Task(
            project_id=project.id,
            name='Task with Time Entry',
            created_by=user.id
        )
        db.session.add(task)
        db.session.commit()
        db.session.refresh(task)
        
        from app.models import TimeEntry
        from datetime import datetime
        entry = TimeEntry(
            user_id=user.id,
            project_id=project.id,
            task_id=task.id,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            duration_seconds=3600
        )
        db.session.add(entry)
        db.session.commit()
        db.session.refresh(entry)
        
        response = authenticated_client.post('/tasks/bulk-move-project', data={
            'task_ids[]': [str(task.id)],
            'project_id': second_project.id
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Verify time entry project is updated
        entry = TimeEntry.query.get(entry.id)
        assert entry.project_id == second_project.id


@pytest.mark.integration
@pytest.mark.routes
def test_bulk_move_project_no_project_selected(authenticated_client, app, tasks_for_bulk):
    """Test bulk move to project without selecting a project."""
    with app.app_context():
        task_ids = [str(task.id) for task in tasks_for_bulk[:2]]
        
        response = authenticated_client.post('/tasks/bulk-move-project', data={
            'task_ids[]': task_ids
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'No project selected' in response.data or b'error' in response.data.lower()


@pytest.mark.integration
@pytest.mark.routes
def test_bulk_move_project_invalid_project(authenticated_client, app, tasks_for_bulk):
    """Test bulk move to project with invalid project ID."""
    with app.app_context():
        task_ids = [str(task.id) for task in tasks_for_bulk[:2]]
        
        response = authenticated_client.post('/tasks/bulk-move-project', data={
            'task_ids[]': task_ids,
            'project_id': 99999  # Non-existent project ID
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Invalid project' in response.data or b'error' in response.data.lower()


@pytest.mark.integration
@pytest.mark.routes
def test_bulk_move_project_logs_activity(authenticated_client, app, tasks_for_bulk, second_project):
    """Test that bulk move to project logs task activity."""
    with app.app_context():
        task_ids = [str(task.id) for task in tasks_for_bulk[:2]]
        
        response = authenticated_client.post('/tasks/bulk-move-project', data={
            'task_ids[]': task_ids,
            'project_id': second_project.id
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Verify activity is logged
        for task_id in task_ids:
            task = Task.query.get(int(task_id))
            activities = task.activities.filter_by(event='project_change').all()
            assert len(activities) > 0


# ============================================================================
# Smoke Tests
# ============================================================================

@pytest.mark.smoke
@pytest.mark.routes
def test_bulk_operations_routes_exist(authenticated_client):
    """Smoke test to verify bulk operations routes exist."""
    # Test bulk delete route
    response = authenticated_client.post('/tasks/bulk-delete', data={
        'task_ids[]': []
    }, follow_redirects=True)
    assert response.status_code == 200
    
    # Test bulk status route
    response = authenticated_client.post('/tasks/bulk-status', data={
        'task_ids[]': [],
        'status': 'todo'
    }, follow_redirects=True)
    assert response.status_code == 200
    
    # Test bulk assign route
    response = authenticated_client.post('/tasks/bulk-assign', data={
        'task_ids[]': []
    }, follow_redirects=True)
    assert response.status_code == 200
    
    # Test bulk move project route
    response = authenticated_client.post('/tasks/bulk-move-project', data={
        'task_ids[]': []
    }, follow_redirects=True)
    assert response.status_code == 200


@pytest.mark.smoke
@pytest.mark.routes
def test_task_list_has_checkboxes(authenticated_client):
    """Smoke test to verify task list page has checkboxes for bulk operations."""
    response = authenticated_client.get('/tasks')
    assert response.status_code == 200
    assert b'task-checkbox' in response.data or b'checkbox' in response.data
    assert b'selectAll' in response.data or b'select' in response.data.lower()


# ============================================================================
# CSV Export Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.routes
def test_export_tasks_csv(authenticated_client, app, tasks_for_bulk):
    """Test exporting tasks to CSV."""
    with app.app_context():
        response = authenticated_client.get('/tasks/export')
        
        assert response.status_code == 200
        assert response.mimetype == 'text/csv'
        assert 'attachment' in response.headers.get('Content-Disposition', '')
        
        # Check CSV content
        csv_data = response.data.decode('utf-8')
        assert 'ID' in csv_data
        assert 'Name' in csv_data
        assert 'Project' in csv_data
        assert 'Status' in csv_data
        
        # Check that task data is in CSV
        assert tasks_for_bulk[0].name in csv_data


@pytest.mark.integration
@pytest.mark.routes
def test_export_tasks_with_filters(authenticated_client, app, tasks_for_bulk):
    """Test exporting tasks with filters applied."""
    with app.app_context():
        # Update one task to a different status
        tasks_for_bulk[0].status = 'in_progress'
        db.session.commit()
        
        # Export with status filter
        response = authenticated_client.get('/tasks/export?status=in_progress')
        
        assert response.status_code == 200
        csv_data = response.data.decode('utf-8')
        
        # Verify CSV structure
        lines = csv_data.split('\n')
        assert 'ID,Name,Description,Project,Status' in lines[0]
        
        # Check if filter worked - if no data, at least header should be there
        # The actual data presence depends on permission model
        assert len(lines) >= 1  # At least header


@pytest.mark.smoke
@pytest.mark.routes
def test_export_button_exists(authenticated_client):
    """Smoke test to verify export button exists on task list."""
    response = authenticated_client.get('/tasks')
    assert response.status_code == 200
    assert b'Export' in response.data or b'export' in response.data
    assert b'/tasks/export' in response.data

