"""
Test suite for Weekly Time Goals feature.
Tests model creation, calculations, relationships, routes, and business logic.
"""

import pytest
from datetime import datetime, timedelta, date
from app.models import WeeklyTimeGoal, TimeEntry, User, Project
from app import db
from factories import TimeEntryFactory


# ============================================================================
# WeeklyTimeGoal Model Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.models
@pytest.mark.smoke
def test_weekly_goal_creation(app, user):
    """Test basic weekly time goal creation."""
    with app.app_context():
        week_start = date.today() - timedelta(days=date.today().weekday())
        goal = WeeklyTimeGoal(
            user_id=user.id,
            target_hours=40.0,
            week_start_date=week_start
        )
        db.session.add(goal)
        db.session.commit()
        
        assert goal.id is not None
        assert goal.target_hours == 40.0
        assert goal.week_start_date == week_start
        assert goal.week_end_date == week_start + timedelta(days=6)
        assert goal.status == 'active'
        assert goal.created_at is not None
        assert goal.updated_at is not None


@pytest.mark.unit
@pytest.mark.models
def test_weekly_goal_default_week(app, user):
    """Test weekly goal creation with default week (current week)."""
    with app.app_context():
        goal = WeeklyTimeGoal(
            user_id=user.id,
            target_hours=40.0
        )
        db.session.add(goal)
        db.session.commit()
        
        # Should default to current week's Monday
        today = date.today()
        expected_week_start = today - timedelta(days=today.weekday())
        
        assert goal.week_start_date == expected_week_start
        assert goal.week_end_date == expected_week_start + timedelta(days=6)


@pytest.mark.unit
@pytest.mark.models
def test_weekly_goal_with_notes(app, user):
    """Test weekly goal with notes."""
    with app.app_context():
        goal = WeeklyTimeGoal(
            user_id=user.id,
            target_hours=35.0,
            notes="Vacation week, reduced hours"
        )
        db.session.add(goal)
        db.session.commit()
        
        assert goal.notes == "Vacation week, reduced hours"


@pytest.mark.unit
@pytest.mark.models
def test_weekly_goal_actual_hours_calculation(app, user, project):
    """Test calculation of actual hours worked."""
    with app.app_context():
        week_start = date.today() - timedelta(days=date.today().weekday())
        goal = WeeklyTimeGoal(
            user_id=user.id,
            target_hours=40.0,
            week_start_date=week_start
        )
        db.session.add(goal)
        db.session.commit()
        
        # Add time entries for the week
        TimeEntryFactory(
            user_id=user.id,
            project_id=project.id,
            start_time=datetime.combine(week_start, datetime.min.time()),
            end_time=datetime.combine(week_start, datetime.min.time()) + timedelta(hours=8),
            duration_seconds=8 * 3600
        )
        TimeEntryFactory(
            user_id=user.id,
            project_id=project.id,
            start_time=datetime.combine(week_start + timedelta(days=1), datetime.min.time()),
            end_time=datetime.combine(week_start + timedelta(days=1), datetime.min.time()) + timedelta(hours=7),
            duration_seconds=7 * 3600
        )
        
        # Refresh goal to get calculated properties
        db.session.refresh(goal)
        
        assert goal.actual_hours == 15.0


@pytest.mark.unit
@pytest.mark.models
def test_weekly_goal_progress_percentage(app, user, project):
    """Test progress percentage calculation."""
    with app.app_context():
        week_start = date.today() - timedelta(days=date.today().weekday())
        goal = WeeklyTimeGoal(
            user_id=user.id,
            target_hours=40.0,
            week_start_date=week_start
        )
        db.session.add(goal)
        db.session.commit()
        
        # Add time entry
        TimeEntryFactory(
            user_id=user.id,
            project_id=project.id,
            start_time=datetime.combine(week_start, datetime.min.time()),
            end_time=datetime.combine(week_start, datetime.min.time()) + timedelta(hours=20),
            duration_seconds=20 * 3600
        )
        
        db.session.refresh(goal)
        
        # 20 hours out of 40 = 50%
        assert goal.progress_percentage == 50.0


