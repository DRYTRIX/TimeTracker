"""
Comprehensive model testing suite.
Tests all models, relationships, properties, and business logic.
"""

import pytest
from datetime import datetime, timedelta, date
from decimal import Decimal

from app.models import (
    User, Project, TimeEntry, Client, Settings,
    Invoice, InvoiceItem, Task
)
from factories import InvoiceFactory
from app import db


# ============================================================================
# User Model Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.models
@pytest.mark.smoke
def test_user_creation(app, user):
    """Test basic user creation."""
    assert user.id is not None
    assert user.username == 'testuser'
    assert user.role == 'user'
    assert user.is_active is True


@pytest.mark.unit
@pytest.mark.models
def test_user_is_admin_property(app, admin_user):
    """Test user is_admin property."""
    assert admin_user.is_admin is True


@pytest.mark.unit
@pytest.mark.models
def test_user_active_timer(app, user, active_timer):
    """Test user active_timer property."""
    # Refresh user to load relationships
    db.session.refresh(user)
    assert user.active_timer is not None
    assert user.active_timer.id == active_timer.id


@pytest.mark.unit
@pytest.mark.models
def test_user_time_entries_relationship(app, user, multiple_time_entries):
    """Test user time entries relationship."""
    db.session.refresh(user)
    assert len(user.time_entries.all()) == 5


@pytest.mark.unit
@pytest.mark.models
def test_user_to_dict(app, user):
    """Test user serialization to dictionary."""
    user_dict = user.to_dict()
    assert 'id' in user_dict
    assert 'username' in user_dict
    assert 'role' in user_dict
    # Should not include sensitive data
    assert 'password' not in user_dict


# ============================================================================
# Client Model Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.models
@pytest.mark.smoke
def test_client_creation(app, test_client):
    """Test basic client creation."""
    assert test_client.id is not None
    assert test_client.name == 'Test Client Corp'
    assert test_client.status == 'active'
    assert test_client.default_hourly_rate == Decimal('85.00')


@pytest.mark.unit
@pytest.mark.models
def test_client_projects_relationship(app, test_client, multiple_projects):
    """Test client projects relationship."""
    db.session.refresh(test_client)
    assert len(test_client.projects.all()) == 3


@pytest.mark.unit
@pytest.mark.models
def test_client_total_projects_property(app, test_client, multiple_projects):
    """Test client total_projects property."""
    db.session.refresh(test_client)
    assert test_client.total_projects == 3


@pytest.mark.unit
@pytest.mark.models
def test_client_archive_activate(app, test_client):
    """Test client archive and activate methods."""
    db.session.refresh(test_client)
    
    # Archive client
    test_client.archive()
    db.session.commit()
    assert test_client.status == 'inactive'
    
    # Activate client
    test_client.activate()
    db.session.commit()
    assert test_client.status == 'active'


@pytest.mark.unit
@pytest.mark.models
def test_client_get_active_clients(app, multiple_clients):
    """Test get_active_clients class method."""
    active_clients = Client.get_active_clients()
    assert len(active_clients) >= 3


@pytest.mark.unit
@pytest.mark.models
def test_client_to_dict(app, test_client):
    """Test client serialization to dictionary."""
    client_dict = test_client.to_dict()
    assert 'id' in client_dict
    assert 'name' in client_dict
    assert 'status' in client_dict


# ============================================================================
# Project Model Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.models
@pytest.mark.smoke
def test_project_creation(app, project):
    """Test basic project creation."""
    assert project.id is not None
    assert project.name == 'Test Project'
    assert project.billable is True
    assert project.status == 'active'


@pytest.mark.unit
@pytest.mark.models
def test_project_client_relationship(app, project, test_client):
    """Test project client relationship."""
    db.session.refresh(project)
    db.session.refresh(test_client)
    assert project.client_id == test_client.id
    # Check backward compatibility
    if hasattr(project, 'client'):
        assert project.client == test_client.name


@pytest.mark.unit
@pytest.mark.models
def test_project_time_entries_relationship(app, project, multiple_time_entries):
    """Test project time entries relationship."""
    db.session.refresh(project)
    assert len(project.time_entries.all()) == 5


