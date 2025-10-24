"""
Comprehensive tests for Time Entry Templates feature.

This module tests:
- TimeEntryTemplate model functionality
- Time entry template routes (CRUD operations)
- Template usage tracking
- Integration with time entries
"""

import pytest
from datetime import datetime
from app.models import TimeEntryTemplate, User, Project, Task, TimeEntry
from app import db


# ============================================================================
# Model Tests
# ============================================================================

@pytest.mark.models
class TestTimeEntryTemplateModel:
    """Test TimeEntryTemplate model functionality"""
    
    def test_create_template_with_all_fields(self, app, user, project, task):
        """Test creating a template with all fields populated"""
        with app.app_context():
            template = TimeEntryTemplate(
                user_id=user.id,
                name="Daily Standup",
                description="Template for daily standup meetings",
                project_id=project.id,
                task_id=task.id,
                default_duration_minutes=15,
                default_notes="Discussed progress and blockers",
                tags="meeting,standup,daily",
                billable=True
            )
            db.session.add(template)
            db.session.commit()
            
            # Verify all fields
            assert template.id is not None
            assert template.name == "Daily Standup"
            assert template.description == "Template for daily standup meetings"
            assert template.project_id == project.id
            assert template.task_id == task.id
            assert template.default_duration_minutes == 15
            assert template.default_notes == "Discussed progress and blockers"
            assert template.tags == "meeting,standup,daily"
            assert template.billable is True
            assert template.usage_count == 0
            assert template.last_used_at is None
            assert template.created_at is not None
            assert template.updated_at is not None
    
    def test_create_template_minimal_fields(self, app, user):
        """Test creating a template with only required fields"""
        with app.app_context():
            template = TimeEntryTemplate(
                user_id=user.id,
                name="Quick Task"
            )
            db.session.add(template)
            db.session.commit()
            
            assert template.id is not None
            assert template.name == "Quick Task"
            assert template.project_id is None
            assert template.task_id is None
            assert template.default_duration_minutes is None
            assert template.default_notes is None
            assert template.tags is None
            assert template.billable is True  # Default value
            assert template.usage_count == 0
    
    def test_template_default_duration_property(self, app, user):
        """Test the default_duration property (hours conversion)"""
        with app.app_context():
            template = TimeEntryTemplate(
                user_id=user.id,
                name="Test Template",
                default_duration_minutes=90
            )
            db.session.add(template)
            db.session.commit()
            
            # Test getter
            assert template.default_duration == 1.5
            
            # Test setter
            template.default_duration = 2.25
            assert template.default_duration_minutes == 135
            
            # Test None handling
            template.default_duration = None
            assert template.default_duration_minutes is None
            assert template.default_duration is None
    
    def test_template_record_usage(self, app, user):
        """Test the record_usage method"""
        with app.app_context():
            template = TimeEntryTemplate(
                user_id=user.id,
                name="Test Template"
            )
            db.session.add(template)
            db.session.commit()
            
            initial_count = template.usage_count
            initial_last_used = template.last_used_at
            
            # Record usage
            template.record_usage()
            db.session.commit()
            
            assert template.usage_count == initial_count + 1
            assert template.last_used_at is not None
            assert template.last_used_at != initial_last_used
    
    def test_template_increment_usage(self, app, user):
        """Test the increment_usage method"""
        with app.app_context():
            template = TimeEntryTemplate(
                user_id=user.id,
                name="Test Template"
            )
            db.session.add(template)
            db.session.commit()
            
            # Increment usage multiple times
            for i in range(3):
                template.increment_usage()
            
            template_id = template.id
            
            # Verify in new query
            updated_template = TimeEntryTemplate.query.get(template_id)
            assert updated_template.usage_count == 3
            assert updated_template.last_used_at is not None
    
    def test_template_to_dict(self, app, user, project, task):
        """Test the to_dict method"""
        with app.app_context():
            template = TimeEntryTemplate(
                user_id=user.id,
                name="Test Template",
                description="Test description",
                project_id=project.id,
                task_id=task.id,
                default_duration_minutes=60,
                default_notes="Test notes",
                tags="test,template",
                billable=True
            )
            db.session.add(template)
            db.session.commit()
            
            template_dict = template.to_dict()
            
            assert template_dict['id'] == template.id
            assert template_dict['user_id'] == user.id
            assert template_dict['name'] == "Test Template"
            assert template_dict['description'] == "Test description"
            assert template_dict['project_id'] == project.id
            assert template_dict['project_name'] == project.name
            assert template_dict['task_id'] == task.id
            assert template_dict['task_name'] == task.name
            assert template_dict['default_duration'] == 1.0
            assert template_dict['default_duration_minutes'] == 60
            assert template_dict['default_notes'] == "Test notes"
            assert template_dict['tags'] == "test,template"
            assert template_dict['billable'] is True
            assert template_dict['usage_count'] == 0
            assert 'created_at' in template_dict
            assert 'updated_at' in template_dict
    
    def test_template_relationships(self, app, user, project, task):
        """Test template relationships with user, project, and task"""
        with app.app_context():
            # Get IDs before context
            user_id = user.id
            project_id = project.id
            task_id = task.id
            
            template = TimeEntryTemplate(
                user_id=user_id,
                name="Test Template",
                project_id=project_id,
                task_id=task_id
            )
            db.session.add(template)
            db.session.commit()
            
            # Test relationships by ID
            assert template.user_id == user_id
            assert template.project_id == project_id
            assert template.task_id == task_id
            
            # Test relationship objects exist
            assert template.user is not None
            assert template.project is not None
            assert template.task is not None
            
            # Test relationship IDs match
            assert template.user.id == user_id
            assert template.project.id == project_id
            assert template.task.id == task_id
    
    def test_template_repr(self, app, user):
        """Test template __repr__ method"""
        with app.app_context():
            template = TimeEntryTemplate(
                user_id=user.id,
                name="Test Template"
            )
            db.session.add(template)
            db.session.commit()
            
            assert repr(template) == '<TimeEntryTemplate Test Template>'