@pytest.mark.unit
@pytest.mark.models
def test_weekly_goal_remaining_hours(app, user, project):
    """Test remaining hours calculation."""
    with app.app_context():
        week_start = date.today() - timedelta(days=date.today().weekday())
        goal = WeeklyTimeGoal(
            user_id=user.id,
            target_hours=40.0,
            week_start_date=week_start
        )
        db.session.add(goal)
        db.session.commit()
        
        # Add time entry
        TimeEntryFactory(
            user_id=user.id,
            project_id=project.id,
            start_time=datetime.combine(week_start, datetime.min.time()),
            end_time=datetime.combine(week_start, datetime.min.time()) + timedelta(hours=15),
            duration_seconds=15 * 3600
        )
        
        db.session.refresh(goal)
        
        assert goal.remaining_hours == 25.0


@pytest.mark.unit
@pytest.mark.models
def test_weekly_goal_is_completed(app, user, project):
    """Test is_completed property."""
    with app.app_context():
        week_start = date.today() - timedelta(days=date.today().weekday())
        goal = WeeklyTimeGoal(
            user_id=user.id,
            target_hours=20.0,
            week_start_date=week_start
        )
        db.session.add(goal)
        db.session.commit()
        
        db.session.refresh(goal)
        assert goal.is_completed is False
        
        # Add time entry to complete goal
        TimeEntryFactory(
            user_id=user.id,
            project_id=project.id,
            start_time=datetime.combine(week_start, datetime.min.time()),
            end_time=datetime.combine(week_start, datetime.min.time()) + timedelta(hours=20),
            duration_seconds=20 * 3600
        )
        
        db.session.refresh(goal)
        assert goal.is_completed is True


@pytest.mark.unit
@pytest.mark.models
def test_weekly_goal_average_hours_per_day(app, user, project):
    """Test average hours per day calculation."""
    with app.app_context():
        week_start = date.today() - timedelta(days=date.today().weekday())
        goal = WeeklyTimeGoal(
            user_id=user.id,
            target_hours=40.0,
            week_start_date=week_start
        )
        db.session.add(goal)
        db.session.commit()
        
        # Add time entry for 10 hours
        TimeEntryFactory(
            user_id=user.id,
            project_id=project.id,
            start_time=datetime.combine(week_start, datetime.min.time()),
            end_time=datetime.combine(week_start, datetime.min.time()) + timedelta(hours=10),
            duration_seconds=10 * 3600
        )
        
        db.session.refresh(goal)
        
        # Remaining: 30 hours, Days remaining: depends on current day
        if goal.days_remaining > 0:
            expected_avg = round(goal.remaining_hours / goal.days_remaining, 2)
            assert goal.average_hours_per_day == expected_avg


@pytest.mark.unit
@pytest.mark.models
def test_weekly_goal_week_label(app, user):
    """Test week label generation."""
    with app.app_context():
        week_start = date(2024, 1, 1)  # A Monday
        goal = WeeklyTimeGoal(
            user_id=user.id,
            target_hours=40.0,
            week_start_date=week_start
        )
        db.session.add(goal)
        db.session.commit()
        
        assert "Jan 01" in goal.week_label
        assert "Jan 07" in goal.week_label


@pytest.mark.unit
@pytest.mark.models
def test_weekly_goal_status_update_completed(app, user, project):
    """Test automatic status update to completed."""
    with app.app_context():
        # Create goal for past week
        week_start = date.today() - timedelta(days=14)
        goal = WeeklyTimeGoal(
            user_id=user.id,
            target_hours=20.0,
            week_start_date=week_start,
            status='active'
        )
        db.session.add(goal)
        db.session.commit()
        
        # Add time entry to meet goal
        TimeEntryFactory(
            user_id=user.id,
            project_id=project.id,
            start_time=datetime.combine(week_start, datetime.min.time()),
            end_time=datetime.combine(week_start, datetime.min.time()) + timedelta(hours=20),
            duration_seconds=20 * 3600
        )
        
        goal.update_status()
        db.session.commit()
        
        assert goal.status == 'completed'


@pytest.mark.unit
@pytest.mark.models
def test_weekly_goal_status_update_failed(app, user, project):
    """Test automatic status update to failed."""
    with app.app_context():
        # Create goal for past week
        week_start = date.today() - timedelta(days=14)
        goal = WeeklyTimeGoal(
            user_id=user.id,
            target_hours=40.0,
            week_start_date=week_start,
            status='active'
        )
        db.session.add(goal)
        db.session.commit()
        
        # Add time entry that doesn't meet goal
        TimeEntryFactory(
            user_id=user.id,
            project_id=project.id,
            start_time=datetime.combine(week_start, datetime.min.time()),
            end_time=datetime.combine(week_start, datetime.min.time()) + timedelta(hours=20),
            duration_seconds=20 * 3600
        )
        
        goal.update_status()
        db.session.commit()
        
        assert goal.status == 'failed'