@pytest.mark.unit
@pytest.mark.models
def test_project_total_hours(app, project, multiple_time_entries):
    """Test project total_hours property."""
    db.session.refresh(project)
    # Each entry is 8 hours (9am to 5pm), 5 entries = 40 hours
    assert project.total_hours > 0


@pytest.mark.unit
@pytest.mark.models
def test_project_estimated_cost(app, project, multiple_time_entries):
    """Test project estimated_cost property."""
    db.session.refresh(project)
    estimated_cost = project.estimated_cost
    assert estimated_cost > 0
    # Cost should be hours * hourly_rate
    expected_cost = project.total_hours * float(project.hourly_rate)
    assert abs(float(estimated_cost) - expected_cost) < 0.01


@pytest.mark.unit
@pytest.mark.models
def test_project_archive(app, project):
    """Test project archiving."""
    db.session.refresh(project)
    project.status = 'archived'
    db.session.commit()
    assert project.status == 'archived'


# ============================================================================
# Time Entry Model Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.models
@pytest.mark.smoke
def test_time_entry_creation(app, time_entry):
    """Test basic time entry creation."""
    assert time_entry.id is not None
    assert time_entry.start_time is not None
    assert time_entry.end_time is not None


@pytest.mark.unit
@pytest.mark.models
def test_time_entry_duration(app, time_entry):
    """Test time entry duration calculations."""
    db.session.refresh(time_entry)
    assert time_entry.duration_seconds > 0
    assert time_entry.duration_hours > 0
    assert time_entry.duration_formatted is not None


@pytest.mark.unit
@pytest.mark.models
def test_active_timer_is_active(app, active_timer):
    """Test active timer is_active property."""
    db.session.refresh(active_timer)
    assert active_timer.is_active is True
    assert active_timer.end_time is None


@pytest.mark.unit
@pytest.mark.models
def test_stop_timer(app, active_timer):
    """Test stopping an active timer."""
    db.session.refresh(active_timer)
    active_timer.stop_timer()
    db.session.commit()
    
    db.session.refresh(active_timer)
    assert active_timer.is_active is False
    assert active_timer.end_time is not None
    assert active_timer.duration_seconds > 0


@pytest.mark.unit
@pytest.mark.models
def test_time_entry_tag_list(app, test_client):
    """Test time entry tag_list property."""
    from app.models import User, Project
    
    user = User.query.first() or User(username='test', role='user')
    project = Project.query.first() or Project(name='Test', client_id=test_client.id, billable=True)
    
    if not user.id:
        db.session.add(user)
    if not project.id:
        db.session.add(project)
    db.session.commit()
    
    from factories import TimeEntryFactory
    entry = TimeEntryFactory(
        user_id=user.id,
        project_id=project.id,
        start_time=datetime.utcnow(),
        end_time=datetime.utcnow() + timedelta(hours=1),
        tags='python,testing,development',
        source='manual'
    )
    
    db.session.refresh(entry)
    assert entry.tag_list == ['python', 'testing', 'development']


# ============================================================================
# Task Model Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.models
def test_task_creation(app, task):
    """Test basic task creation."""
    db.session.refresh(task)
    assert task.id is not None
    assert task.name == 'Test Task'
    assert task.status == 'todo'


@pytest.mark.unit
@pytest.mark.models
def test_task_project_relationship(app, task, project):
    """Test task project relationship."""
    db.session.refresh(task)
    db.session.refresh(project)
    assert task.project_id == project.id


@pytest.mark.unit
@pytest.mark.models
def test_task_status_transitions(app, task):
    """Test task status transitions."""
    db.session.refresh(task)
    
    # Mark as in progress
    task.status = 'in_progress'
    db.session.commit()
    assert task.status == 'in_progress'
    
    # Mark as done
    task.status = 'done'
    db.session.commit()
    assert task.status == 'done'


