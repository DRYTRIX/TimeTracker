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