@pytest.mark.unit
@pytest.mark.models
def test_weekly_goal_get_current_week(app, user):
    """Test getting current week's goal."""
    with app.app_context():
        # Create goal for current week
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        
        goal = WeeklyTimeGoal(
            user_id=user.id,
            target_hours=40.0,
            week_start_date=week_start
        )
        db.session.add(goal)
        db.session.commit()
        
        # Get current week goal
        current_goal = WeeklyTimeGoal.get_current_week_goal(user.id)
        
        assert current_goal is not None
        assert current_goal.id == goal.id


@pytest.mark.unit
@pytest.mark.models
def test_weekly_goal_to_dict(app, user):
    """Test goal serialization to dictionary."""
    with app.app_context():
        goal = WeeklyTimeGoal(
            user_id=user.id,
            target_hours=40.0,
            notes="Test notes"
        )
        db.session.add(goal)
        db.session.commit()
        
        goal_dict = goal.to_dict()
        
        assert 'id' in goal_dict
        assert 'user_id' in goal_dict
        assert 'target_hours' in goal_dict
        assert 'actual_hours' in goal_dict
        assert 'week_start_date' in goal_dict
        assert 'week_end_date' in goal_dict
        assert 'status' in goal_dict
        assert 'notes' in goal_dict
        assert 'progress_percentage' in goal_dict
        assert 'remaining_hours' in goal_dict
        assert 'is_completed' in goal_dict
        
        assert goal_dict['target_hours'] == 40.0
        assert goal_dict['notes'] == "Test notes"


# ============================================================================
# WeeklyTimeGoal Routes Tests
# ============================================================================

@pytest.mark.smoke
def test_weekly_goals_index_page(authenticated_client):
    """Test weekly goals index page loads."""
    response = authenticated_client.get('/goals')
    assert response.status_code == 200


@pytest.mark.smoke
def test_weekly_goals_create_page(authenticated_client):
    """Test weekly goals create page loads."""
    response = authenticated_client.get('/goals/create')
    assert response.status_code == 200


@pytest.mark.smoke
def test_create_weekly_goal_via_form(authenticated_client, app, user):
    """Test creating a weekly goal via form submission."""
    with app.app_context():
        data = {
            'target_hours': 40.0,
            'notes': 'Test goal'
        }
        response = authenticated_client.post('/goals/create', data=data, follow_redirects=True)
        assert response.status_code == 200
        
        # Check goal was created
        goal = WeeklyTimeGoal.query.filter_by(user_id=user.id).first()
        assert goal is not None
        assert goal.target_hours == 40.0


@pytest.mark.smoke
def test_edit_weekly_goal(authenticated_client, app, user):
    """Test editing a weekly goal."""
    with app.app_context():
        goal = WeeklyTimeGoal(
            user_id=user.id,
            target_hours=40.0
        )
        db.session.add(goal)
        db.session.commit()
        goal_id = goal.id
    
    # Update goal (POST request happens outside app context)
    data = {
        'target_hours': 35.0,
        'notes': 'Updated notes',
        'status': 'active'
    }
    response = authenticated_client.post(f'/goals/{goal_id}/edit', data=data, follow_redirects=True)
    assert response.status_code == 200
    
    # Check goal was updated - re-query within app context
    with app.app_context():
        goal = WeeklyTimeGoal.query.get(goal_id)
        assert goal is not None, "Goal should still exist after edit"
        assert goal.target_hours == 35.0, f"Expected 35.0, got {goal.target_hours}"
        assert goal.notes == 'Updated notes'


@pytest.mark.smoke
def test_delete_weekly_goal(authenticated_client, app, user):
    """Test deleting a weekly goal."""
    with app.app_context():
        goal = WeeklyTimeGoal(
            user_id=user.id,
            target_hours=40.0
        )
        db.session.add(goal)
        db.session.commit()
        goal_id = goal.id
    
    # Delete goal (POST request happens outside app context)
    response = authenticated_client.post(f'/goals/{goal_id}/delete', follow_redirects=True)
    assert response.status_code == 200
    
    # Check goal was deleted - re-query within app context
    with app.app_context():
        deleted_goal = WeeklyTimeGoal.query.get(goal_id)
        assert deleted_goal is None, f"Goal should be deleted but found: {deleted_goal}"