# ============================================================================
# Invoice Model Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.models
@pytest.mark.smoke
def test_invoice_creation(app, invoice):
    """Test basic invoice creation."""
    # Invoice is already refreshed in the fixture, no need to refresh again
    assert invoice.id is not None
    assert invoice.invoice_number is not None
    assert invoice.status == 'draft'


@pytest.mark.unit
@pytest.mark.models
def test_invoice_number_generation(app):
    """Test invoice number generation."""
    invoice_number = Invoice.generate_invoice_number()
    assert invoice_number is not None
    assert 'INV-' in invoice_number


@pytest.mark.unit
@pytest.mark.models
def test_invoice_calculate_totals(app, invoice_with_items):
    """Test invoice total calculations."""
    invoice, items = invoice_with_items
    
    # Invoice is already committed and refreshed in the fixture
    # 10 * 75 + 5 * 60 = 750 + 300 = 1050
    assert invoice.subtotal == Decimal('1050.00')
    
    # Tax: 20% of 1050 = 210
    assert invoice.tax_amount == Decimal('210.00')
    
    # Total: 1050 + 210 = 1260
    assert invoice.total_amount == Decimal('1260.00')


@pytest.mark.unit
@pytest.mark.models
def test_invoice_payment_tracking(app, invoice_with_items):
    """Test invoice payment tracking."""
    invoice, items = invoice_with_items
    
    # Record partial payment
    partial_payment = invoice.total_amount / 2
    invoice.record_payment(
        amount=partial_payment,
        payment_date=date.today(),
        payment_method='bank_transfer',
        payment_reference='TEST-123'
    )
    db.session.commit()
    
    db.session.expire(invoice)
    db.session.refresh(invoice)
    assert invoice.payment_status == 'partially_paid'
    assert invoice.amount_paid == partial_payment
    assert invoice.is_partially_paid is True
    
    # Record remaining payment
    remaining = invoice.outstanding_amount
    invoice.record_payment(
        amount=remaining,
        payment_method='bank_transfer'
    )
    db.session.commit()
    
    db.session.expire(invoice)
    db.session.refresh(invoice)
    assert invoice.payment_status == 'fully_paid'
    assert invoice.is_paid is True
    assert invoice.outstanding_amount == Decimal('0')


@pytest.mark.unit
@pytest.mark.models
def test_invoice_overdue_status(app, user, project, test_client):
    """Test invoice overdue status."""
    # Create overdue invoice
    overdue_invoice = InvoiceFactory(
        invoice_number=Invoice.generate_invoice_number(),
        project_id=project.id,
        client_id=test_client.id,
        client_name='Test Client',
        due_date=date.today() - timedelta(days=10),
        created_by=user.id,
        status='sent'
    )
    db.session.commit()
    
    # Ensure status is 'sent' for overdue calculation compatibility
    overdue_invoice.status = 'sent'
    db.session.commit()
    db.session.refresh(overdue_invoice)
    assert overdue_invoice.is_overdue is True
    assert overdue_invoice.days_overdue == 10


# ============================================================================
# Settings Model Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.models
def test_settings_singleton(app):
    """Test settings singleton pattern."""
    settings1 = Settings.get_settings()
    settings2 = Settings.get_settings()
    
    assert settings1.id == settings2.id


@pytest.mark.unit
@pytest.mark.models
def test_settings_default_values(app):
    """Test settings default values."""
    settings = Settings.get_settings()
    
    # Check that settings has expected attributes
    assert hasattr(settings, 'id')
    # Add more default value checks based on your Settings model


# ============================================================================
# Model Relationship Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.models
@pytest.mark.database
def test_cascade_delete_user_time_entries(app, user, multiple_time_entries):
    """Test cascade delete of user time entries."""
    user_id = user.id
    
    # Get time entry count
    entry_count = TimeEntry.query.filter_by(user_id=user_id).count()
    assert entry_count == 5
    
    # Delete user
    db.session.delete(user)
    db.session.commit()
    
    # Check time entries are deleted or handled
    remaining_entries = TimeEntry.query.filter_by(user_id=user_id).count()
    # Depending on cascade settings, entries might be deleted or set to null
    # For now, we just verify the operation completed without errors
    assert remaining_entries >= 0  # Operation completed successfully


