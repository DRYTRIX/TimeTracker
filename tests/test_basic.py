import pytest
from app import db
from app.models import User, Project, TimeEntry, Settings, Client
from factories import TimeEntryFactory
from datetime import datetime, timedelta
from decimal import Decimal

# Note: All fixtures are now imported from conftest.py
# No duplicate fixtures needed here

@pytest.mark.smoke
@pytest.mark.unit
def test_app_creation(app):
    """Test that the app can be created"""
    assert app is not None
    assert app.config['TESTING'] is True

@pytest.mark.unit
@pytest.mark.database
def test_database_creation(app):
    """Test that database tables can be created"""
    with app.app_context():
        # Check that tables exist using inspect
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        assert 'users' in tables
        assert 'projects' in tables
        assert 'time_entries' in tables
        assert 'settings' in tables

@pytest.mark.unit
@pytest.mark.models
def test_user_creation(app):
    """Test user creation"""
    with app.app_context():
        user = User(username='testuser', role='user')
        db.session.add(user)
        db.session.commit()
        
        assert user.id is not None
        assert user.username == 'testuser'
        assert user.role == 'user'
        assert user.is_admin is False

@pytest.mark.unit
@pytest.mark.models
def test_admin_user(app):
    """Test admin user properties"""
    with app.app_context():
        admin = User(username='admin', role='admin')
        db.session.add(admin)
        db.session.commit()
        
        assert admin.is_admin is True

@pytest.mark.unit
@pytest.mark.models
def test_project_creation(app):
    """Test project creation"""
    with app.app_context():
        # Create a client first
        client = Client(name='Test Client', default_hourly_rate=Decimal('50.00'))
        db.session.add(client)
        db.session.commit()
        
        project = Project(
            name='Test Project',
            client_id=client.id,
            description='Test description',
            billable=True,
            hourly_rate=Decimal('50.00')
        )
        db.session.add(project)
        db.session.commit()
        
        assert project.id is not None
        assert project.name == 'Test Project'
        assert project.client_id == client.id
        assert project.billable is True
        assert float(project.hourly_rate) == 50.00

@pytest.mark.unit
@pytest.mark.models
def test_time_entry_creation(app, user, project):
    """Test time entry creation"""
    start_time = datetime.utcnow()
    end_time = start_time + timedelta(hours=2)
    
    entry = TimeEntryFactory(
        user_id=user.id,
        project_id=project.id,
        start_time=start_time,
        end_time=end_time,
        notes='Test entry',
        tags='test,work',
        source='manual'
    )
    db.session.commit()
    
    assert entry.id is not None
    assert entry.duration_hours == 2.0
    assert entry.duration_formatted == '02:00:00'
    assert entry.tag_list == ['test', 'work']

@pytest.mark.unit
@pytest.mark.models
def test_active_timer(app, user, project):
    """Test active timer functionality"""
    # Create active timer
    timer = TimeEntryFactory(
        user_id=user.id,
        project_id=project.id,
        start_time=datetime.utcnow(),
        source='auto',
        end_time=None
    )
    db.session.commit()
    
    assert timer.is_active is True
    assert timer.end_time is None
    
    # Stop timer
    timer.stop_timer()
    db.session.commit()
    assert timer.is_active is False
    assert timer.end_time is not None
    assert timer.duration_seconds > 0

@pytest.mark.unit
@pytest.mark.models
def test_user_active_timer_property(app, user, project):
    """Test user active timer property"""
    # Refresh user to check initial state
    db.session.refresh(user)
    
    # Create active timer
    timer = TimeEntryFactory(
        user_id=user.id,
        project_id=project.id,
        start_time=datetime.utcnow(),
        source='auto',
        end_time=None
    )
    db.session.commit()
    
    # Refresh user to load relationships
    db.session.expire(user)
    db.session.refresh(user)
    
    # Check active timer
    assert user.active_timer is not None
    assert user.active_timer.id == timer.id

@pytest.mark.integration
@pytest.mark.models
def test_project_totals(app, user, project):
    """Test project total calculations"""
    # Create time entries
    start_time = datetime.utcnow()
    entry1 = TimeEntryFactory(
        user_id=user.id,
        project_id=project.id,
        start_time=start_time,
        end_time=start_time + timedelta(hours=2),
        source='manual',
        billable=True
    )
    entry2 = TimeEntryFactory(
        user_id=user.id,
        project_id=project.id,
        start_time=start_time + timedelta(hours=3),
        end_time=start_time + timedelta(hours=5),
        source='manual',
        billable=True
    )
    db.session.commit()
    
    # Refresh project to load relationships
    db.session.expire(project)
    db.session.refresh(project)
    
    # Check totals
    assert project.total_hours == 4.0
    assert project.total_billable_hours == 4.0
    expected_cost = 4.0 * float(project.hourly_rate)
    assert float(project.estimated_cost) == expected_cost

@pytest.mark.unit
@pytest.mark.models
def test_settings_singleton(app):
    """Test settings singleton pattern"""
    with app.app_context():
        # Get settings (should create if not exists)
        settings1 = Settings.get_settings()
        settings2 = Settings.get_settings()
        
        assert settings1.id == settings2.id
        assert settings1 is settings2

@pytest.mark.smoke
@pytest.mark.routes
def test_health_check(client):
    """Test health check endpoint"""
    response = client.get('/_health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'

@pytest.mark.smoke
@pytest.mark.routes
def test_login_page(client):
    """Test login page accessibility"""
    response = client.get('/login')
    assert response.status_code == 200

@pytest.mark.unit
@pytest.mark.routes
def test_protected_route_redirect(client):
    """Test that protected routes redirect to login"""
    response = client.get('/dashboard', follow_redirects=False)
    assert response.status_code == 302
    assert '/login' in response.location

@pytest.mark.smoke
@pytest.mark.unit
def test_testing_config_respects_database_url():
    """Test that TestingConfig respects DATABASE_URL environment variable
    
    This test verifies the fix for GitHub Actions migration validation where
    DATABASE_URL is set to PostgreSQL but TestingConfig was hardcoded to SQLite.
    
    Note: This test runs with whatever DATABASE_URL is currently set in the environment.
    In CI/CD with DATABASE_URL set to PostgreSQL, it will use PostgreSQL.
    Locally without DATABASE_URL, it will use SQLite.
    """
    import os
    from app.config import TestingConfig
    
    config = TestingConfig()
    
    # Verify that the config uses the DATABASE_URL if set, otherwise defaults to SQLite
    if 'DATABASE_URL' in os.environ:
        # In CI/CD or when DATABASE_URL is explicitly set
        assert config.SQLALCHEMY_DATABASE_URI == os.environ['DATABASE_URL']
    else:
        # Local development/testing without DATABASE_URL
        assert config.SQLALCHEMY_DATABASE_URI == 'sqlite:///:memory:'