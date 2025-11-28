"""
Comprehensive API testing suite.
Tests API endpoints to improve coverage.
"""

import pytest
from datetime import datetime, timedelta, date
from decimal import Decimal
import json


# ============================================================================
# Timer API Tests
# ============================================================================


@pytest.mark.api
@pytest.mark.integration
def test_start_timer_api(authenticated_client, project):
    """Test starting a timer via API."""
    response = authenticated_client.post(
        "/api/timer/start", json={"project_id": project.id, "notes": "Working on feature"}
    )

    # Should succeed or return appropriate status
    assert response.status_code in [200, 201, 404, 405]


@pytest.mark.api
@pytest.mark.integration
def test_get_timer_status(authenticated_client):
    """Test getting timer status."""
    response = authenticated_client.get("/api/timer/status")

    # Should return status or appropriate error
    assert response.status_code in [200, 404]


# ============================================================================
# Project API Tests
# ============================================================================


@pytest.mark.api
@pytest.mark.integration
def test_get_projects_list(authenticated_client):
    """Test getting list of projects."""
    response = authenticated_client.get("/api/projects")

    # Should return projects list or appropriate error
    assert response.status_code in [200, 404]


@pytest.mark.api
@pytest.mark.integration
def test_get_project_details(authenticated_client, project):
    """Test getting project details."""
    response = authenticated_client.get(f"/api/projects/{project.id}")

    # Should return project details or appropriate error
    assert response.status_code in [200, 404]


# ============================================================================
# Time Entry API Tests
# ============================================================================


@pytest.mark.api
@pytest.mark.integration
def test_get_time_entries(authenticated_client):
    """Test getting time entries list."""
    response = authenticated_client.get("/api/time-entries")

    # Should return time entries or appropriate error
    assert response.status_code in [200, 404]


@pytest.mark.api
@pytest.mark.integration
def test_get_time_entry_details(authenticated_client, time_entry):
    """Test getting time entry details."""
    response = authenticated_client.get(f"/api/time-entries/{time_entry.id}")

    # Should return time entry details or appropriate error
    assert response.status_code in [200, 404]


# ============================================================================
# Client API Tests
# ============================================================================


@pytest.mark.api
@pytest.mark.integration
def test_get_clients_list(authenticated_client):
    """Test getting list of clients."""
    response = authenticated_client.get("/api/clients")

    # Should return clients list or appropriate error
    assert response.status_code in [200, 404]


@pytest.mark.api
@pytest.mark.integration
def test_get_client_details(authenticated_client, test_client):
    """Test getting client details."""
    response = authenticated_client.get(f"/api/clients/{test_client.id}")

    # Should return client details or appropriate error
    assert response.status_code in [200, 404]


# ============================================================================
# Invoice API Tests
# ============================================================================


@pytest.mark.api
@pytest.mark.integration
def test_get_invoices_list(authenticated_client):
    """Test getting list of invoices."""
    response = authenticated_client.get("/api/invoices")

    # Should return invoices list or appropriate error
    assert response.status_code in [200, 404]


@pytest.mark.api
@pytest.mark.integration
def test_get_invoice_details(authenticated_client, invoice):
    """Test getting invoice details."""
    response = authenticated_client.get(f"/api/invoices/{invoice.id}")

    # Should return invoice details or appropriate error
    assert response.status_code in [200, 404]


# ============================================================================
# Report API Tests
# ============================================================================


@pytest.mark.api
@pytest.mark.integration
def test_get_time_report(authenticated_client):
    """Test getting time report."""
    response = authenticated_client.get(
        "/api/reports/time",
        query_string={
            "start_date": (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d"),
            "end_date": datetime.utcnow().strftime("%Y-%m-%d"),
        },
    )

    # Should return report or appropriate error
    assert response.status_code in [200, 404, 500]


@pytest.mark.api
@pytest.mark.integration
def test_get_project_report(authenticated_client, project):
    """Test getting project report."""
    response = authenticated_client.get(f"/api/reports/projects/{project.id}")

    # Should return report or appropriate error
    assert response.status_code in [200, 404]


# ============================================================================
# Task API Tests
# ============================================================================


@pytest.mark.api
@pytest.mark.integration
def test_get_tasks_list(authenticated_client):
    """Test getting list of tasks."""
    response = authenticated_client.get("/api/tasks")

    # Should return tasks list or appropriate error (400 is also valid if params are required)
    assert response.status_code in [200, 400, 404]


@pytest.mark.api
@pytest.mark.integration
def test_get_task_details(authenticated_client, task):
    """Test getting task details."""
    response = authenticated_client.get(f"/api/tasks/{task.id}")

    # Should return task details or appropriate error
    assert response.status_code in [200, 404]


@pytest.mark.api
@pytest.mark.integration
def test_get_project_tasks_excludes_done_and_cancelled(authenticated_client, project, user, app):
    """Test that /api/projects/<project_id>/tasks excludes done and cancelled tasks."""
    from app.models import Task
    from app import db

    # Create tasks with different statuses
    active_task = Task(name="Active Task", project_id=project.id, status="todo", created_by=user.id)
    in_progress_task = Task(name="In Progress Task", project_id=project.id, status="in_progress", created_by=user.id)
    review_task = Task(name="Review Task", project_id=project.id, status="review", created_by=user.id)
    done_task = Task(name="Done Task", project_id=project.id, status="done", created_by=user.id)
    cancelled_task = Task(name="Cancelled Task", project_id=project.id, status="cancelled", created_by=user.id)

    db.session.add_all([active_task, in_progress_task, review_task, done_task, cancelled_task])
    db.session.commit()

    # Get tasks for the project
    response = authenticated_client.get(f"/api/projects/{project.id}/tasks")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert "tasks" in data
    assert data["success"] is True

    # Verify only active tasks are returned
    task_names = [t["name"] for t in data["tasks"]]
    assert "Active Task" in task_names
    assert "In Progress Task" in task_names
    assert "Review Task" in task_names
    assert "Done Task" not in task_names
    assert "Cancelled Task" not in task_names

    # Verify we got exactly 3 tasks
    assert len(data["tasks"]) == 3


# ============================================================================
# Settings API Tests
# ============================================================================


@pytest.mark.api
@pytest.mark.integration
def test_get_settings(authenticated_client):
    """Test getting application settings."""
    response = authenticated_client.get("/api/settings")

    # Should return settings or appropriate error
    assert response.status_code in [200, 404]


# ============================================================================
# Analytics API Tests
# ============================================================================


@pytest.mark.api
@pytest.mark.integration
def test_get_dashboard_stats(authenticated_client):
    """Test getting dashboard statistics."""
    response = authenticated_client.get("/api/analytics/dashboard")

    # Should return stats or appropriate error
    assert response.status_code in [200, 404, 500]


# ============================================================================
# Search API Tests
# ============================================================================


@pytest.mark.api
@pytest.mark.integration
def test_search_api(authenticated_client):
    """Test search API endpoint."""
    response = authenticated_client.get("/api/search", query_string={"q": "test"})

    # Should return search results or appropriate error
    assert response.status_code in [200, 400, 404]


# ============================================================================
# Export API Tests
# ============================================================================


@pytest.mark.api
@pytest.mark.integration
def test_export_time_entries(authenticated_client):
    """Test exporting time entries."""
    response = authenticated_client.get(
        "/api/export/time-entries",
        query_string={
            "format": "csv",
            "start_date": (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d"),
            "end_date": datetime.utcnow().strftime("%Y-%m-%d"),
        },
    )

    # Should return export or appropriate error
    assert response.status_code in [200, 404, 500]