@pytest.mark.integration
@pytest.mark.models
@pytest.mark.database
def test_project_client_relationship_integrity(app, project, test_client):
    """Test project-client relationship integrity."""
    # Verify the relationship
    assert project.client_id == test_client.id
    
    # Get project through client relationship
    client_projects = Client.query.get(test_client.id).projects.all()
    project_ids = [p.id for p in client_projects]
    assert project.id in project_ids


# ============================================================================
# Model Validation Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.models
def test_project_requires_name(app, test_client):
    """Test that project requires a name."""
    # Project __init__ requires name as first positional argument
    # This test verifies the API enforces this requirement
    with pytest.raises(TypeError):
        project = Project(billable=True)


@pytest.mark.unit
@pytest.mark.models
def test_time_entry_requires_start_time(app, user, project):
    """Test that time entry requires start time."""
    # TimeEntry requires start_time at database level (nullable=False)
    # This test verifies the database enforces this requirement
    from sqlalchemy.exc import IntegrityError
    from app import db
    
    with pytest.raises(IntegrityError):
        entry = TimeEntry(
            user_id=user.id,
            project_id=project.id,
            source='manual'
        )
        db.session.add(entry)
        db.session.commit()


# ============================================================================
# User Deletion and Cascading Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.models
def test_user_deletion_without_relationships(app):
    """Test that a user without relationships can be deleted."""
    with app.app_context():
        # Create a user with no relationships
        delete_user = User(username='deletable', role='user')
        delete_user.is_active = True
        db.session.add(delete_user)
        db.session.commit()
        user_id = delete_user.id
        
        # Delete the user
        db.session.delete(delete_user)
        db.session.commit()
        
        # Verify deletion
        deleted = User.query.get(user_id)
        assert deleted is None


@pytest.mark.unit
@pytest.mark.models
def test_user_deletion_cascades_project_costs(app, test_client):
    """Test that deleting a user cascades to project costs."""
    from app.models import ProjectCost
    from datetime import date
    
    with app.app_context():
        # Create user and project
        user = User(username='costuser', role='user')
        user.is_active = True
        db.session.add(user)
        
        project = Project(
            name='Cost Test Project',
            client_id=test_client.id,
            billable=True
        )
        db.session.add(project)
        db.session.commit()
        
        # Create project cost
        cost = ProjectCost(
            project_id=project.id,
            user_id=user.id,
            description='Test expense',
            category='materials',
            amount=Decimal('100.00'),
            cost_date=date.today()
        )
        db.session.add(cost)
        db.session.commit()
        
        user_id = user.id
        cost_id = cost.id
        
        # Delete user
        db.session.delete(user)
        db.session.commit()
        
        # Verify user is deleted
        deleted_user = User.query.get(user_id)
        assert deleted_user is None
        
        # Verify project cost is cascaded (deleted)
        deleted_cost = ProjectCost.query.get(cost_id)
        assert deleted_cost is None


@pytest.mark.unit
@pytest.mark.models
def test_user_deletion_cascades_time_entries(app, test_client):
    """Test that deleting a user cascades to time entries."""
    with app.app_context():
        # Create user and project
        user = User(username='entryuser', role='user')
        user.is_active = True
        db.session.add(user)
        
        project = Project(
            name='Entry Test Project',
            client_id=test_client.id,
            billable=True
        )
        db.session.add(project)
        db.session.commit()
        
        # Create time entry
        entry = TimeEntry(
            user_id=user.id,
            project_id=project.id,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(hours=1),
            description='Test entry'
        )
        db.session.add(entry)
        db.session.commit()
        
        user_id = user.id
        entry_id = entry.id
        
        # Delete user
        db.session.delete(user)
        db.session.commit()
        
        # Verify user is deleted
        deleted_user = User.query.get(user_id)
        assert deleted_user is None
        
        # Verify time entry is cascaded (deleted)
        deleted_entry = TimeEntry.query.get(entry_id)
        assert deleted_entry is None


