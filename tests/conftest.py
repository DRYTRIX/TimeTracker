"""
Pytest configuration and shared fixtures for TimeTracker tests.
This file contains common fixtures and test configuration used across all test modules.
"""

import pytest
import os
import tempfile
from datetime import datetime, timedelta
from decimal import Decimal

from app import create_app, db
from app.models import (
    User, Project, TimeEntry, Client, Settings, 
    Invoice, InvoiceItem, Task
)


# ============================================================================
# Application Fixtures
# ============================================================================

@pytest.fixture(scope='session')
def app_config():
    """Base test configuration."""
    return {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key-do-not-use-in-production',
        'SERVER_NAME': 'localhost:5000',
        'APPLICATION_ROOT': '/',
        'PREFERRED_URL_SCHEME': 'http',
    }


@pytest.fixture(scope='function')
def app(app_config):
    """Create application for testing with function scope."""
    app = create_app(app_config)
    
    with app.app_context():
        db.create_all()
        
        # Create default settings
        settings = Settings()
        db.session.add(settings)
        db.session.commit()
        
        yield app
        
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """Create test CLI runner."""
    return app.test_cli_runner()


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope='function')
def db_session(app):
    """Create a database session for tests."""
    with app.app_context():
        yield db.session


# ============================================================================
# User Fixtures
# ============================================================================

@pytest.fixture
def user(app):
    """Create a regular test user."""
    user = User(
        username='testuser',
        role='user',
        email='testuser@example.com'
    )
    user.is_active = True  # Set after creation
    db.session.add(user)
    db.session.commit()
    
    # Refresh to ensure all relationships are loaded
    db.session.refresh(user)
    return user


@pytest.fixture
def admin_user(app):
    """Create an admin test user."""
    admin = User(
        username='admin',
        role='admin',
        email='admin@example.com'
    )
    admin.is_active = True  # Set after creation
    db.session.add(admin)
    db.session.commit()
    
    db.session.refresh(admin)
    return admin


@pytest.fixture
def multiple_users(app):
    """Create multiple test users."""
    users = []
    for i in range(1, 4):
        user = User(username=f'user{i}', role='user', email=f'user{i}@example.com')
        user.is_active = True  # Set after creation
        users.append(user)
    db.session.add_all(users)
    db.session.commit()
    
    for user in users:
        db.session.refresh(user)
    
    return users


# ============================================================================
# Client Fixtures
# ============================================================================

@pytest.fixture
def test_client(app, user):
    """Create a test client (business client, not test client)."""
    client = Client(
        name='Test Client Corp',
        description='Test client for integration tests',
        contact_person='John Doe',
        email='john@testclient.com',
        phone='+1 (555) 123-4567',
        address='123 Test Street, Test City, TC 12345',
        default_hourly_rate=Decimal('85.00')
    )
    client.status = 'active'  # Set after creation
    db.session.add(client)
    db.session.commit()
    
    db.session.refresh(client)
    return client


@pytest.fixture
def multiple_clients(app, user):
    """Create multiple test clients."""
    clients = []
    for i in range(1, 4):
        client = Client(
            name=f'Client {i}',
            email=f'client{i}@example.com',
            default_hourly_rate=Decimal('75.00') + Decimal(i * 10)
        )
        client.status = 'active'  # Set after creation
        clients.append(client)
    db.session.add_all(clients)
    db.session.commit()
    
    for client in clients:
        db.session.refresh(client)
    
    return clients


# ============================================================================
# Project Fixtures
# ============================================================================

@pytest.fixture
def project(app, test_client):
    """Create a test project."""
    project = Project(
        name='Test Project',
        client_id=test_client.id,
        description='Test project description',
        billable=True,
        hourly_rate=Decimal('75.00')
    )
    project.status = 'active'  # Set after creation
    db.session.add(project)
    db.session.commit()
    
    db.session.refresh(project)
    return project


@pytest.fixture
def multiple_projects(app, test_client):
    """Create multiple test projects."""
    projects = []
    for i in range(1, 4):
        project = Project(
            name=f'Project {i}',
            client_id=test_client.id,
            description=f'Test project {i}',
            billable=True,
            hourly_rate=Decimal('75.00')
        )
        project.status = 'active'  # Set after creation
        projects.append(project)
    db.session.add_all(projects)
    db.session.commit()
    
    for proj in projects:
        db.session.refresh(proj)
    
    return projects


# ============================================================================
# Time Entry Fixtures
# ============================================================================

@pytest.fixture
def time_entry(app, user, project):
    """Create a single time entry."""
    start_time = datetime.utcnow() - timedelta(hours=2)
    end_time = datetime.utcnow()
    
    entry = TimeEntry(
        user_id=user.id,
        project_id=project.id,
        start_time=start_time,
        end_time=end_time,
        notes='Test time entry',
        tags='test,development',
        source='manual',
        billable=True
    )
    db.session.add(entry)
    db.session.commit()
    
    db.session.refresh(entry)
    return entry


