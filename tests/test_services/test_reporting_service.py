"""
Tests for ReportingService.
"""

import pytest
from datetime import datetime, timedelta
from app.services import ReportingService
from app.models import TimeEntry, Project, User
from app import db


@pytest.mark.unit
def test_get_reports_summary(app, test_user, test_project):
    """Test getting reports summary"""
    service = ReportingService()
    
    # Create some time entries
    entry = TimeEntry(
        user_id=test_user.id,
        project_id=test_project.id,
        start_time=datetime.utcnow() - timedelta(hours=2),
        end_time=datetime.utcnow(),
        duration_seconds=7200,  # 2 hours
        billable=True
    )
    db.session.add(entry)
    db.session.commit()
    
    # Get summary
    result = service.get_reports_summary(
        user_id=test_user.id,
        is_admin=False
    )
    
    assert result['summary'] is not None
    assert 'total_hours' in result['summary']
    assert 'billable_hours' in result['summary']
    assert result['recent_entries'] is not None
    assert result['comparison'] is not None


@pytest.mark.unit
def test_get_time_summary(app, test_user, test_project):
    """Test getting time summary"""
    service = ReportingService()
    
    # Create time entries
    entry = TimeEntry(
        user_id=test_user.id,
        project_id=test_project.id,
        start_time=datetime.utcnow() - timedelta(hours=1),
        end_time=datetime.utcnow(),
        duration_seconds=3600,  # 1 hour
        billable=True
    )
    db.session.add(entry)
    db.session.commit()
    
    # Get time summary
    summary = service.get_time_summary(
        user_id=test_user.id,
        billable_only=False
    )
    
    assert summary['total_hours'] >= 0
    assert summary['billable_hours'] >= 0
    assert summary['total_entries'] >= 1


@pytest.mark.unit
def test_get_project_summary(app, test_project, test_user):
    """Test getting project summary"""
    service = ReportingService()
    
    # Create time entry for project
    entry = TimeEntry(
        user_id=test_user.id,
        project_id=test_project.id,
        start_time=datetime.utcnow() - timedelta(hours=1),
        end_time=datetime.utcnow(),
        duration_seconds=3600,
        billable=True
    )
    db.session.add(entry)
    db.session.commit()
    
    # Get project summary
    summary = service.get_project_summary(
        project_id=test_project.id
    )
    
    assert 'error' not in summary
    assert 'time_summary' in summary or 'total_hours' in summary

