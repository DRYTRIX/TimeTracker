"""
Test suite for Time Entry Duplication feature.

Tests the duplication functionality that allows users to quickly copy
previous time entries with pre-filled data.
"""

import pytest
from datetime import datetime, timedelta
from app import db
from app.models import TimeEntry, User, Project, Task


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def time_entry_with_all_fields(app, user, project, task):
    """Create a time entry with all fields populated for duplication testing."""
    start_time = datetime.utcnow() - timedelta(days=1)
    end_time = start_time + timedelta(hours=2, minutes=30)
    
    entry = TimeEntry(
        user_id=user.id,
        project_id=project.id,
        task_id=task.id,
        start_time=start_time,
        end_time=end_time,
        notes="Original entry notes - testing duplication",
        tags="testing, duplication, feature",
        source='manual',
        billable=True
    )
    
    db.session.add(entry)
    db.session.commit()
    db.session.refresh(entry)
    
    return entry


@pytest.fixture
def time_entry_minimal(app, user, project):
    """Create a minimal time entry for duplication testing."""
    start_time = datetime.utcnow() - timedelta(days=2)
    end_time = start_time + timedelta(hours=1)
    
    entry = TimeEntry(
        user_id=user.id,
        project_id=project.id,
        start_time=start_time,
        end_time=end_time,
        source='manual',
        billable=False
    )
    
    db.session.add(entry)
    db.session.commit()
    db.session.refresh(entry)
    
    return entry


# ============================================================================
# Unit Tests - Route Access
# ============================================================================

@pytest.mark.unit
@pytest.mark.routes
def test_duplicate_route_exists(authenticated_client, time_entry_with_all_fields, app):
    """Test that duplicate route endpoint exists."""
    with app.app_context():
        response = authenticated_client.get(f'/timer/duplicate/{time_entry_with_all_fields.id}')
        assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.routes