@pytest.fixture
def multiple_time_entries(app, user, project):
    """Create multiple time entries."""
    base_time = datetime.utcnow() - timedelta(days=7)
    entries = []
    
    for i in range(5):
        start = base_time + timedelta(days=i, hours=9)
        end = base_time + timedelta(days=i, hours=17)
        
        entry = TimeEntry(
            user_id=user.id,
            project_id=project.id,
            start_time=start,
            end_time=end,
            notes=f'Work day {i+1}',
            tags='development,testing',
            source='manual',
            billable=True
        )
        entries.append(entry)
    
    db.session.add_all(entries)
    db.session.commit()
    
    for entry in entries:
        db.session.refresh(entry)
    
    return entries


@pytest.fixture
def active_timer(app, user, project):
    """Create an active timer (time entry without end time)."""
    timer = TimeEntry(
        user_id=user.id,
        project_id=project.id,
        start_time=datetime.utcnow(),
        notes='Active timer',
        source='auto',
        billable=True
    )
    db.session.add(timer)
    db.session.commit()
    
    db.session.refresh(timer)
    return timer


# ============================================================================
# Task Fixtures
# ============================================================================

@pytest.fixture
def task(app, project, user):
    """Create a test task."""
    task = Task(
        name='Test Task',
        description='Test task description',
        project_id=project.id,
        priority='medium',
        created_by=user.id
    )
    task.status = 'todo'  # Set after creation
    db.session.add(task)
    db.session.commit()
    
    db.session.refresh(task)
    return task


# ============================================================================
# Invoice Fixtures
# ============================================================================

@pytest.fixture
def invoice(app, user, project, test_client):
    """Create a test invoice."""
    from datetime import date
    
    invoice = Invoice(
        invoice_number=Invoice.generate_invoice_number(),
        project_id=project.id,
        client_id=test_client.id,
        client_name=test_client.name,
        due_date=date.today() + timedelta(days=30),
        created_by=user.id,
        tax_rate=Decimal('20.00')
    )
    invoice.status = 'draft'  # Set after creation
    db.session.add(invoice)
    db.session.commit()
    
    db.session.refresh(invoice)
    return invoice


@pytest.fixture
def invoice_with_items(app, invoice):
    """Create an invoice with items."""
    items = [
        InvoiceItem(
            invoice_id=invoice.id,
            description='Development work',
            quantity=Decimal('10.00'),
            unit_price=Decimal('75.00')
        ),
        InvoiceItem(
            invoice_id=invoice.id,
            description='Testing work',
            quantity=Decimal('5.00'),
            unit_price=Decimal('60.00')
        )
    ]
    
    db.session.add_all(items)
    db.session.commit()
    
    invoice.calculate_totals()
    db.session.commit()
    
    db.session.refresh(invoice)
    for item in items:
        db.session.refresh(item)
    
    return invoice, items


# ============================================================================
# Authentication Fixtures
# ============================================================================

@pytest.fixture
def authenticated_client(client, user):
    """Create an authenticated test client."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True
    return client


@pytest.fixture
def admin_authenticated_client(client, admin_user):
    """Create an authenticated admin test client."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user.id)
        sess['_fresh'] = True
    return client


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture
def temp_file():
    """Create a temporary file for testing."""
    fd, path = tempfile.mkstemp()
    yield path
    os.close(fd)
    os.unlink(path)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    dirpath = tempfile.mkdtemp()
    yield dirpath
    import shutil
    shutil.rmtree(dirpath)


# ============================================================================
# Alias Fixtures (for compatibility with different test naming conventions)
# ============================================================================

@pytest.fixture
def test_client_obj(test_client):
    """Alias for test_client to avoid naming conflicts"""
    return test_client


@pytest.fixture
def auth_user(user):
    """Alias for user fixture"""
    return user


@pytest.fixture
def test_project(project):
    """Alias for project fixture"""
    return project


@pytest.fixture
def test_task(task):
    """Alias for task fixture"""
    return task


# ============================================================================
# Installation Config Fixture
# ============================================================================

@pytest.fixture
def installation_config(temp_dir):
    """Create a temporary installation config for testing"""
    from app.utils.installation import InstallationConfig
    
    # Override the config directory to use temp directory
    original_config_dir = InstallationConfig.CONFIG_DIR
    InstallationConfig.CONFIG_DIR = temp_dir
    
    # Create the config instance
    config = InstallationConfig()
    
    yield config
    
    # Restore original config directory
    InstallationConfig.CONFIG_DIR = original_config_dir


# ============================================================================
# Pytest Markers
# ============================================================================

def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "smoke: Quick smoke tests")
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "api: API endpoint tests")
    config.addinivalue_line("markers", "database: Database-related tests")
    config.addinivalue_line("markers", "models: Model tests")
    config.addinivalue_line("markers", "routes: Route tests")
    config.addinivalue_line("markers", "security: Security tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "slow: Slow running tests")

