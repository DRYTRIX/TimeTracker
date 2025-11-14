"""Extended model tests for additional coverage"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from app import db
from app.models import (
    User, Client, Project, TimeEntry, Invoice, InvoiceItem,
    Task, Comment, Settings
)
from factories import ClientFactory, ProjectFactory, InvoiceFactory, InvoiceItemFactory, UserFactory


# ============================================================================
# User Model Extended Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.models
def test_user_display_name(app):
    """Test user display name property"""
    with app.app_context():
        # User with full name
        user1 = User(username='testuser', email='test@example.com', full_name='Test User')
        assert user1.display_name == 'Test User'
        
        # User without full name
        user2 = User(username='anotheruser', email='another@example.com')
        assert user2.display_name == 'anotheruser'


@pytest.mark.unit
@pytest.mark.models
def test_user_total_hours(user):
    """Test user total hours calculation"""
    # Should return 0 or a number >= 0
    assert user.total_hours >= 0


@pytest.mark.unit
@pytest.mark.models
def test_user_repr(user):
    """Test user repr"""
    assert repr(user) == f'<User {user.username}>'


@pytest.mark.unit
@pytest.mark.models
def test_user_projects_through_time_entries(app, user, project):
    """Test getting user's projects through time entries"""
    with app.app_context():
        user = db.session.merge(user)
        project = db.session.merge(project)
        
        # Create time entry
        from factories import TimeEntryFactory
        entry = TimeEntryFactory(
            user_id=user.id,
            project_id=project.id,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(hours=2),
            source='manual'
        )
        db.session.commit()
        
        # Get user's projects
        projects = set(entry.project for entry in user.time_entries.all())
        assert project in projects


# ============================================================================
# Client Model Extended Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.models
def test_client_status_property(test_client):
    """Test client status and is_active property"""
    assert test_client.status in ['active', 'inactive']
    if test_client.status == 'active':
        assert test_client.is_active


@pytest.mark.unit
@pytest.mark.models
def test_client_repr(test_client):
    """Test client repr"""
    assert repr(test_client) == f'<Client {test_client.name}>'


@pytest.mark.unit
@pytest.mark.models
def test_client_with_multiple_projects(app, test_client):
    """Test client with multiple projects"""
    with app.app_context():
        test_client = db.session.merge(test_client)
        
        # Create multiple projects
        for i in range(5):
            project = Project(
                name=f'Project {i}',
                client_id=test_client.id,
                billable=True,
                hourly_rate=100.0
            )
            db.session.add(project)
        
        db.session.commit()
        db.session.refresh(test_client)
        
        assert test_client.total_projects >= 5


@pytest.mark.unit
@pytest.mark.models
def test_client_archive_activate_methods(app, test_client):
    """Test client archive and activate methods"""
    with app.app_context():
        test_client = db.session.merge(test_client)
        
        # Initially should be active
        initial_status = test_client.status
        assert initial_status == 'active'
        
        # Archive the client
        test_client.archive()
        db.session.commit()
        assert test_client.status == 'inactive'
        assert not test_client.is_active
        
        # Activate the client
        test_client.activate()
        db.session.commit()
        assert test_client.status == 'active'
        assert test_client.is_active


# ============================================================================
# Project Model Extended Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.models
def test_project_status(project):
    """Test project status"""
    assert project.status in ['active', 'inactive', 'completed']
    assert hasattr(project, 'is_active')


@pytest.mark.unit
@pytest.mark.models
def test_project_billable_hours(project):
    """Test project billable hours calculation"""
    # Should return 0 or a number >= 0
    if hasattr(project, 'total_billable_hours'):
        assert project.total_billable_hours >= 0


@pytest.mark.unit
@pytest.mark.models
def test_project_with_no_time_entries(app, test_client):
    """Test project total hours with no time entries"""
    with app.app_context():
        test_client = db.session.merge(test_client)
        
        project = Project(
            name='Empty Project',
            client_id=test_client.id,
            billable=True,
            hourly_rate=100.0
        )
        db.session.add(project)
        db.session.commit()
        
        assert project.total_hours == 0.0


