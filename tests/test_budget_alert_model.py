"""Model tests for BudgetAlert"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from app import db
from app.models import BudgetAlert, Project, User, Client


@pytest.fixture
def client_obj(app):
    """Create a test client"""
    client = Client(name="Test Client")
    db.session.add(client)
    db.session.commit()
    return client


@pytest.fixture
def project_with_budget(app, client_obj):
    """Create a test project with budget"""
    project = Project(
        name="Test Project",
        client_id=client_obj.id,
        billable=True,
        hourly_rate=Decimal("100.00"),
        budget_amount=Decimal("10000.00"),
        budget_threshold_percent=80,
        status='active'
    )
    db.session.add(project)
    db.session.commit()
    return project


@pytest.fixture
def test_user(app):
    """Create a test user"""
    user = User(username="testuser", role="user")
    user.is_active = True
    db.session.add(user)
    db.session.commit()
    return user


def test_budget_alert_creation(app, project_with_budget):
    """Test creating a budget alert"""
    alert = BudgetAlert(
        project_id=project_with_budget.id,
        alert_type='warning_80',
        alert_level='warning',
        budget_consumed_percent=Decimal('82.5'),
        budget_amount=Decimal('10000.00'),
        consumed_amount=Decimal('8250.00'),
        message='Warning: Project has consumed 82.5% of budget'
    )
    
    db.session.add(alert)
    db.session.commit()
    
    assert alert.id is not None
    assert alert.project_id == project_with_budget.id
    assert alert.alert_type == 'warning_80'
    assert alert.alert_level == 'warning'
    assert float(alert.budget_consumed_percent) == 82.5
    assert not alert.is_acknowledged
    assert alert.acknowledged_by is None
    assert alert.acknowledged_at is None


def test_budget_alert_acknowledge(app, project_with_budget, test_user):
    """Test acknowledging a budget alert"""
    alert = BudgetAlert(
        project_id=project_with_budget.id,
        alert_type='warning_80',
        alert_level='warning',
        budget_consumed_percent=Decimal('82.5'),
        budget_amount=Decimal('10000.00'),
        consumed_amount=Decimal('8250.00'),
        message='Warning: Project has consumed 82.5% of budget'
    )
    
    db.session.add(alert)
    db.session.commit()
    
    # Acknowledge the alert
    alert.acknowledge(test_user.id)
    
    assert alert.is_acknowledged
    assert alert.acknowledged_by == test_user.id
    assert alert.acknowledged_at is not None
    assert isinstance(alert.acknowledged_at, datetime)


def test_budget_alert_to_dict(app, project_with_budget):
    """Test converting budget alert to dictionary"""
    alert = BudgetAlert(
        project_id=project_with_budget.id,
        alert_type='warning_80',
        alert_level='warning',
        budget_consumed_percent=Decimal('82.5'),
        budget_amount=Decimal('10000.00'),
        consumed_amount=Decimal('8250.00'),
        message='Warning: Project has consumed 82.5% of budget'
    )
    
    db.session.add(alert)
    db.session.commit()
    
    alert_dict = alert.to_dict()
    
    assert isinstance(alert_dict, dict)
    assert alert_dict['id'] == alert.id
    assert alert_dict['project_id'] == project_with_budget.id
    assert alert_dict['project_name'] == project_with_budget.name
    assert alert_dict['alert_type'] == 'warning_80'
    assert alert_dict['alert_level'] == 'warning'
    assert alert_dict['budget_consumed_percent'] == 82.5
    assert alert_dict['budget_amount'] == 10000.0
    assert alert_dict['consumed_amount'] == 8250.0
    assert not alert_dict['is_acknowledged']
    assert alert_dict['acknowledged_by'] is None
    assert alert_dict['acknowledged_at'] is None


def test_get_active_alerts(app, project_with_budget):
    """Test getting active alerts"""
    # Create multiple alerts
    alert1 = BudgetAlert(
        project_id=project_with_budget.id,
        alert_type='warning_80',
        alert_level='warning',
        budget_consumed_percent=Decimal('82.5'),
        budget_amount=Decimal('10000.00'),
        consumed_amount=Decimal('8250.00'),
        message='Warning 1'
    )
    
    alert2 = BudgetAlert(
        project_id=project_with_budget.id,
        alert_type='warning_100',
        alert_level='critical',
        budget_consumed_percent=Decimal('100.0'),
        budget_amount=Decimal('10000.00'),
        consumed_amount=Decimal('10000.00'),
        message='Warning 2'
    )
    
    db.session.add(alert1)
    db.session.add(alert2)
    db.session.commit()
    
    # Get all active (unacknowledged) alerts
    active_alerts = BudgetAlert.get_active_alerts()
    
    assert len(active_alerts) == 2
    assert all(not alert.is_acknowledged for alert in active_alerts)


def test_get_active_alerts_by_project(app, project_with_budget, client_obj):
    """Test getting active alerts for a specific project"""
    # Create another project
    project2 = Project(
        name="Project 2",
        client_id=client_obj.id,
        billable=True,
        hourly_rate=Decimal("100.00"),
        budget_amount=Decimal("5000.00"),
        status='active'
    )
    db.session.add(project2)
    db.session.commit()
    
    # Create alerts for both projects
    alert1 = BudgetAlert(
        project_id=project_with_budget.id,
        alert_type='warning_80',
        alert_level='warning',
        budget_consumed_percent=Decimal('82.5'),
        budget_amount=Decimal('10000.00'),
        consumed_amount=Decimal('8250.00'),
        message='Project 1 alert'
    )
    
    alert2 = BudgetAlert(
        project_id=project2.id,
        alert_type='warning_80',
        alert_level='warning',
        budget_consumed_percent=Decimal('85.0'),
        budget_amount=Decimal('5000.00'),
        consumed_amount=Decimal('4250.00'),
        message='Project 2 alert'
    )
    
    db.session.add(alert1)
    db.session.add(alert2)
    db.session.commit()
    
    # Get alerts for project 1 only
    project1_alerts = BudgetAlert.get_active_alerts(project_id=project_with_budget.id)
    
    assert len(project1_alerts) == 1
    assert project1_alerts[0].project_id == project_with_budget.id


def test_create_alert_method(app, project_with_budget):
    """Test the create_alert class method"""
    alert = BudgetAlert.create_alert(
        project_id=project_with_budget.id,
        alert_type='warning_80',
        budget_consumed_percent=82.5,
        budget_amount=10000.0,
        consumed_amount=8250.0
    )
    
    assert alert is not None
    assert alert.id is not None
    assert alert.alert_type == 'warning_80'
    assert alert.alert_level == 'warning'
    assert float(alert.budget_consumed_percent) == 82.5
    assert 'Warning: Project has consumed' in alert.message


def test_create_alert_critical_type(app, project_with_budget):
    """Test creating a critical alert"""
    alert = BudgetAlert.create_alert(
        project_id=project_with_budget.id,
        alert_type='warning_100',
        budget_consumed_percent=100.0,
        budget_amount=10000.0,
        consumed_amount=10000.0
    )
    
    assert alert is not None
    assert alert.alert_level == 'critical'


def test_create_alert_over_budget(app, project_with_budget):
    """Test creating an over budget alert"""
    alert = BudgetAlert.create_alert(
        project_id=project_with_budget.id,
        alert_type='over_budget',
        budget_consumed_percent=110.0,
        budget_amount=10000.0,
        consumed_amount=11000.0
    )
    
    assert alert is not None
    assert alert.alert_level == 'critical'
    assert 'over budget' in alert.message.lower()


def test_create_alert_no_duplicates(app, project_with_budget):
    """Test that duplicate alerts are not created"""
    # Create first alert
    alert1 = BudgetAlert.create_alert(
        project_id=project_with_budget.id,
        alert_type='warning_80',
        budget_consumed_percent=82.5,
        budget_amount=10000.0,
        consumed_amount=8250.0
    )
    
    # Try to create duplicate alert
    alert2 = BudgetAlert.create_alert(
        project_id=project_with_budget.id,
        alert_type='warning_80',
        budget_consumed_percent=83.0,
        budget_amount=10000.0,
        consumed_amount=8300.0
    )
    
    # Should return the existing alert, not create a new one
    assert alert1.id == alert2.id
    
    # Verify only one alert exists
    all_alerts = BudgetAlert.query.filter_by(project_id=project_with_budget.id).all()
    assert len(all_alerts) == 1


def test_get_alert_summary(app, project_with_budget, client_obj):
    """Test getting alert summary statistics"""
    # Create multiple alerts with different statuses
    alert1 = BudgetAlert(
        project_id=project_with_budget.id,
        alert_type='warning_80',
        alert_level='warning',
        budget_consumed_percent=Decimal('82.5'),
        budget_amount=Decimal('10000.00'),
        consumed_amount=Decimal('8250.00'),
        message='Warning alert'
    )
    
    alert2 = BudgetAlert(
        project_id=project_with_budget.id,
        alert_type='warning_100',
        alert_level='critical',
        budget_consumed_percent=Decimal('100.0'),
        budget_amount=Decimal('10000.00'),
        consumed_amount=Decimal('10000.00'),
        message='Critical alert'
    )
    
    # Create acknowledged alert
    alert3 = BudgetAlert(
        project_id=project_with_budget.id,
        alert_type='warning_80',
        alert_level='warning',
        budget_consumed_percent=Decimal('85.0'),
        budget_amount=Decimal('10000.00'),
        consumed_amount=Decimal('8500.00'),
        message='Acknowledged alert'
    )
    alert3.is_acknowledged = True
    
    db.session.add(alert1)
    db.session.add(alert2)
    db.session.add(alert3)
    db.session.commit()
    
    summary = BudgetAlert.get_alert_summary()
    
    assert summary['total_alerts'] == 3
    assert summary['unacknowledged_alerts'] == 2
    assert summary['critical_alerts'] == 1


def test_get_alert_summary_by_project(app, project_with_budget, client_obj):
    """Test getting alert summary for a specific project"""
    # Create another project
    project2 = Project(
        name="Project 2",
        client_id=client_obj.id,
        billable=True,
        hourly_rate=Decimal("100.00"),
        budget_amount=Decimal("5000.00"),
        status='active'
    )
    db.session.add(project2)
    db.session.commit()
    
    # Create alerts for both projects
    alert1 = BudgetAlert(
        project_id=project_with_budget.id,
        alert_type='warning_80',
        alert_level='warning',
        budget_consumed_percent=Decimal('82.5'),
        budget_amount=Decimal('10000.00'),
        consumed_amount=Decimal('8250.00'),
        message='Project 1 alert'
    )
    
    alert2 = BudgetAlert(
        project_id=project2.id,
        alert_type='warning_80',
        alert_level='warning',
        budget_consumed_percent=Decimal('85.0'),
        budget_amount=Decimal('5000.00'),
        consumed_amount=Decimal('4250.00'),
        message='Project 2 alert'
    )
    
    db.session.add(alert1)
    db.session.add(alert2)
    db.session.commit()
    
    # Get summary for project 1 only
    summary = BudgetAlert.get_alert_summary(project_id=project_with_budget.id)
    
    assert summary['total_alerts'] == 1
    assert summary['unacknowledged_alerts'] == 1


def test_alert_repr(app, project_with_budget):
    """Test the string representation of a budget alert"""
    alert = BudgetAlert(
        project_id=project_with_budget.id,
        alert_type='warning_80',
        alert_level='warning',
        budget_consumed_percent=Decimal('82.5'),
        budget_amount=Decimal('10000.00'),
        consumed_amount=Decimal('8250.00'),
        message='Test alert'
    )
    
    db.session.add(alert)
    db.session.commit()
    
    repr_str = repr(alert)
    assert 'BudgetAlert' in repr_str
    assert 'warning_80' in repr_str
    assert str(project_with_budget.id) in repr_str


def test_alert_message_generation(app, project_with_budget):
    """Test alert message generation for different types"""
    # Test warning_80 message
    alert1 = BudgetAlert.create_alert(
        project_id=project_with_budget.id,
        alert_type='warning_80',
        budget_consumed_percent=82.5,
        budget_amount=10000.0,
        consumed_amount=8250.0
    )
    assert 'Warning' in alert1.message
    assert '82.5%' in alert1.message or '82.5' in alert1.message
    
    # Test warning_100 message
    alert2 = BudgetAlert.create_alert(
        project_id=project_with_budget.id,
        alert_type='warning_100',
        budget_consumed_percent=100.0,
        budget_amount=10000.0,
        consumed_amount=10000.0
    )
    assert 'reached 100%' in alert2.message.lower() or 'alert' in alert2.message.lower()
    
    # Test over_budget message
    alert3 = BudgetAlert.create_alert(
        project_id=project_with_budget.id,
        alert_type='over_budget',
        budget_consumed_percent=110.0,
        budget_amount=10000.0,
        consumed_amount=11000.0
    )
    assert 'over budget' in alert3.message.lower() or 'critical' in alert3.message.lower()


def test_acknowledged_alerts_filter(app, project_with_budget, test_user):
    """Test filtering for acknowledged alerts"""
    # Create alerts
    alert1 = BudgetAlert.create_alert(
        project_id=project_with_budget.id,
        alert_type='warning_80',
        budget_consumed_percent=82.5,
        budget_amount=10000.0,
        consumed_amount=8250.0
    )
    
    alert2 = BudgetAlert.create_alert(
        project_id=project_with_budget.id,
        alert_type='warning_100',
        budget_consumed_percent=100.0,
        budget_amount=10000.0,
        consumed_amount=10000.0
    )
    
    # Acknowledge one alert
    alert1.acknowledge(test_user.id)
    
    # Get unacknowledged alerts
    unacknowledged = BudgetAlert.get_active_alerts(acknowledged=False)
    assert len(unacknowledged) == 1
    assert unacknowledged[0].id == alert2.id
    
    # Get acknowledged alerts
    acknowledged = BudgetAlert.get_active_alerts(acknowledged=True)
    assert len(acknowledged) == 1
    assert acknowledged[0].id == alert1.id

