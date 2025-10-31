"""Unit tests for budget forecasting utilities"""

import pytest
from datetime import datetime, timedelta, date
from decimal import Decimal
from app import db
from app.models import Project, TimeEntry, User, ProjectCost, Client
from app.utils.budget_forecasting import (
    calculate_burn_rate,
    estimate_completion_date,
    analyze_resource_allocation,
    analyze_cost_trends,
    get_budget_status,
    check_budget_alerts
)


@pytest.fixture
def client_obj(app):
    """Create a test client"""
    client = Client(name="Test Client", status="active")
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


@pytest.fixture
def time_entries_last_30_days(app, project_with_budget, test_user):
    """Create time entries for the last 30 days"""
    entries = []
    now = datetime.now()
    
    for i in range(30):
        entry_date = now - timedelta(days=i)
        entry = TimeEntry(
            user_id=test_user.id,
            project_id=project_with_budget.id,
            start_time=entry_date,
            end_time=entry_date + timedelta(hours=4),
            billable=True
        )
        entry.calculate_duration()
        db.session.add(entry)
        entries.append(entry)
    
    db.session.commit()
    return entries


def test_calculate_burn_rate_no_data(app, project_with_budget):
    """Test burn rate calculation with no time entries"""
    burn_rate = calculate_burn_rate(project_with_budget.id, days=30)
    
    assert burn_rate is not None
    assert burn_rate['daily_burn_rate'] == 0
    assert burn_rate['weekly_burn_rate'] == 0
    assert burn_rate['monthly_burn_rate'] == 0
    assert burn_rate['period_total'] == 0
    assert burn_rate['period_days'] == 30


def test_calculate_burn_rate_with_data(app, project_with_budget, time_entries_last_30_days):
    """Test burn rate calculation with time entries"""
    burn_rate = calculate_burn_rate(project_with_budget.id, days=30)
    
    assert burn_rate is not None
    assert burn_rate['daily_burn_rate'] > 0
    assert burn_rate['weekly_burn_rate'] > 0
    assert burn_rate['monthly_burn_rate'] > 0
    assert burn_rate['period_total'] > 0
    
    # Each day has 4 hours at $100/hr = $400/day
    expected_daily = 400.0
    assert abs(burn_rate['daily_burn_rate'] - expected_daily) < 1.0  # Allow small rounding difference


def test_calculate_burn_rate_invalid_project(app):
    """Test burn rate calculation with invalid project ID"""
    burn_rate = calculate_burn_rate(99999, days=30)
    assert burn_rate is None


def test_estimate_completion_date_no_budget(app, client_obj):
    """Test completion estimate for project without budget"""
    project = Project(
        name="No Budget Project",
        client_id=client_obj.id,
        billable=True,
        hourly_rate=Decimal("100.00"),
        status='active'
    )
    db.session.add(project)
    db.session.commit()
    
    estimate = estimate_completion_date(project.id)
    assert estimate is None


def test_estimate_completion_date_no_activity(app, project_with_budget):
    """Test completion estimate with no recent activity"""
    estimate = estimate_completion_date(project_with_budget.id, analysis_days=30)
    
    assert estimate is not None
    assert estimate['estimated_completion_date'] is None
    assert estimate['days_remaining'] is None
    assert estimate['confidence'] == 'low'
    assert 'No recent activity' in estimate['message']


def test_estimate_completion_date_with_activity(app, project_with_budget, time_entries_last_30_days):
    """Test completion estimate with activity"""
    estimate = estimate_completion_date(project_with_budget.id, analysis_days=30)
    
    assert estimate is not None
    assert estimate['estimated_completion_date'] is not None
    assert estimate['days_remaining'] is not None
    assert estimate['daily_burn_rate'] > 0
    assert estimate['budget_amount'] == 10000.0
    assert estimate['confidence'] in ['high', 'medium', 'low']


def test_analyze_resource_allocation_no_data(app, project_with_budget):
    """Test resource allocation analysis with no data"""
    allocation = analyze_resource_allocation(project_with_budget.id, days=30)
    
    assert allocation is not None
    assert allocation['users'] == []
    assert allocation['total_hours'] == 0
    assert allocation['total_cost'] == 0


