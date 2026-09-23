"""Tests for CSV import of time entries."""

from datetime import datetime, timedelta

import pytest

from app import db
from app.models import TimeEntry
from app.services.time_entry_csv_import_service import import_time_entries_from_csv_text

pytestmark = [pytest.mark.unit]

CSV_HEADER = "start_time,end_time,project_id,notes,billable,tags\n"


@pytest.mark.unit
def test_import_empty_csv(app, user):
    result, status = import_time_entries_from_csv_text("", user_id=user.id, is_admin=False)
    assert status == 400
    assert result["success"] is False


@pytest.mark.unit
def test_import_header_only_no_data_rows(app, user):
    result, status = import_time_entries_from_csv_text(CSV_HEADER, user_id=user.id, is_admin=False)
    assert status == 200
    assert result["success"] is True
    assert result["created"] == 0
    assert result["failed"] == 0


@pytest.mark.unit
def test_import_small_csv_success(app, user, project):
    start = datetime.utcnow() - timedelta(hours=4)
    end = datetime.utcnow() - timedelta(hours=2)
    csv_text = (
        CSV_HEADER
        + f"{start.isoformat()},{end.isoformat()},{project.id},Imported row,true,import\n"
    )

    result, status = import_time_entries_from_csv_text(
        csv_text,
        user_id=user.id,
        is_admin=False,
    )

    assert status == 200
    assert result["success"] is True
    assert result["created"] == 1
    assert result["failed"] == 0

    entries = TimeEntry.query.filter_by(user_id=user.id, project_id=project.id).all()
    assert any(e.notes == "Imported row" for e in entries)


@pytest.mark.unit
def test_import_row_missing_project(app, user, project):
    start = datetime.utcnow() - timedelta(hours=4)
    end = datetime.utcnow() - timedelta(hours=2)
    csv_text = CSV_HEADER + f"{start.isoformat()},{end.isoformat()},,,,\n"

    result, status = import_time_entries_from_csv_text(
        csv_text,
        user_id=user.id,
        is_admin=False,
    )

    assert status == 200
    assert result["created"] == 0
    assert result["failed"] == 1
    assert result["errors"][0]["error"] == "project_id is required"