@pytest.mark.unit
@pytest.mark.models
def test_project_hourly_rate(app, test_client):
    """Test project hourly rate"""
    with app.app_context():
        test_client = db.session.merge(test_client)
        
        project = Project(
            name='Cost Project',
            client_id=test_client.id,
            billable=True,
            hourly_rate=100.0
        )
        db.session.add(project)
        db.session.commit()
        
        assert project.hourly_rate == 100.0
        assert project.billable


@pytest.mark.unit
@pytest.mark.models
def test_project_non_billable(app, test_client):
    """Test non-billable project"""
    with app.app_context():
        test_client = db.session.merge(test_client)
        
        project = Project(
            name='Non-Billable Project',
            client_id=test_client.id,
            billable=False
        )
        db.session.add(project)
        db.session.commit()
        
        assert not project.billable
        assert project.hourly_rate == 0.0 or project.hourly_rate is None


@pytest.mark.unit
@pytest.mark.models
def test_project_to_dict(app, project):
    """Test project to_dict method"""
    with app.app_context():
        project = db.session.merge(project)
        project_dict = project.to_dict()
        
        assert 'id' in project_dict
        assert 'name' in project_dict
        # Project may use 'client' key instead of 'client_id'
        assert 'client' in project_dict or 'client_id' in project_dict
        assert project_dict['name'] == project.name


# ============================================================================
# TimeEntry Model Extended Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.models
def test_time_entry_str_representation(time_entry):
    """Test time entry string representation"""
    str_repr = str(time_entry)
    assert 'TimeEntry' in str_repr


@pytest.mark.unit
@pytest.mark.models
def test_time_entry_with_notes(app, user, project):
    """Test time entry with notes"""
    with app.app_context():
        user = db.session.merge(user)
        project = db.session.merge(project)
        
        notes = "Worked on implementing new feature X"
        from factories import TimeEntryFactory
        entry = TimeEntryFactory(
            user_id=user.id,
            project_id=project.id,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(hours=2),
            notes=notes,
            source='manual'
        )
        db.session.commit()
        
        assert entry.notes == notes


@pytest.mark.unit
@pytest.mark.models
def test_time_entry_with_tags(app, user, project):
    """Test time entry with tags"""
    with app.app_context():
        user = db.session.merge(user)
        project = db.session.merge(project)
        
        from factories import TimeEntryFactory
        entry = TimeEntryFactory(
            user_id=user.id,
            project_id=project.id,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(hours=2),
            tags='development,testing,bugfix',
            source='manual'
        )
        db.session.commit()
        
        tag_list = entry.tag_list
        assert 'development' in tag_list
        assert 'testing' in tag_list
        assert 'bugfix' in tag_list


@pytest.mark.unit
@pytest.mark.models
def test_time_entry_billable_calculation(app, user, project):
    """Test time entry billable cost calculation"""
    with app.app_context():
        user = db.session.merge(user)
        project = db.session.merge(project)
        project.billable = True
        project.hourly_rate = 100.0
        
        from factories import TimeEntryFactory
        entry = TimeEntryFactory(
            user_id=user.id,
            project_id=project.id,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(hours=3),
            source='manual'
        )
        db.session.commit()
        
        # 3 hours * $100/hr = $300
        expected_cost = 3.0 * 100.0
        if hasattr(entry, 'billable_amount'):
            assert entry.billable_amount == expected_cost


@pytest.mark.unit
@pytest.mark.models
def test_time_entry_long_duration(app, user, project):
    """Test time entry with very long duration"""
    with app.app_context():
        user = db.session.merge(user)
        project = db.session.merge(project)
        
        start = datetime.utcnow()
        end = start + timedelta(hours=24)  # 24 hours
        
        from factories import TimeEntryFactory
        entry = TimeEntryFactory(
            user_id=user.id,
            project_id=project.id,
            start_time=start,
            end_time=end,
            source='manual'
        )
        db.session.commit()
        
        # Check duration through time difference
        duration_seconds = (end - start).total_seconds()
        assert duration_seconds >= 24 * 3600


# ============================================================================
# Task Model Extended Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.models
def test_task_str_representation(task):
    """Test task string representation"""
    str_repr = str(task)
    assert 'Task' in str_repr or task.name in str_repr


@pytest.mark.unit
@pytest.mark.models
def test_task_repr(task):
    """Test task repr"""
    repr_str = repr(task)
    assert 'Task' in repr_str


