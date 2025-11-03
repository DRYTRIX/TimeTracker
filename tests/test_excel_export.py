"""
Tests for Excel export functionality
"""
import pytest
from datetime import datetime, timedelta
from app.models import TimeEntry, Task


@pytest.mark.unit
@pytest.mark.routes
def test_create_time_entries_excel_with_client(app, user, project, test_client):
    """Test that Excel export handles project.client correctly as a string property"""
    from app.utils.excel_export import create_time_entries_excel
    
    # Create a time entry with project that has a client
    start_time = datetime.utcnow() - timedelta(hours=2)
    end_time = datetime.utcnow()
    
    entry = TimeEntry(
        user_id=user.id,
        project_id=project.id,
        start_time=start_time,
        end_time=end_time,
        notes='Test entry for Excel export',
        tags='test,export',
        source='manual',
        billable=True
    )
    
    # Calculate duration manually since we're not going through the full commit cycle
    entry.duration_seconds = (end_time - start_time).total_seconds()
    
    # Test that project.client is a string property, not an object
    assert hasattr(project, 'client')
    assert isinstance(project.client, str)
    assert project.client == test_client.name
    
    # Test Excel export function
    output, filename = create_time_entries_excel([entry])
    
    # Verify the output was created successfully
    assert output is not None
    assert filename is not None
    assert filename.endswith('.xlsx')
    
    # Verify the file content can be read
    output.seek(0)
    content = output.read()
    assert len(content) > 0


@pytest.mark.unit
@pytest.mark.routes  
def test_create_time_entries_excel_with_task(app, user, project, task):
    """Test that Excel export handles entries with tasks correctly"""
    from app.utils.excel_export import create_time_entries_excel
    
    # Create a time entry with a task
    start_time = datetime.utcnow() - timedelta(hours=1)
    end_time = datetime.utcnow()
    
    entry = TimeEntry(
        user_id=user.id,
        project_id=project.id,
        task_id=task.id,
        start_time=start_time,
        end_time=end_time,
        notes='Test entry with task',
        billable=True
    )
    
    # Calculate duration
    entry.duration_seconds = (end_time - start_time).total_seconds()
    
    # Test Excel export function
    output, filename = create_time_entries_excel([entry])
    
    # Verify the output was created successfully
    assert output is not None
    assert filename is not None
    
    # Verify the file content can be read
    output.seek(0)
    content = output.read()
    assert len(content) > 0


@pytest.mark.unit
@pytest.mark.routes
def test_create_time_entries_excel_multiple_entries(app, multiple_time_entries):
    """Test Excel export with multiple time entries"""
    from app.utils.excel_export import create_time_entries_excel
    
    # Test Excel export function with multiple entries
    output, filename = create_time_entries_excel(multiple_time_entries)
    
    # Verify the output was created successfully
    assert output is not None
    assert filename is not None
    
    # Verify the file content can be read
    output.seek(0)
    content = output.read()
    assert len(content) > 0


@pytest.mark.unit  
@pytest.mark.routes
def test_project_report_excel_export(app, time_entry):
    """Test project report Excel export with project.client"""
    from app.utils.excel_export import create_project_report_excel
    
    # Create project data structure
    project = time_entry.project
    projects_data = [{
        'name': project.name,
        'client': project.client,  # Should be a string
        'total_hours': 8.0,
        'billable_hours': 7.5,
        'hourly_rate': 75.00,
        'billable_amount': 562.50,
        'total_costs': 0,
        'total_value': 562.50
    }]
    
    # Test that project.client is a string
    assert isinstance(project.client, str)
    
    # Test Excel export function
    output, filename = create_project_report_excel(
        projects_data, 
        start_date='2024-01-01', 
        end_date='2024-12-31'
    )
    
    # Verify the output was created successfully
    assert output is not None
    assert filename is not None
    
    # Verify the file content can be read
    output.seek(0)
    content = output.read()
    assert len(content) > 0

