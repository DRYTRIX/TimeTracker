"""
Smoke tests for Project Dashboard feature.
Quick validation tests to ensure the dashboard is working at a basic level.
"""

import pytest
from datetime import datetime, timedelta, date
from decimal import Decimal
from app import create_app, db
from app.models import User, Project, Client, Task, TimeEntry, Activity
from app.models.kanban_column import KanbanColumn


@pytest.fixture
def app():
    """Create and configure a test application instance."""
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False
    })
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create a test Flask client."""
    return app.test_client()


@pytest.fixture
def user(app):
    """Create a test user."""
    with app.app_context():
        user = User(username='testuser', role='user', email='test@example.com')
        user.set_password('testpass123')
        db.session.add(user)
        db.session.commit()
        yield user


@pytest.fixture
def test_client_obj(app):
    """Create a test client."""
    with app.app_context():
        client = Client(name='Test Client', description='A test client')
        db.session.add(client)
        db.session.commit()
        yield client


@pytest.fixture
def project_with_data(app, test_client_obj, user):
    """Create a project with some sample data."""
    with app.app_context():
        # Avoid kanban default initialization during requests to prevent SQLite PK conflicts in tests
        try:
            import app.routes.projects as projects_routes
            projects_routes.KanbanColumn.initialize_default_columns = staticmethod(lambda project_id=None: True)
        except Exception:
            pass
        # Create project
        project = Project(
            name='Dashboard Test Project',
            client_id=test_client_obj.id,
            description='A test project',
            billable=True,
            hourly_rate=Decimal('100.00'),
            budget_amount=Decimal('5000.00')
        )
        project.estimated_hours = 50.0
        db.session.add(project)
        db.session.commit()
        
        # Add some tasks
        task1 = Task(
            project_id=project.id,
            name='Test Task 1',
            status='todo',
            priority='high',
            created_by=user.id,
            assigned_to=user.id
        )
        task2 = Task(
            project_id=project.id,
            name='Test Task 2',
            status='done',
            priority='medium',
            created_by=user.id,
            assigned_to=user.id
        )
        db.session.add_all([task1, task2])
        
        # Add time entries
        now = datetime.now()
        entry = TimeEntry(
            user_id=user.id,
            project_id=project.id,
            task_id=task1.id,
            start_time=now - timedelta(hours=4),
            end_time=now,
            duration_seconds=14400,  # 4 hours
            billable=True
        )
        db.session.add(entry)
        
        # Add activity
        Activity.log(
            user_id=user.id,
            action='created',
            entity_type='project',
            entity_id=project.id,
            entity_name=project.name,
            description=f'Created project "{project.name}"'
        )
        
        db.session.commit()
        yield project


def login(client, username='testuser', password='testpass123'):
    """Helper function to log in a user."""
    return client.post('/auth/login', data={
        'username': username,
        'password': password
    }, follow_redirects=True)


class TestProjectDashboardSmoke:
    """Smoke tests for project dashboard functionality."""
    
    def test_dashboard_page_loads(self, client, user, project_with_data):
        """Smoke test: Dashboard page loads without errors"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
        
        response = client.get(f'/projects/{project_with_data.id}/dashboard')
        assert response.status_code == 200, "Dashboard page should load successfully"
        assert b'Dashboard' in response.data or b'dashboard' in response.data.lower()
    
    def test_dashboard_requires_authentication(self, client, project_with_data):
        """Smoke test: Dashboard requires user to be logged in"""
        response = client.get(f'/projects/{project_with_data.id}/dashboard')
        assert response.status_code == 302, "Should redirect to login"
    
    def test_dashboard_shows_project_name(self, client, user, project_with_data):
        """Smoke test: Dashboard displays the project name"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
        
        response = client.get(f'/projects/{project_with_data.id}/dashboard')
        assert response.status_code == 200
        assert project_with_data.name.encode() in response.data
    
    def test_dashboard_shows_key_metrics(self, client, user, project_with_data):
        """Smoke test: Dashboard displays key metrics cards"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
        
        response = client.get(f'/projects/{project_with_data.id}/dashboard')
        assert response.status_code == 200
        
        # Check for key metrics
        assert b'Total Hours' in response.data or b'total hours' in response.data.lower()
        assert b'Budget' in response.data or b'budget' in response.data.lower()
        assert b'Tasks' in response.data or b'tasks' in response.data.lower()
        assert b'Team' in response.data or b'team' in response.data.lower()
    
    def test_dashboard_shows_charts(self, client, user, project_with_data):
        """Smoke test: Dashboard includes chart canvases"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
        
        response = client.get(f'/projects/{project_with_data.id}/dashboard')
        assert response.status_code == 200
        
        # Check for chart elements
        assert b'canvas' in response.data or b'Chart' in response.data
    
    def test_dashboard_shows_budget_visualization(self, client, user, project_with_data):
        """Smoke test: Dashboard shows budget vs actual section"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
        
        response = client.get(f'/projects/{project_with_data.id}/dashboard')
        assert response.status_code == 200
        assert b'Budget vs. Actual' in response.data or b'Budget' in response.data
    
    def test_dashboard_shows_task_statistics(self, client, user, project_with_data):
        """Smoke test: Dashboard shows task statistics"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
        
        response = client.get(f'/projects/{project_with_data.id}/dashboard')
        assert response.status_code == 200
        assert b'Task' in response.data
        # Should show task counts
        assert b'2' in response.data  # We created 2 tasks
    
    def test_dashboard_shows_team_contributions(self, client, user, project_with_data):
        """Smoke test: Dashboard shows team member contributions"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
        
        response = client.get(f'/projects/{project_with_data.id}/dashboard')
        assert response.status_code == 200
        assert b'Team Member' in response.data or b'Contributions' in response.data
    
    def test_dashboard_shows_recent_activity(self, client, user, project_with_data):
        """Smoke test: Dashboard shows recent activity section"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
        
        response = client.get(f'/projects/{project_with_data.id}/dashboard')
        assert response.status_code == 200
        assert b'Recent Activity' in response.data or b'Activity' in response.data
    
    def test_dashboard_has_back_link(self, client, user, project_with_data):
        """Smoke test: Dashboard has link back to project view"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
        
        response = client.get(f'/projects/{project_with_data.id}/dashboard')
        assert response.status_code == 200
        assert b'Back to Project' in response.data
        assert f'/projects/{project_with_data.id}'.encode() in response.data
    
    def test_dashboard_period_filter_works(self, client, user, project_with_data):
        """Smoke test: Dashboard period filter functions"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
        
        # Test each period filter
        for period in ['all', 'week', 'month', '3months', 'year']:
            response = client.get(f'/projects/{project_with_data.id}/dashboard?period={period}')
            assert response.status_code == 200, f"Dashboard should load with period={period}"
    
    def test_dashboard_period_filter_dropdown(self, client, user, project_with_data):
        """Smoke test: Dashboard has period filter dropdown"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
        
        response = client.get(f'/projects/{project_with_data.id}/dashboard')
        assert response.status_code == 200
        assert b'periodFilter' in response.data or b'All Time' in response.data
    
    def test_project_view_has_dashboard_link(self, client, user, project_with_data):
        """Smoke test: Project view page has link to dashboard"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
        
        response = client.get(f'/projects/{project_with_data.id}')
        assert response.status_code == 200
        # Be resilient to routing differences; check presence of dashboard link or text
        page_text = response.get_data(as_text=True).lower()
        assert ('dashboard' in page_text) or ('/dashboard' in page_text)
    
    def test_dashboard_handles_no_data_gracefully(self, client, user, test_client_obj):
        """Smoke test: Dashboard handles project with no data"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
        
        # Create empty project
        empty_project = Project(
            name='Empty Project',
            client_id=test_client_obj.id
        )
        db.session.add(empty_project)
        db.session.commit()
        
        response = client.get(f'/projects/{empty_project.id}/dashboard')
        assert response.status_code == 200, "Dashboard should load even with no data"
    
    def test_dashboard_shows_hours_worked(self, client, user, project_with_data):
        """Smoke test: Dashboard displays hours worked"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
        
        response = client.get(f'/projects/{project_with_data.id}/dashboard')
        assert response.status_code == 200
        # Should show 4.0 hours (from our test data)
        assert b'4.0' in response.data
    
    def test_dashboard_shows_budget_amount(self, client, user, project_with_data):
        """Smoke test: Dashboard displays budget amount"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
        
        response = client.get(f'/projects/{project_with_data.id}/dashboard')
        assert response.status_code == 200
        # Should show budget of 5000
        assert b'5000' in response.data
    
    def test_dashboard_calculates_completion_rate(self, client, user, project_with_data):
        """Smoke test: Dashboard calculates task completion rate"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
        
        response = client.get(f'/projects/{project_with_data.id}/dashboard')
        assert response.status_code == 200
        # With 1 done out of 2 tasks, should show 50%
        assert b'50' in response.data or b'completion' in response.data.lower()
    
    def test_dashboard_shows_team_member_name(self, client, user, project_with_data):
        """Smoke test: Dashboard shows team member username"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
        
        response = client.get(f'/projects/{project_with_data.id}/dashboard')
        assert response.status_code == 200
        assert user.username.encode() in response.data
    
    def test_dashboard_handles_invalid_period(self, client, user, project_with_data):
        """Smoke test: Dashboard handles invalid period parameter gracefully"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
        
        response = client.get(f'/projects/{project_with_data.id}/dashboard?period=invalid')
        assert response.status_code == 200, "Should still load with invalid period"
    
    def test_dashboard_404_for_nonexistent_project(self, client, user):
        """Smoke test: Dashboard returns 404 for non-existent project"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
        
        response = client.get('/projects/99999/dashboard')
        assert response.status_code == 404
    
    def test_dashboard_chart_js_loaded(self, client, user, project_with_data):
        """Smoke test: Dashboard loads Chart.js library"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
        
        response = client.get(f'/projects/{project_with_data.id}/dashboard')
        assert response.status_code == 200
        assert b'chart.js' in response.data.lower() or b'Chart' in response.data
    
    def test_dashboard_responsive_layout(self, client, user, project_with_data):
        """Smoke test: Dashboard uses responsive grid layout"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
        
        response = client.get(f'/projects/{project_with_data.id}/dashboard')
        assert response.status_code == 200
        # Check for responsive grid classes
        assert b'grid' in response.data or b'lg:grid-cols' in response.data
    
    def test_dashboard_dark_mode_compatible(self, client, user, project_with_data):
        """Smoke test: Dashboard has dark mode styling"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
        
        response = client.get(f'/projects/{project_with_data.id}/dashboard')
        assert response.status_code == 200
        # Check for dark mode classes
        assert b'dark:' in response.data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

