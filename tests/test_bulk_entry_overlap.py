from datetime import datetime

import pytest

from app import db
from app.models import TimeEntry


@pytest.mark.routes
def test_bulk_entry_accepts_slot_that_starts_when_another_ends(app, authenticated_client, user, project):
    """An entry that only touches the new slot is not an overlap."""
    with app.app_context():
        db.session.add(
            TimeEntry(
                user_id=user.id,
                project_id=project.id,
                start_time=datetime(2025, 6, 3, 9, 0),
                end_time=datetime(2025, 6, 3, 12, 0),
                source="manual",
            )
        )
        db.session.commit()

    data = {
        "project_id": project.id,
        "start_date": "2025-06-03",
        "end_date": "2025-06-03",
        "start_time": "12:00",
        "end_time": "17:00",
        "notes": "Afternoon block",
    }
    authenticated_client.post("/timer/bulk", data=data, follow_redirects=True)

    with app.app_context():
        assert TimeEntry.query.filter_by(notes="Afternoon block").count() == 1

    data.update(start_time="11:00", notes="Overlapping block")
    authenticated_client.post("/timer/bulk", data=data, follow_redirects=True)

    with app.app_context():
        assert TimeEntry.query.filter_by(notes="Overlapping block").count() == 0
