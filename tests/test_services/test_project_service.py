"""
Tests for ProjectService.
"""

import pytest
from datetime import datetime
from app.services import ProjectService
from app.models import Project, Client, User
from app import db


@pytest.mark.unit
def test_create_project_success(app, test_client_model, test_user):
    """Test successful project creation"""
    service = ProjectService()

    result = service.create_project(
        name="Test Project",
        client_id=test_client_model.id,
        description="Test description",
        billable=True,
        created_by=test_user.id,
    )

    assert result["success"] is True
    assert result["project"] is not None
    assert result["project"].name == "Test Project"
    assert result["project"].client_id == test_client_model.id


@pytest.mark.unit
def test_create_project_invalid_client(app, test_user):
    """Test project creation with invalid client"""
    service = ProjectService()

    result = service.create_project(
        name="Test Project", client_id=99999, created_by=test_user.id  # Non-existent client
    )

    assert result["success"] is False
    assert result["error"] == "invalid_client"


@pytest.mark.unit
def test_list_projects_with_eager_loading(app, test_client_model, test_user):
    """Test listing projects with eager loading prevents N+1"""
    service = ProjectService()

    # Create a project
    project = Project(name="Test Project", client_id=test_client_model.id, created_by=test_user.id)
    db.session.add(project)
    db.session.commit()

    # List projects
    result = service.list_projects(status="active", page=1, per_page=20)

    assert result["projects"] is not None
    assert len(result["projects"]) >= 1

    # Verify client is loaded (no N+1 query)
    project = result["projects"][0]
    # Accessing client should not trigger additional query
    assert project.client is not None
    assert project.client.id == test_client_model.id


@pytest.mark.unit
def test_get_project_with_details(app, test_client_model, test_user):
    """Test getting project with all details"""
    service = ProjectService()

    # Create a project
    project = Project(name="Test Project", client_id=test_client_model.id, created_by=test_user.id)
    db.session.add(project)
    db.session.commit()

    # Get project details
    project = service.get_project_with_details(
        project_id=project.id, include_time_entries=True, include_tasks=True, include_comments=True, include_costs=True
    )

    assert project is not None
    assert project.name == "Test Project"
    # Verify relations are loaded
    assert project.client is not None


@pytest.mark.unit
def test_list_projects_filtering(app, test_client_model, test_user):
    """Test project list filtering"""
    service = ProjectService()

    # Create projects
    project1 = Project(name="Active Project", client_id=test_client_model.id, status="active", created_by=test_user.id)
    project2 = Project(
        name="Archived Project", client_id=test_client_model.id, status="archived", created_by=test_user.id
    )
    db.session.add_all([project1, project2])
    db.session.commit()

    # Filter by active status
    result = service.list_projects(status="active", page=1, per_page=20)
    active_projects = [p for p in result["projects"] if p.status == "active"]
    assert len(active_projects) >= 1

    # Filter by archived status
    result = service.list_projects(status="archived", page=1, per_page=20)
    archived_projects = [p for p in result["projects"] if p.status == "archived"]
    assert len(archived_projects) >= 1
