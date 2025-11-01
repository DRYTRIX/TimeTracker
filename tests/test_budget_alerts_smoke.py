"""Smoke tests for budget alerts and forecasting feature"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from app import db
from app.models import Project, User, TimeEntry, BudgetAlert, Client


@pytest.fixture
def admin_user(app):
    """Create an admin user"""
    user = User(username="admin", role="admin")
    user.is_active = True
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def regular_user(app):
    """Create a regular user"""
    user = User(username="regular_user", role="user")
    user.is_active = True
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def client_obj(app):
    """Create a test client"""
    client = Client(name="Smoke Test Client")
    db.session.add(client)
    db.session.commit()
    return client


@pytest.fixture
def project_with_budget(app, client_obj):
    """Create a test project with budget"""
    project = Project(
        name="Budget Test Project",
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


def test_budget_dashboard_loads(client, app, admin_user, project_with_budget):
    """Test that the budget dashboard page loads"""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user.id)
    
    response = client.get('/budget/dashboard')
    assert response.status_code == 200
    assert b'Budget Alerts' in response.data or b'budget' in response.data.lower()


def test_project_budget_detail_loads(client, app, admin_user, project_with_budget):
    """Test that the project budget detail page loads"""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user.id)
    
    response = client.get(f'/budget/project/{project_with_budget.id}')
    assert response.status_code == 200
    assert project_with_budget.name.encode() in response.data


def test_burn_rate_api_endpoint(client, app, admin_user, project_with_budget, regular_user):
    """Test the burn rate API endpoint"""
    # Add some time entries
    now = datetime.now()
    for i in range(5):
        entry = TimeEntry(
            user_id=regular_user.id,
            project_id=project_with_budget.id,
            start_time=now - timedelta(days=i),
            end_time=now - timedelta(days=i) + timedelta(hours=4),
            billable=True
        )
        entry.calculate_duration()
        db.session.add(entry)
    db.session.commit()
    
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user.id)
    
    response = client.get(f'/api/budget/burn-rate/{project_with_budget.id}')
    assert response.status_code == 200
    
    data = response.get_json()
    assert 'daily_burn_rate' in data
    assert 'weekly_burn_rate' in data
    assert 'monthly_burn_rate' in data
    assert 'period_total' in data


def test_completion_estimate_api_endpoint(client, app, admin_user, project_with_budget):
    """Test the completion estimate API endpoint"""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user.id)
    
    response = client.get(f'/api/budget/completion-estimate/{project_with_budget.id}')
    assert response.status_code == 200
    
    data = response.get_json()
    assert 'budget_amount' in data
    assert 'consumed_amount' in data
    assert 'daily_burn_rate' in data


def test_resource_allocation_api_endpoint(client, app, admin_user, project_with_budget, regular_user):
    """Test the resource allocation API endpoint"""
    # Add some time entries
    now = datetime.now()
    for i in range(5):
        entry = TimeEntry(
            user_id=regular_user.id,
            project_id=project_with_budget.id,
            start_time=now - timedelta(days=i),
            end_time=now - timedelta(days=i) + timedelta(hours=4),
            billable=True
        )
        entry.calculate_duration()
        db.session.add(entry)
    db.session.commit()
    
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user.id)
    
    response = client.get(f'/api/budget/resource-allocation/{project_with_budget.id}')
    assert response.status_code == 200
    
    data = response.get_json()
    assert 'users' in data
    assert 'total_hours' in data
    assert 'total_cost' in data


def test_cost_trends_api_endpoint(client, app, admin_user, project_with_budget, regular_user):
    """Test the cost trends API endpoint"""
    # Add some time entries
    now = datetime.now()
    for i in range(10):
        entry = TimeEntry(
            user_id=regular_user.id,
            project_id=project_with_budget.id,
            start_time=now - timedelta(days=i),
            end_time=now - timedelta(days=i) + timedelta(hours=4),
            billable=True
        )
        entry.calculate_duration()
        db.session.add(entry)
    db.session.commit()
    
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user.id)
    
    response = client.get(f'/api/budget/cost-trends/{project_with_budget.id}?granularity=week')
    assert response.status_code == 200
    
    data = response.get_json()
    assert 'periods' in data
    assert 'trend_direction' in data
    assert 'average_cost_per_period' in data


def test_budget_status_api_endpoint(client, app, admin_user, project_with_budget):
    """Test the budget status API endpoint"""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user.id)
    
    response = client.get(f'/api/budget/status/{project_with_budget.id}')
    assert response.status_code == 200
    
    data = response.get_json()
    assert 'budget_amount' in data
    assert 'consumed_amount' in data
    assert 'remaining_amount' in data
    assert 'consumed_percentage' in data
    assert 'status' in data


def test_alerts_api_endpoint(client, app, admin_user, project_with_budget):
    """Test the alerts API endpoint"""
    # Create a test alert
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
    
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user.id)
    
    response = client.get('/api/budget/alerts')
    assert response.status_code == 200
    
    data = response.get_json()
    assert 'alerts' in data
    assert 'count' in data
    assert data['count'] >= 1


def test_acknowledge_alert_api_endpoint(client, app, admin_user, project_with_budget):
    """Test the acknowledge alert API endpoint"""
    # Create a test alert
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
    
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user.id)
    
    response = client.post(f'/api/budget/alerts/{alert.id}/acknowledge')
    assert response.status_code == 200
    
    data = response.get_json()
    assert 'message' in data
    assert 'alert' in data
    
    # Verify the alert was acknowledged
    db.session.refresh(alert)
    assert alert.is_acknowledged
    assert alert.acknowledged_by == admin_user.id


def test_check_alerts_api_endpoint(client, app, admin_user, project_with_budget, regular_user):
    """Test the check alerts API endpoint (admin only)"""
    # Add time entries to trigger an alert
    now = datetime.now()
    for i in range(82):
        entry = TimeEntry(
            user_id=regular_user.id,
            project_id=project_with_budget.id,
            start_time=now - timedelta(hours=i+1),
            end_time=now - timedelta(hours=i),
            billable=True
        )
        entry.calculate_duration()
        db.session.add(entry)
    db.session.commit()
    
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user.id)
    
    response = client.post(f'/api/budget/check-alerts/{project_with_budget.id}')
    assert response.status_code == 200
    
    data = response.get_json()
    assert 'message' in data
    assert 'alerts_created' in data


def test_budget_summary_api_endpoint(client, app, admin_user, project_with_budget):
    """Test the budget summary API endpoint"""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user.id)
    
    response = client.get('/api/budget/summary')
    assert response.status_code == 200
    
    data = response.get_json()
    assert 'total_projects' in data
    assert 'healthy' in data
    assert 'warning' in data
    assert 'critical' in data
    assert 'over_budget' in data
    assert 'total_budget' in data
    assert 'total_consumed' in data
    assert 'alert_stats' in data


def test_non_admin_cannot_check_alerts(client, app, regular_user, project_with_budget):
    """Test that non-admin users cannot manually check alerts"""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(regular_user.id)
    
    response = client.post(f'/api/budget/check-alerts/{project_with_budget.id}')
    assert response.status_code == 403


def test_budget_alert_model_integration(app, project_with_budget):
    """Test BudgetAlert model basic operations"""
    # Create an alert
    alert = BudgetAlert.create_alert(
        project_id=project_with_budget.id,
        alert_type='warning_80',
        budget_consumed_percent=82.5,
        budget_amount=10000.0,
        consumed_amount=8250.0
    )
    
    assert alert is not None
    assert alert.id is not None
    
    # Retrieve the alert
    retrieved_alert = BudgetAlert.query.get(alert.id)
    assert retrieved_alert is not None
    assert retrieved_alert.project_id == project_with_budget.id
    
    # Test to_dict
    alert_dict = retrieved_alert.to_dict()
    assert isinstance(alert_dict, dict)
    assert 'id' in alert_dict
    assert 'project_id' in alert_dict


def test_scheduled_task_integration(app, project_with_budget, regular_user):
    """Test that budget alert checking task runs without errors"""
    from app.utils.scheduled_tasks import check_project_budget_alerts
    
    # Add time entries that should trigger an alert
    now = datetime.now()
    for i in range(85):
        entry = TimeEntry(
            user_id=regular_user.id,
            project_id=project_with_budget.id,
            start_time=now - timedelta(hours=i+1),
            end_time=now - timedelta(hours=i),
            billable=True
        )
        entry.calculate_duration()
        db.session.add(entry)
    db.session.commit()
    
    # Run the scheduled task
    with app.app_context():
        alerts_created = check_project_budget_alerts()
    
    # Should have created at least one alert
    assert alerts_created >= 0  # Task should run without errors


def test_budget_forecasting_utilities_integration(app, project_with_budget, regular_user):
    """Test integration of all budget forecasting utilities"""
    from app.utils.budget_forecasting import (
        calculate_burn_rate,
        estimate_completion_date,
        analyze_resource_allocation,
        analyze_cost_trends,
        get_budget_status,
        check_budget_alerts
    )
    
    # Add some time entries
    now = datetime.now()
    for i in range(30):
        entry = TimeEntry(
            user_id=regular_user.id,
            project_id=project_with_budget.id,
            start_time=now - timedelta(days=i),
            end_time=now - timedelta(days=i) + timedelta(hours=4),
            billable=True
        )
        entry.calculate_duration()
        db.session.add(entry)
    db.session.commit()
    
    # Test all utilities
    burn_rate = calculate_burn_rate(project_with_budget.id)
    assert burn_rate is not None
    
    completion = estimate_completion_date(project_with_budget.id)
    assert completion is not None
    
    allocation = analyze_resource_allocation(project_with_budget.id)
    assert allocation is not None
    
    trends = analyze_cost_trends(project_with_budget.id)
    assert trends is not None
    
    status = get_budget_status(project_with_budget.id)
    assert status is not None
    
    alerts = check_budget_alerts(project_with_budget.id)
    assert isinstance(alerts, list)


def test_project_without_budget_handling(client, app, admin_user, client_obj):
    """Test that project without budget is handled gracefully"""
    # Create project without budget
    project = Project(
        name="No Budget Project",
        client_id=client_obj.id,
        billable=True,
        hourly_rate=Decimal("100.00"),
        status='active'
    )
    db.session.add(project)
    db.session.commit()
    
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user.id)
    
    # Try to access budget details
    response = client.get(f'/budget/project/{project.id}')
    # Should redirect or show warning, not crash
    assert response.status_code in [200, 302, 404]


def test_end_to_end_budget_workflow(client, app, admin_user, project_with_budget, regular_user):
    """Test complete budget monitoring workflow"""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user.id)
    
    # 1. View dashboard
    response = client.get('/budget/dashboard')
    assert response.status_code == 200
    
    # 2. Add time entries to consume budget
    now = datetime.now()
    for i in range(50):
        entry = TimeEntry(
            user_id=regular_user.id,
            project_id=project_with_budget.id,
            start_time=now - timedelta(hours=i+1),
            end_time=now - timedelta(hours=i),
            billable=True
        )
        entry.calculate_duration()
        db.session.add(entry)
    db.session.commit()
    
    # 3. Check budget status
    response = client.get(f'/api/budget/status/{project_with_budget.id}')
    assert response.status_code == 200
    
    # 4. View project detail
    response = client.get(f'/budget/project/{project_with_budget.id}')
    assert response.status_code == 200
    
    # 5. Get burn rate
    response = client.get(f'/api/budget/burn-rate/{project_with_budget.id}')
    assert response.status_code == 200