def test_analyze_resource_allocation_with_data(app, project_with_budget, time_entries_last_30_days):
    """Test resource allocation analysis with data"""
    allocation = analyze_resource_allocation(project_with_budget.id, days=30)
    
    assert allocation is not None
    assert len(allocation['users']) > 0
    assert allocation['total_hours'] > 0
    assert allocation['total_cost'] > 0
    assert allocation['hourly_rate'] == 100.0
    
    # Check user data structure
    user_data = allocation['users'][0]
    assert 'user_id' in user_data
    assert 'username' in user_data
    assert 'hours' in user_data
    assert 'cost' in user_data
    assert 'cost_percentage' in user_data
    assert 'hours_percentage' in user_data


def test_analyze_cost_trends_no_data(app, project_with_budget):
    """Test cost trend analysis with no data"""
    trends = analyze_cost_trends(project_with_budget.id, days=90, granularity='week')
    
    assert trends is not None
    assert trends['periods'] == []
    assert trends['trend_direction'] == 'insufficient_data'
    assert trends['average_cost_per_period'] == 0


def test_analyze_cost_trends_with_data(app, project_with_budget, time_entries_last_30_days):
    """Test cost trend analysis with data"""
    trends = analyze_cost_trends(project_with_budget.id, days=30, granularity='week')
    
    assert trends is not None
    assert len(trends['periods']) > 0
    assert trends['trend_direction'] in ['increasing', 'decreasing', 'stable', 'insufficient_data']
    assert trends['average_cost_per_period'] >= 0
    assert trends['granularity'] == 'week'


def test_analyze_cost_trends_different_granularities(app, project_with_budget, time_entries_last_30_days):
    """Test cost trend analysis with different granularities"""
    # Daily granularity
    daily_trends = analyze_cost_trends(project_with_budget.id, days=30, granularity='day')
    assert daily_trends is not None
    
    # Weekly granularity
    weekly_trends = analyze_cost_trends(project_with_budget.id, days=30, granularity='week')
    assert weekly_trends is not None
    
    # Monthly granularity
    monthly_trends = analyze_cost_trends(project_with_budget.id, days=90, granularity='month')
    assert monthly_trends is not None


def test_get_budget_status_no_budget(app, client_obj):
    """Test budget status for project without budget"""
    project = Project(
        name="No Budget Project",
        client_id=client_obj.id,
        billable=True,
        hourly_rate=Decimal("100.00"),
        status='active'
    )
    db.session.add(project)
    db.session.commit()
    
    status = get_budget_status(project.id)
    assert status is None


def test_get_budget_status_healthy(app, project_with_budget):
    """Test budget status for healthy project"""
    status = get_budget_status(project_with_budget.id)
    
    assert status is not None
    assert status['budget_amount'] == 10000.0
    assert status['consumed_amount'] == 0.0
    assert status['remaining_amount'] == 10000.0
    assert status['consumed_percentage'] == 0.0
    assert status['status'] == 'healthy'
    assert status['threshold_percent'] == 80


def test_get_budget_status_warning(app, project_with_budget, test_user):
    """Test budget status for project in warning state"""
    # Create entries that consume 70% of budget
    # Budget is $10,000, hourly rate is $100
    # 70% = $7,000 = 70 hours
    now = datetime.now()
    for i in range(70):
        entry = TimeEntry(
            user_id=test_user.id,
            project_id=project_with_budget.id,
            start_time=now - timedelta(hours=i+1),
            end_time=now - timedelta(hours=i),
            billable=True
        )
        entry.calculate_duration()
        db.session.add(entry)
    db.session.commit()
    
    status = get_budget_status(project_with_budget.id)
    
    assert status is not None
    assert status['status'] == 'warning'
    assert status['consumed_percentage'] >= 60  # At least 60%
    assert status['consumed_percentage'] < 80   # Less than 80%


def test_get_budget_status_critical(app, project_with_budget, test_user):
    """Test budget status for project in critical state"""
    # Create entries that consume 85% of budget
    # Budget is $10,000, hourly rate is $100
    # 85% = $8,500 = 85 hours
    now = datetime.now()
    for i in range(85):
        entry = TimeEntry(
            user_id=test_user.id,
            project_id=project_with_budget.id,
            start_time=now - timedelta(hours=i+1),
            end_time=now - timedelta(hours=i),
            billable=True
        )
        entry.calculate_duration()
        db.session.add(entry)
    db.session.commit()
    
    status = get_budget_status(project_with_budget.id)
    
    assert status is not None
    assert status['status'] == 'critical'
    assert status['consumed_percentage'] >= 80   # At least 80%
    assert status['consumed_percentage'] < 100   # Less than 100%