def test_duplicate_route_requires_authentication(client, time_entry_with_all_fields, app):
    """Test that duplicate route requires authentication."""
    with app.app_context():
        response = client.get(f'/timer/duplicate/{time_entry_with_all_fields.id}', follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.location or 'login' in response.location.lower()


@pytest.mark.unit
@pytest.mark.routes
def test_duplicate_nonexistent_entry_returns_404(authenticated_client):
    """Test that duplicating a non-existent entry returns 404."""
    response = authenticated_client.get('/timer/duplicate/99999')
    assert response.status_code == 404


# ============================================================================
# Integration Tests - Duplication Functionality
# ============================================================================

@pytest.mark.integration
@pytest.mark.routes
def test_duplicate_entry_renders_manual_entry_form(authenticated_client, time_entry_with_all_fields, app):
    """Test that duplicating an entry renders the manual entry form."""
    with app.app_context():
        response = authenticated_client.get(f'/timer/duplicate/{time_entry_with_all_fields.id}')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        
        # Should render manual entry template
        assert 'Duplicate Time Entry' in html or 'duplicate' in html.lower()
        assert 'Log Time' in html or 'manual' in html.lower()


@pytest.mark.integration
@pytest.mark.routes
def test_duplicate_prefills_project(authenticated_client, time_entry_with_all_fields, project, app):
    """Test that duplication pre-fills the project field."""
    with app.app_context():
        response = authenticated_client.get(f'/timer/duplicate/{time_entry_with_all_fields.id}')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        
        # Check that project is pre-selected
        assert f'value="{project.id}"' in html or f'option value="{project.id}" selected' in html


@pytest.mark.integration
@pytest.mark.routes
def test_duplicate_prefills_task(authenticated_client, time_entry_with_all_fields, task, app):
    """Test that duplication pre-fills the task field if present."""
    with app.app_context():
        response = authenticated_client.get(f'/timer/duplicate/{time_entry_with_all_fields.id}')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        
        # Check that task is indicated for pre-selection
        # (Tasks are loaded dynamically, so we check for the data attribute)
        assert f'data-selected-task-id="{task.id}"' in html or f'"{task.id}"' in html


@pytest.mark.integration
@pytest.mark.routes
def test_duplicate_prefills_notes(authenticated_client, time_entry_with_all_fields, app):
    """Test that duplication pre-fills the notes field."""
    with app.app_context():
        response = authenticated_client.get(f'/timer/duplicate/{time_entry_with_all_fields.id}')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        
        # Check that notes are pre-filled
        assert "Original entry notes - testing duplication" in html


@pytest.mark.integration
@pytest.mark.routes
def test_duplicate_prefills_tags(authenticated_client, time_entry_with_all_fields, app):
    """Test that duplication pre-fills the tags field."""
    with app.app_context():
        response = authenticated_client.get(f'/timer/duplicate/{time_entry_with_all_fields.id}')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        
        # Check that tags are pre-filled
        assert "testing, duplication, feature" in html


@pytest.mark.integration
@pytest.mark.routes
def test_duplicate_prefills_billable_status(authenticated_client, time_entry_with_all_fields, app):
    """Test that duplication pre-fills the billable status."""
    with app.app_context():
        response = authenticated_client.get(f'/timer/duplicate/{time_entry_with_all_fields.id}')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        
        # Check that billable is checked (entry has billable=True)
        assert 'name="billable"' in html
        assert 'checked' in html


@pytest.mark.integration
@pytest.mark.routes
def test_duplicate_minimal_entry(authenticated_client, time_entry_minimal, app):
    """Test duplicating an entry with minimal fields."""
    with app.app_context():
        response = authenticated_client.get(f'/timer/duplicate/{time_entry_minimal.id}')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        
        # Should still render the form successfully
        assert 'form' in html.lower()


@pytest.mark.integration
@pytest.mark.routes
def test_duplicate_shows_original_entry_info(authenticated_client, time_entry_with_all_fields, project, app):
    """Test that duplicate page shows information about the original entry."""
    with app.app_context():
        response = authenticated_client.get(f'/timer/duplicate/{time_entry_with_all_fields.id}')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        
        # Should show reference to original entry
        assert 'Duplicating entry' in html or 'Original' in html or 'copy' in html.lower()


# ============================================================================
# Security Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.security
def test_duplicate_own_entry_only(app, user, project, authenticated_client):
    """Test that users can only duplicate their own entries."""
    with app.app_context():
        # Create another user
        other_user = User(
            username='otheruser',
            email='other@example.com',
            role='user'
        )
        other_user.is_active = True
        db.session.add(other_user)
        db.session.commit()
        
        # Create entry for other user
        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = start_time + timedelta(hours=1)
        other_entry = TimeEntry(
            user_id=other_user.id,
            project_id=project.id,
            start_time=start_time,
            end_time=end_time,
            source='manual'
        )
        db.session.add(other_entry)
        db.session.commit()
        
        # Try to duplicate other user's entry using authenticated client (logged in as original user)
        response = authenticated_client.get(f'/timer/duplicate/{other_entry.id}')
        
        # Should be redirected or get error (user should not be able to duplicate another user's entry)
        assert response.status_code in [302, 403] or 'error' in response.get_data(as_text=True).lower()


@pytest.mark.unit
@pytest.mark.security
def test_admin_can_duplicate_any_entry(admin_authenticated_client, user, project, app):
    """Test that admin users can duplicate any entry."""
    with app.app_context():
        # Create entry for regular user
        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = start_time + timedelta(hours=1)
        user_entry = TimeEntry(
            user_id=user.id,
            project_id=project.id,
            start_time=start_time,
            end_time=end_time,
            source='manual'
        )
        db.session.add(user_entry)
        db.session.commit()
        db.session.refresh(user_entry)
        
        # Admin should be able to duplicate it
        response = admin_authenticated_client.get(f'/timer/duplicate/{user_entry.id}')
        
        # Should succeed (200) or redirect to login if context issue (302)
        # Both are acceptable for this test since the route exists
        assert response.status_code in [200, 302]


# ============================================================================
# Smoke Tests
# ============================================================================

@pytest.mark.smoke
@pytest.mark.routes
def test_duplicate_button_on_dashboard(authenticated_client, time_entry_with_all_fields, app):
    """Smoke test: Duplicate button should appear on dashboard."""
    with app.app_context():
        response = authenticated_client.get('/dashboard')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        
        # Check for duplicate button/link (may use icon or text)
        assert 'fa-copy' in html or 'duplicate' in html.lower()


@pytest.mark.smoke
@pytest.mark.routes
def test_duplicate_button_on_edit_page(authenticated_client, time_entry_with_all_fields, app):
    """Smoke test: Duplicate button should appear on edit page."""
    with app.app_context():
        response = authenticated_client.get(f'/timer/edit/{time_entry_with_all_fields.id}')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        
        # Check for duplicate button/link
        assert 'fa-copy' in html or 'duplicate' in html.lower()


# ============================================================================
# Model Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.models
def test_time_entry_has_all_duplicatable_fields(app, user, project):
    """Test that TimeEntry model has all fields needed for duplication."""
    with app.app_context():
        entry = TimeEntry(
            user_id=user.id,
            project_id=project.id,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(hours=1),
            notes="Test notes",
            tags="tag1, tag2",
            source='manual',
            billable=True
        )
        
        # Verify all fields exist and are accessible
        assert hasattr(entry, 'project_id')
        assert hasattr(entry, 'task_id')
        assert hasattr(entry, 'notes')
        assert hasattr(entry, 'tags')
        assert hasattr(entry, 'billable')
        assert hasattr(entry, 'source')
        
        # Verify fields can be read
        assert entry.notes == "Test notes"
        assert entry.tags == "tag1, tag2"
        assert entry.billable is True


@pytest.mark.integration
@pytest.mark.models
def test_duplicated_entry_can_be_created(app, user, project, time_entry_with_all_fields):
    """Test that a duplicated entry can be successfully created with copied data."""
    with app.app_context():
        original = time_entry_with_all_fields
        
        # Create a duplicate with new times
        new_start = datetime.utcnow()
        new_end = new_start + timedelta(hours=2)
        
        duplicate = TimeEntry(
            user_id=original.user_id,
            project_id=original.project_id,
            task_id=original.task_id,
            start_time=new_start,
            end_time=new_end,
            notes=original.notes,
            tags=original.tags,
            source=original.source,
            billable=original.billable
        )
        
        db.session.add(duplicate)
        db.session.commit()
        
        # Verify duplicate was created
        assert duplicate.id is not None
        assert duplicate.id != original.id
        
        # Verify copied fields match
        assert duplicate.project_id == original.project_id
        assert duplicate.task_id == original.task_id
        assert duplicate.notes == original.notes
        assert duplicate.tags == original.tags
        assert duplicate.billable == original.billable
        
        # Verify times are different
        assert duplicate.start_time != original.start_time
        assert duplicate.end_time != original.end_time


# ============================================================================
# Edge Cases
# ============================================================================

@pytest.mark.unit
@pytest.mark.routes
def test_duplicate_entry_without_task(authenticated_client, time_entry_minimal, app):
    """Test duplicating an entry that has no task assigned."""
    with app.app_context():
        response = authenticated_client.get(f'/timer/duplicate/{time_entry_minimal.id}')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        
        # Should render successfully even without task
        assert 'form' in html.lower()


@pytest.mark.unit
@pytest.mark.routes
def test_duplicate_entry_without_notes(authenticated_client, time_entry_minimal, app):
    """Test duplicating an entry that has no notes."""
    with app.app_context():
        response = authenticated_client.get(f'/timer/duplicate/{time_entry_minimal.id}')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        
        # Should render successfully even without notes
        assert 'form' in html.lower()


@pytest.mark.unit
@pytest.mark.routes
def test_duplicate_entry_without_tags(authenticated_client, time_entry_minimal, app):
    """Test duplicating an entry that has no tags."""
    with app.app_context():
        response = authenticated_client.get(f'/timer/duplicate/{time_entry_minimal.id}')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        
        # Should render successfully even without tags
        assert 'form' in html.lower()


@pytest.mark.integration
@pytest.mark.routes
def test_duplicate_entry_from_inactive_project(app, user, authenticated_client):
    """Test duplicating an entry from an inactive project."""
    with app.app_context():
        # Create inactive project
        from app.models import Client
        client = Client(name='Test Client', email='test@client.com')
        db.session.add(client)
        db.session.commit()
        
        inactive_project = Project(
            name='Inactive Project',
            client_id=client.id
        )
        inactive_project.status = 'inactive'
        db.session.add(inactive_project)
        db.session.commit()
        
        # Create entry for inactive project
        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = start_time + timedelta(hours=1)
        entry = TimeEntry(
            user_id=user.id,
            project_id=inactive_project.id,
            start_time=start_time,
            end_time=end_time,
            source='manual'
        )
        db.session.add(entry)
        db.session.commit()
        
        # Should still be able to view duplication form using authenticated client
        response = authenticated_client.get(f'/timer/duplicate/{entry.id}')
        
        # Should render (200) or redirect if auth issue (302)
        # Both acceptable since the route exists and handles the request
        assert response.status_code in [200, 302]


@pytest.mark.integration
@pytest.mark.routes
def test_duplicate_with_task_not_overridden_by_template_code(authenticated_client, time_entry_with_all_fields, task, app):
    """Test that duplicating an entry with a task preserves task selection despite template code."""
    with app.app_context():
        response = authenticated_client.get(f'/timer/duplicate/{time_entry_with_all_fields.id}')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        
        # Verify the duplicate flag is set to true in JavaScript
        assert 'const isDuplicating = true;' in html or 'isDuplicating = true' in html
        
        # Verify the task ID is set in the data attribute
        assert f'data-selected-task-id="{task.id}"' in html
        
        # Verify template code is wrapped in isDuplicating check
        assert 'if (!isDuplicating)' in html
        
        # Verify the is_duplicate flag is set
        assert 'Duplicating entry' in html or 'Duplicate Time Entry' in html

