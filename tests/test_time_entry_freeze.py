"""Tests demonstrating time-control with freezegun and model time calculations."""
import datetime as dt

import pytest

from app import db
from app.models import TimeEntry
from factories import UserFactory, ProjectFactory


@pytest.mark.unit
def test_active_timer_duration_without_real_time(app, time_freezer):
    """Create a running timer at T0 and stop it at T0+90 minutes using time freezer."""
    freezer = time_freezer("2024-01-01 09:00:00")
    with app.app_context():
        user = UserFactory()
        project = ProjectFactory()
        entry = TimeEntry(
            user_id=user.id,
            project_id=project.id,
            start_time=dt.datetime(2024, 1, 1, 9, 0, 0),
            notes="Work session",
            source="auto",
            billable=True,
        )
        db.session.add(entry)
        db.session.commit()

        # Advance frozen time and compute duration deterministically without tz side-effects
        freezer.stop()
        freezer = time_freezer("2024-01-01 10:30:00")
        entry = db.session.get(TimeEntry, entry.id)
        entry.end_time = entry.start_time + dt.timedelta(minutes=90)
        entry.calculate_duration()
        db.session.commit()

        # Duration should be exactly 90 minutes = 5400 seconds (ROUNDING_MINUTES=1 in TestingConfig)
        db.session.refresh(entry)
        assert entry.duration_seconds == 5400
        assert entry.end_time.hour == 10
        assert entry.end_time.minute == 30