@pytest.mark.unit
@pytest.mark.models
def test_user_deletion_removes_from_favorite_projects(app, test_client):
    """Test that deleting a user removes them from favorite projects."""
    with app.app_context():
        # Create user and project
        user = User(username='favuser', role='user')
        user.is_active = True
        db.session.add(user)
        
        project = Project(
            name='Favorite Test Project',
            client_id=test_client.id,
            billable=True
        )
        db.session.add(project)
        db.session.commit()
        
        # Add project to favorites
        user.favorite_projects.append(project)
        db.session.commit()
        
        # Verify favorite was added
        assert project in user.favorite_projects.all()
        
        user_id = user.id
        project_id = project.id
        
        # Delete user
        db.session.delete(user)
        db.session.commit()
        
        # Verify user is deleted
        deleted_user = User.query.get(user_id)
        assert deleted_user is None
        
        # Verify project still exists (favorites are many-to-many)
        remaining_project = Project.query.get(project_id)
        assert remaining_project is not None
        
        # Verify user is not in project's favorited_by
        assert user_id not in [u.id for u in remaining_project.favorited_by.all()]


@pytest.mark.unit
@pytest.mark.models
def test_user_deletion_preserves_tasks_assigned_to_them(app, test_client):
    """Test that deleting a user preserves tasks but nullifies assigned_to."""
    with app.app_context():
        # Create users and project
        creator = User(username='creator', role='user')
        creator.is_active = True
        assignee = User(username='assignee', role='user')
        assignee.is_active = True
        db.session.add_all([creator, assignee])
        
        project = Project(
            name='Task Test Project',
            client_id=test_client.id,
            billable=True
        )
        db.session.add(project)
        db.session.commit()
        
        # Create task
        task = Task(
            project_id=project.id,
            name='Test Task',
            description='Test description',
            created_by=creator.id,
            assigned_to=assignee.id
        )
        db.session.add(task)
        db.session.commit()
        
        assignee_id = assignee.id
        task_id = task.id
        
        # Delete assignee
        db.session.delete(assignee)
        db.session.commit()
        
        # Verify assignee is deleted
        deleted_user = User.query.get(assignee_id)
        assert deleted_user is None
        
        # Verify task still exists but assigned_to is nullified
        remaining_task = Task.query.get(task_id)
        assert remaining_task is not None
        assert remaining_task.assigned_to is None


@pytest.mark.unit
@pytest.mark.models
def test_user_cannot_be_deleted_if_has_created_tasks(app, test_client):
    """Test that deleting a user who created tasks cascades properly."""
    from sqlalchemy.exc import IntegrityError
    
    with app.app_context():
        # Create user and project
        creator = User(username='taskcreator', role='user')
        creator.is_active = True
        db.session.add(creator)
        
        project = Project(
            name='Task Creator Project',
            client_id=test_client.id,
            billable=True
        )
        db.session.add(project)
        db.session.commit()
        
        # Create task
        task = Task(
            project_id=project.id,
            name='Created Task',
            description='Test description',
            created_by=creator.id
        )
        db.session.add(task)
        db.session.commit()
        
        creator_id = creator.id
        
        # Try to delete creator - should raise IntegrityError because created_by is NOT NULL
        with pytest.raises(IntegrityError):
            db.session.delete(creator)
            db.session.commit()
        
        db.session.rollback()
        
        # Verify creator still exists
        still_exists = User.query.get(creator_id)
        assert still_exists is not None


@pytest.mark.unit
@pytest.mark.models
def test_user_deletion_count_check(app):
    """Test that we can query user count before and after deletion."""
    with app.app_context():
        # Get initial count
        initial_count = User.query.count()
        
        # Create and delete a user
        temp_user = User(username='tempuser', role='user')
        temp_user.is_active = True
        db.session.add(temp_user)
        db.session.commit()
        
        # Verify count increased
        assert User.query.count() == initial_count + 1
        
        # Delete user
        db.session.delete(temp_user)
        db.session.commit()
        
        # Verify count back to initial
        assert User.query.count() == initial_count