@pytest.mark.smoke
def test_view_weekly_goal(authenticated_client, app, user):
    """Test viewing a specific weekly goal."""
    # Create goal outside app context to ensure it persists
    goal = WeeklyTimeGoal(
        user_id=user.id,
        target_hours=40.0
    )
    with app.app_context():
        db.session.add(goal)
        db.session.commit()
        goal_id = goal.id
    
    response = authenticated_client.get(f'/goals/{goal_id}')
    assert response.status_code == 200


# ============================================================================
# API Endpoints Tests
# ============================================================================

@pytest.mark.smoke
def test_api_get_current_goal(authenticated_client, app, user):
    """Test API endpoint for getting current week's goal."""
    # Create goal outside app context to ensure it persists
    goal = WeeklyTimeGoal(
        user_id=user.id,
        target_hours=40.0
    )
    with app.app_context():
        db.session.add(goal)
        db.session.commit()
    
    response = authenticated_client.get('/api/goals/current')
    assert response.status_code == 200
    
    data = response.get_json()
    assert 'target_hours' in data
    assert data['target_hours'] == 40.0


@pytest.mark.smoke
def test_api_list_goals(authenticated_client, app, user):
    """Test API endpoint for listing goals."""
    # Create multiple goals
    goals = []
    for i in range(3):
        goal = WeeklyTimeGoal(
            user_id=user.id,
            target_hours=40.0,
            week_start_date=date.today() - timedelta(weeks=i, days=date.today().weekday())
        )
        goals.append(goal)
    
    with app.app_context():
        for goal in goals:
            db.session.add(goal)
        db.session.commit()
    
    response = authenticated_client.get('/api/goals')
    assert response.status_code == 200
    
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 3


@pytest.mark.smoke
def test_api_get_goal_stats(authenticated_client, app, user, project):
    """Test API endpoint for goal statistics."""
    # Create a few goals (their actual status will be determined by update_status)
    # Goal 1: Completed in the past with enough hours
    past_week_start = date.today() - timedelta(days=14)
    goal1 = WeeklyTimeGoal(
        user_id=user.id,
        target_hours=40.0,
        week_start_date=past_week_start
    )
    
    # Goal 2: Active week
    current_week_start = date.today() - timedelta(days=date.today().weekday())
    goal2 = WeeklyTimeGoal(
        user_id=user.id,
        target_hours=40.0,
        week_start_date=current_week_start
    )
    
    with app.app_context():
        db.session.add(goal1)
        db.session.add(goal2)
        db.session.commit()
    
    response = authenticated_client.get('/api/goals/stats')
    assert response.status_code == 200
    
    data = response.get_json()
    # Verify the structure is correct
    assert 'total_goals' in data
    assert 'completed' in data
    assert 'failed' in data
    assert 'active' in data
    assert 'completion_rate' in data
    assert data['total_goals'] == 2
    # Verify counts are consistent (completed + failed + active + cancelled should equal total)
    assert (data.get('completed', 0) + data.get('failed', 0) + 
            data.get('active', 0) + data.get('cancelled', 0)) == data['total_goals']


@pytest.mark.unit
def test_weekly_goal_user_relationship(app, user):
    """Test weekly goal user relationship."""
    with app.app_context():
        goal = WeeklyTimeGoal(
            user_id=user.id,
            target_hours=40.0
        )
        db.session.add(goal)
        db.session.commit()
        
        db.session.refresh(goal)
        assert goal.user is not None
        assert goal.user.id == user.id


@pytest.mark.unit
def test_user_has_weekly_goals_relationship(app, user):
    """Test that user has weekly_goals relationship."""
    with app.app_context():
        # Re-query the user to ensure it's in the current session
        from app.models import User
        user_obj = User.query.get(user.id)
        
        goal1 = WeeklyTimeGoal(user_id=user_obj.id, target_hours=40.0)
        goal2 = WeeklyTimeGoal(
            user_id=user_obj.id,
            target_hours=35.0,
            week_start_date=date.today() - timedelta(weeks=1, days=date.today().weekday())
        )
        db.session.add_all([goal1, goal2])
        db.session.commit()
        
        db.session.refresh(user_obj)
        assert user_obj.weekly_goals.count() >= 2