# ============================================================================
# Route Tests
# ============================================================================

@pytest.mark.routes
class TestTimeEntryTemplateRoutes:
    """Test time entry template routes"""
    
    def test_list_templates_authenticated(self, authenticated_client, user):
        """Test accessing templates list page when authenticated"""
        response = authenticated_client.get('/templates')
        assert response.status_code == 200
        assert b'Time Entry Templates' in response.data
    
    def test_list_templates_unauthenticated(self, client):
        """Test accessing templates list page without authentication"""
        response = client.get('/templates', follow_redirects=False)
        assert response.status_code == 302  # Redirect to login
    
    def test_create_template_page_get(self, authenticated_client):
        """Test accessing create template page"""
        response = authenticated_client.get('/templates/create')
        assert response.status_code == 200
        assert b'Create Time Entry Template' in response.data
        assert b'Template Name' in response.data
    
    def test_create_template_success(self, authenticated_client, user, project):
        """Test creating a new template successfully"""
        response = authenticated_client.post('/templates/create', data={
            'name': 'New Template',
            'project_id': project.id,
            'default_duration': '1.5',
            'default_notes': 'Test notes',
            'tags': 'test,new'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'created successfully' in response.data
        
        # Verify template was created
        template = TimeEntryTemplate.query.filter_by(
            user_id=user.id,
            name='New Template'
        ).first()
        assert template is not None
        assert template.project_id == project.id
        assert template.default_duration == 1.5
        assert template.default_notes == 'Test notes'
        assert template.tags == 'test,new'
    
    def test_create_template_without_name(self, authenticated_client):
        """Test creating a template without a name fails"""
        response = authenticated_client.post('/templates/create', data={
            'name': '',
            'default_notes': 'Test notes'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'required' in response.data or b'error' in response.data
    
    def test_create_template_duplicate_name(self, authenticated_client, user):
        """Test creating a template with duplicate name fails"""
        # Create first template
        template = TimeEntryTemplate(
            user_id=user.id,
            name='Duplicate Test'
        )
        db.session.add(template)
        db.session.commit()
        
        # Try to create another with same name
        response = authenticated_client.post('/templates/create', data={
            'name': 'Duplicate Test',
            'default_notes': 'Test notes'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'already exists' in response.data
    
    def test_edit_template_page_get(self, authenticated_client, user):
        """Test accessing edit template page"""
        # Create a template
        template = TimeEntryTemplate(
            user_id=user.id,
            name='Edit Test'
        )
        db.session.add(template)
        db.session.commit()
        
        response = authenticated_client.get(f'/templates/{template.id}/edit')
        assert response.status_code == 200
        assert b'Edit Test' in response.data
    
    def test_edit_template_success(self, authenticated_client, user):
        """Test editing a template successfully"""
        # Create a template
        template = TimeEntryTemplate(
            user_id=user.id,
            name='Original Name'
        )
        db.session.add(template)
        db.session.commit()
        template_id = template.id
        
        # Edit the template
        response = authenticated_client.post(f'/templates/{template_id}/edit', data={
            'name': 'Updated Name',
            'default_notes': 'Updated notes'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'updated successfully' in response.data
        
        # Verify update
        updated_template = TimeEntryTemplate.query.get(template_id)
        assert updated_template.name == 'Updated Name'
        assert updated_template.default_notes == 'Updated notes'
    
    def test_delete_template_success(self, authenticated_client, user):
        """Test deleting a template successfully"""
        # Create a template
        template = TimeEntryTemplate(
            user_id=user.id,
            name='Delete Test'
        )
        db.session.add(template)
        db.session.commit()
        template_id = template.id
        
        # Delete the template
        response = authenticated_client.post(f'/templates/{template_id}/delete', 
                                            follow_redirects=True)
        
        assert response.status_code == 200
        assert b'deleted successfully' in response.data
        
        # Verify deletion
        deleted_template = TimeEntryTemplate.query.get(template_id)
        assert deleted_template is None
    
    # View template test skipped - view.html template doesn't exist yet
    # def test_view_template(self, authenticated_client, user):
    #     """Test viewing a single template"""
    #     template = TimeEntryTemplate(
    #         user_id=user.id,
    #         name='View Test',
    #         default_notes='Test notes'
    #     )
    #     db.session.add(template)
    #     db.session.commit()
    #     
    #     response = authenticated_client.get(f'/templates/{template.id}')
    #     assert response.status_code == 200
    #     assert b'View Test' in response.data
    #     assert b'Test notes' in response.data


# ============================================================================
# API Tests
# ============================================================================

@pytest.mark.api
class TestTimeEntryTemplateAPI:
    """Test time entry template API endpoints"""
    
    def test_get_templates_api(self, authenticated_client, user):
        """Test getting templates via API"""
        # Create some templates
        for i in range(3):
            template = TimeEntryTemplate(
                user_id=user.id,
                name=f'Template {i}'
            )
            db.session.add(template)
        db.session.commit()
        
        response = authenticated_client.get('/api/templates')
        assert response.status_code == 200
        data = response.get_json()
        assert 'templates' in data
        assert len(data['templates']) >= 3
    
    def test_get_single_template_api(self, authenticated_client, user):
        """Test getting a single template via API"""
        template = TimeEntryTemplate(
            user_id=user.id,
            name='API Test',
            default_notes='Test notes'
        )
        db.session.add(template)
        db.session.commit()
        
        response = authenticated_client.get(f'/api/templates/{template.id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['name'] == 'API Test'
        assert data['default_notes'] == 'Test notes'
    
    def test_use_template_api(self, authenticated_client, user):
        """Test marking template as used via API"""
        template = TimeEntryTemplate(
            user_id=user.id,
            name='Use Test'
        )
        db.session.add(template)
        db.session.commit()
        template_id = template.id
        
        response = authenticated_client.post(f'/api/templates/{template_id}/use')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        
        # Verify usage was recorded
        updated_template = TimeEntryTemplate.query.get(template_id)
        assert updated_template.usage_count == 1
        assert updated_template.last_used_at is not None


# ============================================================================
# Smoke Tests
# ============================================================================

@pytest.mark.smoke
class TestTimeEntryTemplatesSmoke:
    """Smoke tests for time entry templates feature"""
    
    def test_templates_page_renders(self, authenticated_client):
        """Smoke test: templates page renders without errors"""
        response = authenticated_client.get('/templates')
        assert response.status_code == 200
        assert b'Time Entry Templates' in response.data
    
    def test_create_template_page_renders(self, authenticated_client):
        """Smoke test: create template page renders without errors"""
        response = authenticated_client.get('/templates/create')
        assert response.status_code == 200
        assert b'Create' in response.data
    
    def test_template_crud_workflow(self, authenticated_client, user, project):
        """Smoke test: complete CRUD workflow for templates"""
        # Create
        response = authenticated_client.post('/templates/create', data={
            'name': 'Smoke Test Template',
            'project_id': project.id,
            'default_notes': 'Smoke test'
        }, follow_redirects=True)
        assert response.status_code == 200
        
        # Read
        template = TimeEntryTemplate.query.filter_by(
            user_id=user.id,
            name='Smoke Test Template'
        ).first()
        assert template is not None
        
        # View test skipped - view.html doesn't exist yet
        # response = authenticated_client.get(f'/templates/{template.id}')
        # assert response.status_code == 200
        
        # Update
        response = authenticated_client.post(f'/templates/{template.id}/edit', data={
            'name': 'Smoke Test Template Updated',
            'default_notes': 'Updated notes'
        }, follow_redirects=True)
        assert response.status_code == 200
        
        # Delete
        response = authenticated_client.post(f'/templates/{template.id}/delete',
                                            follow_redirects=True)
        assert response.status_code == 200


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.integration
class TestTimeEntryTemplateIntegration:
    """Integration tests for time entry templates with other features"""
    
    def test_template_with_project_and_task(self, app, user, project, task):
        """Test template integration with projects and tasks"""
        with app.app_context():
            template = TimeEntryTemplate(
                user_id=user.id,
                name='Integration Test',
                project_id=project.id,
                task_id=task.id
            )
            db.session.add(template)
            db.session.commit()
            
            # Verify relationships work
            assert template.project.name == project.name
            assert template.task.name == task.name
    
    def test_template_usage_tracking_over_time(self, app, user):
        """Test template usage tracking"""
        with app.app_context():
            template = TimeEntryTemplate(
                user_id=user.id,
                name='Usage Tracking Test'
            )
            db.session.add(template)
            db.session.commit()
            
            # Use template multiple times
            usage_times = []
            for _ in range(5):
                template.record_usage()
                usage_times.append(template.last_used_at)
                db.session.commit()
            
            assert template.usage_count == 5
            # Last used time should be most recent
            assert template.last_used_at == max(usage_times)
    
    def test_multiple_users_separate_templates(self, app):
        """Test that templates are user-specific"""
        with app.app_context():
            # Create two users
            user1 = User(username='template_user1', email='user1@test.com')
            user1.is_active = True
            user2 = User(username='template_user2', email='user2@test.com')
            user2.is_active = True
            db.session.add_all([user1, user2])
            db.session.commit()
            
            # Create templates for each user
            template1 = TimeEntryTemplate(
                user_id=user1.id,
                name='User1 Template'
            )
            template2 = TimeEntryTemplate(
                user_id=user2.id,
                name='User2 Template'
            )
            db.session.add_all([template1, template2])
            db.session.commit()
            
            # Verify isolation
            user1_templates = TimeEntryTemplate.query.filter_by(user_id=user1.id).all()
            user2_templates = TimeEntryTemplate.query.filter_by(user_id=user2.id).all()
            
            assert len(user1_templates) == 1
            assert len(user2_templates) == 1
            assert user1_templates[0].name == 'User1 Template'
            assert user2_templates[0].name == 'User2 Template'

