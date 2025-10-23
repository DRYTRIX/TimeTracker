"""Tests for project inactive status functionality"""
import pytest
from app import create_app, db
from app.models import Project, Client, User


@pytest.fixture
def app():
    """Create application for testing"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def admin_user(app):
    """Create admin user for testing"""
    with app.app_context():
        user = User(username='admin', role='admin')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def test_client_obj(app):
    """Create test client for projects"""
    with app.app_context():
        client = Client(name='Test Client')
        db.session.add(client)
        db.session.commit()
        return client


@pytest.fixture
def test_project(app, test_client_obj):
    """Create test project"""
    with app.app_context():
        project = Project(name='Test Project', client_id=test_client_obj.id)
        db.session.add(project)
        db.session.commit()
        return project


class TestProjectInactiveStatus:
    """Test project inactive status functionality"""
    
    def test_project_default_status(self, app, test_client_obj):
        """Test that new projects have active status by default"""
        with app.app_context():
            project = Project(name='New Project', client_id=test_client_obj.id)
            db.session.add(project)
            db.session.commit()
            
            assert project.status == 'active'
            assert project.is_active is True
    
    def test_project_deactivate(self, app, test_project):
        """Test deactivating a project"""
        with app.app_context():
            project = Project.query.get(test_project.id)
            project.deactivate()
            
            assert project.status == 'inactive'
            assert project.is_active is False
    
    def test_project_activate_from_inactive(self, app, test_project):
        """Test activating an inactive project"""
        with app.app_context():
            project = Project.query.get(test_project.id)
            project.deactivate()
            assert project.status == 'inactive'
            
            project.activate()
            assert project.status == 'active'
            assert project.is_active is True
    
    def test_project_archive_from_inactive(self, app, test_project):
        """Test archiving an inactive project"""
        with app.app_context():
            project = Project.query.get(test_project.id)
            project.deactivate()
            assert project.status == 'inactive'
            
            project.archive()
            assert project.status == 'archived'
    
    def test_project_unarchive_to_active(self, app, test_project):
        """Test unarchiving a project returns it to active"""
        with app.app_context():
            project = Project.query.get(test_project.id)
            project.archive()
            assert project.status == 'archived'
            
            project.unarchive()
            assert project.status == 'active'
    
    def test_project_status_transitions(self, app, test_project):
        """Test complete status transition cycle"""
        with app.app_context():
            project = Project.query.get(test_project.id)
            
            # Start active
            assert project.status == 'active'
            
            # Move to inactive
            project.deactivate()
            assert project.status == 'inactive'
            
            # Move back to active
            project.activate()
            assert project.status == 'active'
            
            # Move to archived
            project.archive()
            assert project.status == 'archived'
            
            # Move back to active via unarchive
            project.unarchive()
            assert project.status == 'active'


class TestProjectInactiveRoutes:
    """Test project inactive status routes"""
    
    def login(self, client, username='admin', password='password'):
        """Helper to log in"""
        return client.post('/auth/login', data={
            'username': username,
            'password': password
        }, follow_redirects=True)
    
    def test_deactivate_project_route(self, client, app, admin_user, test_project):
        """Test deactivating a project via route"""
        with client:
            self.login(client)
            
            with app.app_context():
                project_id = test_project.id
                
            response = client.post(f'/projects/{project_id}/deactivate', 
                                   follow_redirects=True)
            
            assert response.status_code == 200
            
            with app.app_context():
                project = Project.query.get(project_id)
                assert project.status == 'inactive'
    
    def test_activate_project_route(self, client, app, admin_user, test_project):
        """Test activating a project via route"""
        with client:
            self.login(client)
            
            with app.app_context():
                project = Project.query.get(test_project.id)
                project.deactivate()
                project_id = project.id
                
            response = client.post(f'/projects/{project_id}/activate',
                                   follow_redirects=True)
            
            assert response.status_code == 200
            
            with app.app_context():
                project = Project.query.get(project_id)
                assert project.status == 'active'
    
    def test_filter_inactive_projects(self, client, app, admin_user, test_client_obj):
        """Test filtering projects by inactive status"""
        with client:
            self.login(client)
            
            # Create multiple projects with different statuses
            with app.app_context():
                active_project = Project(name='Active Project', client_id=test_client_obj.id)
                inactive_project = Project(name='Inactive Project', client_id=test_client_obj.id)
                archived_project = Project(name='Archived Project', client_id=test_client_obj.id)
                
                db.session.add_all([active_project, inactive_project, archived_project])
                db.session.commit()
                
                inactive_project.deactivate()
                archived_project.archive()
            
            # Test filter for inactive projects
            response = client.get('/projects?status=inactive')
            assert response.status_code == 200
            assert b'Inactive Project' in response.data
            assert b'Active Project' not in response.data
            assert b'Archived Project' not in response.data


class TestTaskDeletion:
    """Test individual task deletion"""
    
    def login(self, client, username='admin', password='password'):
        """Helper to log in"""
        return client.post('/auth/login', data={
            'username': username,
            'password': password
        }, follow_redirects=True)
    
    def test_task_list_has_delete_buttons(self, client, app, admin_user, test_project):
        """Test that task list shows individual delete buttons"""
        with client:
            self.login(client)
            
            with app.app_context():
                from app.models import Task
                task = Task(
                    name='Test Task',
                    project_id=test_project.id,
                    created_by=admin_user.id
                )
                db.session.add(task)
                db.session.commit()
            
            response = client.get('/tasks')
            assert response.status_code == 200
            # Should have delete button, not bulk checkboxes
            assert b'confirmDeleteTask' in response.data
            # Should not have bulk delete
            assert b'bulkDeleteBtn' not in response.data
            assert b'selectAll' not in response.data

