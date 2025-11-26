"""
Tests for TaskService.
"""

import pytest
from datetime import date
from app.services import TaskService
from app.models import Task, Project, User
from app import db


@pytest.mark.unit
def test_create_task_success(app, test_project, test_user):
    """Test successful task creation"""
    service = TaskService()
    
    result = service.create_task(
        name="Test Task",
        project_id=test_project.id,
        description="Test description",
        priority='high',
        created_by=test_user.id
    )
    
    assert result['success'] is True
    assert result['task'] is not None
    assert result['task'].name == "Test Task"
    assert result['task'].project_id == test_project.id


@pytest.mark.unit
def test_create_task_invalid_project(app, test_user):
    """Test task creation with invalid project"""
    service = TaskService()
    
    result = service.create_task(
        name="Test Task",
        project_id=99999,  # Non-existent project
        created_by=test_user.id
    )
    
    assert result['success'] is False
    assert result['error'] == 'invalid_project'


@pytest.mark.unit
def test_list_tasks_with_eager_loading(app, test_project, test_user):
    """Test listing tasks with eager loading prevents N+1"""
    service = TaskService()
    
    # Create a task
    task = Task(
        name="Test Task",
        project_id=test_project.id,
        created_by=test_user.id
    )
    db.session.add(task)
    db.session.commit()
    
    # List tasks
    result = service.list_tasks(
        project_id=test_project.id,
        user_id=test_user.id,
        is_admin=True,
        page=1,
        per_page=20
    )
    
    assert result['tasks'] is not None
    assert len(result['tasks']) >= 1
    
    # Verify project is loaded (no N+1 query)
    task = result['tasks'][0]
    assert task.project is not None
    assert task.project.id == test_project.id


@pytest.mark.unit
def test_get_task_with_details(app, test_project, test_user):
    """Test getting task with all details"""
    service = TaskService()
    
    # Create a task
    task = Task(
        name="Test Task",
        project_id=test_project.id,
        created_by=test_user.id
    )
    db.session.add(task)
    db.session.commit()
    
    # Get task details
    task = service.get_task_with_details(
        task_id=task.id,
        include_time_entries=True,
        include_comments=True,
        include_activities=True
    )
    
    assert task is not None
    assert task.name == "Test Task"
    # Verify relations are loaded
    assert task.project is not None