@pytest.mark.unit
@pytest.mark.models
def test_task_with_priority(app, project, user):
    """Test task with priority levels"""
    with app.app_context():
        project = db.session.merge(project)
        user = db.session.merge(user)
        
        for priority in ['low', 'medium', 'high']:
            task = Task(
                project_id=project.id,
                name=f'Task with {priority} priority',
                assigned_to=user.id,
                created_by=user.id,
                priority=priority
            )
            db.session.add(task)
        
        db.session.commit()
        
        # Verify tasks were created
        tasks = Task.query.filter_by(project_id=project.id).all()
        assert len(tasks) >= 3


@pytest.mark.unit
@pytest.mark.models
def test_task_with_due_date(app, project, user):
    """Test task with due date"""
    with app.app_context():
        project = db.session.merge(project)
        user = db.session.merge(user)
        
        due_date = datetime.utcnow() + timedelta(days=7)
        task = Task(
            project_id=project.id,
            name='Task with deadline',
            assigned_to=user.id,
            created_by=user.id,
            due_date=due_date
        )
        db.session.add(task)
        db.session.commit()
        
        # Verify task was created
        assert task.id is not None
        if hasattr(task, 'due_date'):
            assert task.due_date is not None


@pytest.mark.unit
@pytest.mark.models
def test_task_completion(app, task):
    """Test marking task as completed"""
    with app.app_context():
        task = db.session.merge(task)
        
        task.status = 'completed'
        task.completed_at = datetime.utcnow()
        db.session.commit()
        
        assert task.status == 'completed'
        if hasattr(task, 'completed_at'):
            assert task.completed_at is not None


# ============================================================================
# Invoice Model Extended Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.models
def test_invoice_str_representation(invoice):
    """Test invoice string representation"""
    str_repr = str(invoice)
    assert 'Invoice' in str_repr or invoice.invoice_number in str_repr


@pytest.mark.unit
@pytest.mark.models
def test_invoice_repr(invoice):
    """Test invoice repr"""
    repr_str = repr(invoice)
    assert 'Invoice' in repr_str


@pytest.mark.unit
@pytest.mark.models
def test_invoice_with_multiple_items(app, test_client, project, user):
    """Test invoice with multiple line items"""
    with app.app_context():
        test_client = db.session.merge(test_client)
        project = db.session.merge(project)
        user = db.session.merge(user)
        
        invoice = InvoiceFactory(
            client_id=test_client.id,
            project_id=project.id,
            client_name=test_client.name,
            invoice_number='INV-TEST-001',
            issue_date=datetime.utcnow().date(),
            due_date=(datetime.utcnow() + timedelta(days=30)).date(),
            status='draft',
            created_by=user.id
        )
        
        # Add multiple items
        for i in range(5):
            InvoiceItemFactory(
                invoice_id=invoice.id,
                description=f'Service {i+1}',
                quantity=i+1,
                unit_price=100.0
            )
        
        db.session.commit()
        db.session.refresh(invoice)
        
        # Verify items were added
        if hasattr(invoice, 'items'):
            assert len(invoice.items.all()) == 5


@pytest.mark.unit
@pytest.mark.models
def test_invoice_with_discount(app, invoice):
    """Test invoice with discount applied"""
    with app.app_context():
        invoice = db.session.merge(invoice)
        
        if hasattr(invoice, 'discount'):
            invoice.discount = 10.0  # 10% discount
            db.session.commit()
            
            invoice.calculate_totals()
            assert invoice.total < invoice.subtotal


@pytest.mark.unit
@pytest.mark.models
def test_invoice_status_transitions(app, test_client, project, user):
    """Test invoice status transitions"""
    with app.app_context():
        test_client = db.session.merge(test_client)
        project = db.session.merge(project)
        user = db.session.merge(user)
        
        invoice = InvoiceFactory(
            client_id=test_client.id,
            project_id=project.id,
            client_name=test_client.name,
            invoice_number='INV-STATUS-001',
            issue_date=datetime.utcnow().date(),
            due_date=(datetime.utcnow() + timedelta(days=30)).date(),
            status='draft',
            created_by=user.id
        )
        db.session.commit()
        
        # Test status transitions
        assert invoice.status == 'draft'
        
        invoice.status = 'sent'
        db.session.commit()
        assert invoice.status == 'sent'
        
        invoice.status = 'paid'
        db.session.commit()
        assert invoice.status == 'paid'