def test_get_budget_status_over_budget(app, project_with_budget, test_user):
    """Test budget status for over budget project"""
    # Create entries that consume 110% of budget
    # Budget is $10,000, hourly rate is $100
    # 110% = $11,000 = 110 hours
    now = datetime.now()
    for i in range(110):
        entry = TimeEntry(
            user_id=test_user.id,
            project_id=project_with_budget.id,
            start_time=now - timedelta(hours=i+1),
            end_time=now - timedelta(hours=i),
            billable=True
        )
        entry.calculate_duration()
        db.session.add(entry)
    db.session.commit()
    
    status = get_budget_status(project_with_budget.id)
    
    assert status is not None
    assert status['status'] == 'over_budget'
    assert status['consumed_percentage'] >= 100


def test_check_budget_alerts_no_alerts_needed(app, project_with_budget):
    """Test budget alert checking when no alerts are needed"""
    alerts = check_budget_alerts(project_with_budget.id)
    
    assert isinstance(alerts, list)
    assert len(alerts) == 0


def test_check_budget_alerts_warning_alert(app, project_with_budget, test_user):
    """Test budget alert checking for warning threshold"""
    # Create entries that consume 82% of budget
    now = datetime.now()
    for i in range(82):
        entry = TimeEntry(
            user_id=test_user.id,
            project_id=project_with_budget.id,
            start_time=now - timedelta(hours=i+1),
            end_time=now - timedelta(hours=i),
            billable=True
        )
        entry.calculate_duration()
        db.session.add(entry)
    db.session.commit()
    
    alerts = check_budget_alerts(project_with_budget.id)
    
    assert isinstance(alerts, list)
    assert len(alerts) > 0
    assert any(alert['type'] == 'warning_80' for alert in alerts)


def test_check_budget_alerts_over_budget(app, project_with_budget, test_user):
    """Test budget alert checking for over budget"""
    # Create entries that consume 110% of budget
    now = datetime.now()
    for i in range(110):
        entry = TimeEntry(
            user_id=test_user.id,
            project_id=project_with_budget.id,
            start_time=now - timedelta(hours=i+1),
            end_time=now - timedelta(hours=i),
            billable=True
        )
        entry.calculate_duration()
        db.session.add(entry)
    db.session.commit()
    
    alerts = check_budget_alerts(project_with_budget.id)
    
    assert isinstance(alerts, list)
    # Should have over_budget alert
    assert any(alert['type'] == 'over_budget' for alert in alerts)


def test_check_budget_alerts_invalid_project(app):
    """Test budget alert checking with invalid project"""
    alerts = check_budget_alerts(99999)
    assert isinstance(alerts, list)
    assert len(alerts) == 0


def test_resource_allocation_multiple_users(app, project_with_budget, client_obj):
    """Test resource allocation with multiple users"""
    # Create additional users
    user1 = User(username="user1", role="user")
    user1.is_active = True
    user2 = User(username="user2", role="user")
    user2.is_active = True
    db.session.add(user1)
    db.session.add(user2)
    db.session.commit()
    
    # Create time entries for multiple users
    now = datetime.now()
    for i in range(10):
        # User 1: 10 entries of 2 hours each
        entry1 = TimeEntry(
            user_id=user1.id,
            project_id=project_with_budget.id,
            start_time=now - timedelta(days=i),
            end_time=now - timedelta(days=i) + timedelta(hours=2),
            billable=True
        )
        entry1.calculate_duration()
        db.session.add(entry1)
        
        # User 2: 10 entries of 3 hours each
        entry2 = TimeEntry(
            user_id=user2.id,
            project_id=project_with_budget.id,
            start_time=now - timedelta(days=i),
            end_time=now - timedelta(days=i) + timedelta(hours=3),
            billable=True
        )
        entry2.calculate_duration()
        db.session.add(entry2)
    
    db.session.commit()
    
    allocation = analyze_resource_allocation(project_with_budget.id, days=30)
    
    assert allocation is not None
    assert len(allocation['users']) == 2
    
    # Check that costs are sorted (highest first)
    assert allocation['users'][0]['cost'] >= allocation['users'][1]['cost']
    
    # Check that percentages add up to 100%
    total_cost_percentage = sum(u['cost_percentage'] for u in allocation['users'])
    assert abs(total_cost_percentage - 100.0) < 0.1  # Allow small rounding difference

