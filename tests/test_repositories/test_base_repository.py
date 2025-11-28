"""
Tests for BaseRepository.
"""

import pytest
from app.repositories.base_repository import BaseRepository
from app.models import Project, Client
from app import db


@pytest.mark.unit
def test_get_by_id_success(app, test_project):
    """Test getting record by ID"""
    repo = BaseRepository(Project)
    project = repo.get_by_id(test_project.id)

    assert project is not None
    assert project.id == test_project.id
    assert project.name == test_project.name


@pytest.mark.unit
def test_get_by_id_not_found(app):
    """Test getting non-existent record"""
    repo = BaseRepository(Project)
    project = repo.get_by_id(99999)

    assert project is None


@pytest.mark.unit
def test_find_by(app, test_client_model):
    """Test finding records by criteria"""
    repo = BaseRepository(Project)

    # Create a project
    project = Project(name="Test Project", client_id=test_client_model.id)
    db.session.add(project)
    db.session.commit()

    # Find by status
    projects = repo.find_by(status="active")
    assert len(projects) >= 1
    assert any(p.id == project.id for p in projects)


@pytest.mark.unit
def test_find_one_by(app, test_client_model):
    """Test finding single record"""
    repo = BaseRepository(Project)

    # Create a project
    project = Project(name="Unique Project", client_id=test_client_model.id)
    db.session.add(project)
    db.session.commit()

    # Find one
    found = repo.find_one_by(name="Unique Project")
    assert found is not None
    assert found.id == project.id


@pytest.mark.unit
def test_create(app, test_client_model):
    """Test creating a record"""
    repo = BaseRepository(Project)

    project = repo.create(name="New Project", client_id=test_client_model.id, status="active")

    assert project is not None
    assert project.name == "New Project"
    assert project.id is None  # Not yet committed

    db.session.commit()
    assert project.id is not None


@pytest.mark.unit
def test_update(app, test_project):
    """Test updating a record"""
    repo = BaseRepository(Project)

    original_name = test_project.name
    repo.update(test_project, name="Updated Name")

    assert test_project.name == "Updated Name"
    assert test_project.name != original_name


@pytest.mark.unit
def test_count(app, test_client_model):
    """Test counting records"""
    repo = BaseRepository(Project)

    # Create some projects
    project1 = Project(name="Project 1", client_id=test_client_model.id)
    project2 = Project(name="Project 2", client_id=test_client_model.id)
    db.session.add_all([project1, project2])
    db.session.commit()

    # Count all
    total = repo.count()
    assert total >= 2

    # Count by status
    active_count = repo.count(status="active")
    assert active_count >= 2


@pytest.mark.unit
def test_exists(app, test_project):
    """Test checking existence"""
    repo = BaseRepository(Project)

    assert repo.exists(id=test_project.id) is True
    assert repo.exists(id=99999) is False