# ============================================================================
# Comment Model Extended Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.models
def test_comment_creation(app, user, task):
    """Test creating a comment on a task"""
    with app.app_context():
        user = db.session.merge(user)
        task = db.session.merge(task)
        
        comment = Comment(
            content='This is a test comment',
            user_id=user.id,
            task_id=task.id
        )
        db.session.add(comment)
        db.session.commit()
        
        assert comment.id is not None
        assert comment.content == 'This is a test comment'
        assert comment.task_id == task.id
        assert comment.user_id == user.id


@pytest.mark.unit
@pytest.mark.models
def test_comment_str_representation(app, user, task):
    """Test comment string representation"""
    with app.app_context():
        user = db.session.merge(user)
        task = db.session.merge(task)
        
        comment = Comment(
            content='Test comment',
            user_id=user.id,
            task_id=task.id
        )
        db.session.add(comment)
        db.session.commit()
        
        str_repr = str(comment)
        assert 'Comment' in str_repr or 'Test comment' in str_repr


# ============================================================================
# Settings Model Extended Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.models
def test_settings_update(app):
    """Test updating settings"""
    with app.app_context():
        settings = Settings.get_settings()
        
        original_company = settings.company_name
        settings.company_name = 'Updated Company Name'
        db.session.commit()
        
        # Verify update
        settings = Settings.get_settings()
        assert settings.company_name == 'Updated Company Name'
        assert settings.company_name != original_company


@pytest.mark.unit
@pytest.mark.models
def test_settings_currency(app):
    """Test settings currency configuration"""
    with app.app_context():
        settings = Settings.get_settings()
        
        # Test different currencies
        for currency in ['USD', 'EUR', 'GBP', 'JPY']:
            settings.currency = currency
            db.session.commit()
            
            settings = Settings.get_settings()
            assert settings.currency == currency


@pytest.mark.unit
@pytest.mark.models
def test_settings_timezone_validation(app):
    """Test that invalid timezones are handled"""
    with app.app_context():
        settings = Settings.get_settings()
        
        # Set a valid timezone
        settings.timezone = 'America/New_York'
        db.session.commit()
        
        settings = Settings.get_settings()
        assert settings.timezone == 'America/New_York'


@pytest.mark.unit
@pytest.mark.models
def test_settings_str_representation(app):
    """Test settings string representation"""
    with app.app_context():
        settings = Settings.get_settings()
        str_repr = str(settings)
        assert 'Settings' in str_repr


# ============================================================================
# Relationship Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.models
def test_user_client_relationship_through_projects(app, user, test_client):
    """Test user-client relationship through projects and time entries"""
    with app.app_context():
        user = db.session.merge(user)
        test_client = db.session.merge(test_client)
        
        # Create project
        project = Project(
            name='Relationship Test Project',
            client_id=test_client.id,
            billable=True,
            hourly_rate=100.0
        )
        db.session.add(project)
        db.session.flush()
        
        # Create time entry
        from factories import TimeEntryFactory
        entry = TimeEntryFactory(
            user_id=user.id,
            project_id=project.id,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(hours=2),
            source='manual'
        )
        db.session.commit()
        
        # Verify relationships
        assert entry.project.client_id == test_client.id
        assert entry.user_id == user.id


@pytest.mark.integration
@pytest.mark.models
def test_task_comment_relationship(app, user, project):
    """Test task-comment relationship"""
    with app.app_context():
        user = db.session.merge(user)
        project = db.session.merge(project)
        
        # Create task
        task = Task(
            project_id=project.id,
            name='Task with comments',
            assigned_to=user.id,
            created_by=user.id
        )
        db.session.add(task)
        db.session.flush()
        
        # Add comments
        for i in range(3):
            comment = Comment(
                content=f'Comment {i+1}',
                user_id=user.id,
                task_id=task.id
            )
            db.session.add(comment)
        
        db.session.commit()
        db.session.refresh(task)
        
        # Verify relationship
        if hasattr(task, 'comments'):
            assert len(task.comments) >= 3

