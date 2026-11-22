"""Tests for bulk time entry actions."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app import db
from app.models import TimeEntry
from app.services.time_entry_bulk_service import apply_bulk_time_entry_actions

pytestmark = [pytest.mark.unit]


@patch("app.services.time_entry_bulk_service.safe_commit")
@patch("app.services.time_entry_bulk_service.db")
def test_bulk_all_active_entries_returns_400(mock_db, mock_safe_commit):
    e = MagicMock()
    e.user_id = 1
    e.is_active = True

    mock_q = MagicMock()
    mock_q.all.return_value = [e]

    with patch("app.services.time_entry_bulk_service.TimeEntry") as TE:
        TE.query.filter.return_value = mock_q
        result = apply_bulk_time_entry_actions(
            [99],
            "set_billable",
            True,
            user_id=1,
            is_admin=False,
        )

    assert result["success"] is False
    assert result["http_status"] == 400
    assert "active" in result["error"].lower()
    mock_db.session.rollback.assert_called()
    mock_safe_commit.assert_not_called()


@pytest.mark.unit
def test_bulk_empty_entry_ids(app):
    result = apply_bulk_time_entry_actions([], "delete", None, user_id=1, is_admin=False)
    assert result["success"] is False
    assert result["http_status"] == 400


@pytest.mark.unit
def test_bulk_set_billable(app, user, project):
    start = datetime.utcnow() - timedelta(hours=3)
    end = datetime.utcnow() - timedelta(hours=2)
    entry = TimeEntry(
        user_id=user.id,
        project_id=project.id,
        start_time=start,
        end_time=end,
        source="manual",
        billable=False,
    )
    db.session.add(entry)
    db.session.commit()

    result = apply_bulk_time_entry_actions(
        [entry.id],
        "set_billable",
        True,
        user_id=user.id,
        is_admin=False,
    )

    assert result["success"] is True
    assert result["affected"] == 1
    db.session.refresh(entry)
    assert entry.billable is True


@pytest.mark.unit
def test_bulk_delete_completed_entry(app, user, project):
    start = datetime.utcnow() - timedelta(hours=3)
    end = datetime.utcnow() - timedelta(hours=2)
    entry = TimeEntry(
        user_id=user.id,
        project_id=project.id,
        start_time=start,
        end_time=end,
        source="manual",
    )
    db.session.add(entry)
    db.session.commit()
    entry_id = entry.id

    result = apply_bulk_time_entry_actions(
        [entry_id],
        "delete",
        None,
        user_id=user.id,
        is_admin=False,
    )

    assert result["success"] is True
    assert result["affected"] == 1
    assert TimeEntry.query.get(entry_id) is None


@pytest.mark.unit
def test_bulk_access_denied_other_users_entry(app, user, project, admin_user):
    start = datetime.utcnow() - timedelta(hours=3)
    end = datetime.utcnow() - timedelta(hours=2)
    entry = TimeEntry(
        user_id=admin_user.id,
        project_id=project.id,
        start_time=start,
        end_time=end,
        source="manual",
    )
    db.session.add(entry)
    db.session.commit()

    result = apply_bulk_time_entry_actions(
        [entry.id],
        "delete",
        None,
        user_id=user.id,
        is_admin=False,
    )

    assert result["success"] is False
    assert result["http_status"] == 403


def _completed_entry(user, project, *, paid=False, billable=True, hours_ago=3):
    start = datetime.utcnow() - timedelta(hours=hours_ago)
    entry = TimeEntry(
        user_id=user.id,
        project_id=project.id,
        start_time=start,
        end_time=start + timedelta(hours=1),
        source="manual",
        billable=billable,
    )
    entry.paid = paid
    db.session.add(entry)
    db.session.commit()
    return entry


@pytest.mark.unit
def test_bulk_set_billable_skips_invoiced_and_running_entries(app, user, project):
    open_entry = _completed_entry(user, project)
    paid_entry = _completed_entry(user, project, paid=True, hours_ago=5)
    running = TimeEntry(
        user_id=user.id, project_id=project.id, start_time=datetime.utcnow(), source="auto", billable=True
    )
    db.session.add(running)
    db.session.commit()

    result = apply_bulk_time_entry_actions(
        [open_entry.id, paid_entry.id, running.id],
        "set_billable",
        False,
        user_id=user.id,
        is_admin=False,
    )

    assert result["success"] is True
    assert result["affected"] == 1
    assert result["affected_ids"] == [open_entry.id]
    assert result["skipped"] == 2
    assert result["skipped_reasons"] == {"already_invoiced": 1, "timer_running": 1}
    db.session.expire_all()
    assert TimeEntry.query.get(open_entry.id).billable is False
    assert TimeEntry.query.get(paid_entry.id).billable is True
    assert TimeEntry.query.get(running.id).billable is True


@pytest.mark.unit
def test_bulk_set_billable_all_invoiced_returns_400_with_counts(app, user, project):
    paid_entry = _completed_entry(user, project, paid=True)

    result = apply_bulk_time_entry_actions([paid_entry.id], "set_billable", False, user_id=user.id, is_admin=False)

    assert result["success"] is False
    assert result["http_status"] == 400
    assert "invoiced" in result["error"]
    assert result["skipped"] == 1
    assert result["skipped_reasons"] == {"already_invoiced": 1}
    db.session.expire_all()
    assert TimeEntry.query.get(paid_entry.id).billable is True


@pytest.mark.unit
def test_bulk_set_paid_does_not_skip_paid_entries(app, user, project):
    paid_entry = _completed_entry(user, project, paid=True)

    result = apply_bulk_time_entry_actions([paid_entry.id], "set_paid", False, user_id=user.id, is_admin=False)

    assert result["success"] is True
    assert result["affected"] == 1
    assert result["skipped"] == 0
    assert result["skipped_reasons"] == {}


@pytest.mark.unit
def test_bulk_set_project_and_task(app, user, project, task, test_client):
    from app.models import Project

    other = Project(
        name="Other Bulk Project",
        client_id=test_client.id,
        description="bulk move target",
        billable=True,
    )
    db.session.add(other)
    db.session.commit()

    entry = _completed_entry(user, project)
    entry.task_id = task.id
    db.session.commit()

    moved = apply_bulk_time_entry_actions(
        [entry.id],
        "set_project",
        other.id,
        user_id=user.id,
        is_admin=False,
    )
    assert moved["success"] is True
    db.session.refresh(entry)
    assert entry.project_id == other.id
    assert entry.task_id is None  # cleared — task belonged to old project

    # Move back, then set task on matching project
    apply_bulk_time_entry_actions([entry.id], "set_project", project.id, user_id=user.id, is_admin=False)
    tasked = apply_bulk_time_entry_actions(
        [entry.id],
        "set_task",
        task.id,
        user_id=user.id,
        is_admin=False,
    )
    assert tasked["success"] is True
    db.session.refresh(entry)
    assert entry.task_id == task.id


@pytest.mark.unit
def test_bulk_set_project_skips_invoiced(app, user, project, test_client):
    from app.models import Project

    other = Project(name="Paid Skip Project", client_id=test_client.id, description="x", billable=True)
    db.session.add(other)
    db.session.commit()
    paid_entry = _completed_entry(user, project, paid=True)

    result = apply_bulk_time_entry_actions(
        [paid_entry.id],
        "set_project",
        other.id,
        user_id=user.id,
        is_admin=False,
    )
    assert result["success"] is False
    assert result["skipped_reasons"] == {"already_invoiced": 1}
    db.session.refresh(paid_entry)
    assert paid_entry.project_id == project.id
