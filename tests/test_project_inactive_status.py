"""Tests for project inactive status functionality"""
import pytest
from app.models import Project


class TestProjectInactiveStatus:
    """Test project inactive status functionality"""
    
    @pytest.mark.models
    def test_project_default_status(self, app, test_client):
        """Test that new projects have active status by default"""
        from app import db
        
        project = Project(name='New Project', client_id=test_client.id)
        db.session.add(project)
        db.session.commit()
        
        assert project.status == 'active'
        assert project.is_active is True
    
    @pytest.mark.models
    def test_project_deactivate(self, app, project):
        """Test deactivating a project"""
        from app import db
        
        project.deactivate()
        db.session.commit()
        
        assert project.status == 'inactive'
        assert project.is_active is False
    
    @pytest.mark.models
    def test_project_activate_from_inactive(self, app, project):
        """Test activating an inactive project"""
        from app import db
        
        project.deactivate()
        db.session.commit()
        assert project.status == 'inactive'
        
        project.activate()
        db.session.commit()
        assert project.status == 'active'
        assert project.is_active is True
    
    @pytest.mark.models
    def test_project_archive_from_inactive(self, app, project):
        """Test archiving an inactive project"""
        from app import db
        
        project.deactivate()
        db.session.commit()
        assert project.status == 'inactive'
        
        project.archive()
        db.session.commit()
        assert project.status == 'archived'
    
    @pytest.mark.models
    def test_project_unarchive_to_active(self, app, project):
        """Test unarchiving a project returns it to active"""
        from app import db
        
        project.archive()
        db.session.commit()
        assert project.status == 'archived'
        
        project.unarchive()
        db.session.commit()
        assert project.status == 'active'
    
    @pytest.mark.models
    def test_project_status_transitions(self, app, project):
        """Test complete status transition cycle"""
        from app import db
        
        # Start active
        assert project.status == 'active'
        
        # Move to inactive
        project.deactivate()
        db.session.commit()
        assert project.status == 'inactive'
        
        # Move back to active
        project.activate()
        db.session.commit()
        assert project.status == 'active'
        
        # Move to archived
        project.archive()
        db.session.commit()
        assert project.status == 'archived'
        
        # Move back to active via unarchive
        project.unarchive()
        db.session.commit()
        assert project.status == 'active'


class TestProjectInactiveRoutes:
    """Test project inactive status routes"""
    
    @pytest.mark.routes
    def test_deactivate_project_route(self, admin_authenticated_client, app, project):
        """Test deactivating a project via route"""
        from app import db
        
        project_id = project.id
        
        response = admin_authenticated_client.post(f'/projects/{project_id}/deactivate', 
                               follow_redirects=True)
        
        assert response.status_code == 200
        
        db.session.refresh(project)
        assert project.status == 'inactive'
    
    @pytest.mark.routes
    def test_activate_project_route(self, admin_authenticated_client, app, project):
        """Test activating a project via route"""
        from app import db
        
        project.deactivate()
        db.session.commit()
        project_id = project.id
        
        response = admin_authenticated_client.post(f'/projects/{project_id}/activate',
                               follow_redirects=True)
        
        assert response.status_code == 200
        
        db.session.refresh(project)
        assert project.status == 'active'
    
    @pytest.mark.routes
    def test_filter_inactive_projects(self, admin_authenticated_client, app, test_client):
        """Test filtering projects by inactive status"""
        from app import db
        
        # Create multiple projects with different statuses
        active_project = Project(name='Active Project', client_id=test_client.id)
        inactive_project = Project(name='Inactive Project', client_id=test_client.id)
        archived_project = Project(name='Archived Project', client_id=test_client.id)
        
        db.session.add_all([active_project, inactive_project, archived_project])
        db.session.commit()
        
        inactive_project.deactivate()
        archived_project.archive()
        db.session.commit()
        
        # Test filter for inactive projects
        response = admin_authenticated_client.get('/projects?status=inactive')
        assert response.status_code == 200
        assert b'Inactive Project' in response.data
        assert b'Active Project' not in response.data
        assert b'Archived Project' not in response.data


class TestTaskDeletion:
    """Test individual task deletion"""
    
    @pytest.mark.routes
    def test_task_list_has_delete_buttons(self, admin_authenticated_client, app, project, admin_user):
        """Test that task list shows individual delete buttons"""
        from app.models import Task
        from app import db
        
        task = Task(
            name='Test Task',
            project_id=project.id,
            created_by=admin_user.id
        )
        db.session.add(task)
        db.session.commit()
        
        response = admin_authenticated_client.get('/tasks')
        assert response.status_code == 200
        # Should have delete button, not bulk checkboxes
        assert b'confirmDeleteTask' in response.data
        # Should not have bulk delete
        assert b'bulkDeleteBtn' not in response.data
        assert b'selectAll' not in response.data

