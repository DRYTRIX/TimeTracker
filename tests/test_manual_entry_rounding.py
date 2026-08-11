"""Integration tests for per-user rounding on the manual entry form (#725)."""

import pytest

from app import db
from app.models import TimeEntry
from app.utils.time_rounding import apply_user_rounding

pytestmark = [pytest.mark.routes]


@pytest.mark.routes
def test_manual_entry_rounds_explicit_duration_once(authenticated_client, user, project, app):
    """Explicit worked_time override is rounded once using the user's preferences.

    Uses start/end spanning 2 hours but an explicit duration of 1:02 so that
    a start/end recalculation would produce a different value than the rounded
    override (3600s), catching double-apply or override-ignored bugs.
    """
    with app.app_context():
        # Mutate the identity-map instance so the next request's current_user
        # (same scoped session in tests) sees the new prefs after commit.
        user.time_rounding_enabled = True
        user.time_rounding_minutes = 15
        user.time_rounding_method = "nearest"
        db.session.commit()
        user_id = user.id
        raw_seconds = 62 * 60  # 1:02
        expected = apply_user_rounding(raw_seconds, user)  # nearest 15 → 3600
        assert expected == 3600

    response = authenticated_client.post(
        "/timer/manual",
        data={
            "project_id": project.id,
            "start_date": "2025-06-01",
            "start_time": "09:00",
            "end_date": "2025-06-01",
            "end_time": "11:00",  # 2h window — must not overwrite the override
            "worked_time": "1:02",
            "worked_time_mode": "explicit",
            "notes": "Rounded explicit duration",
            "billable": "on",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        entry = TimeEntry.query.filter_by(notes="Rounded explicit duration", user_id=user_id).first()
        assert entry is not None
        assert entry.duration_seconds == expected
        # Not the raw override, and not the 2-hour start/end span
        assert entry.duration_seconds != raw_seconds
        assert entry.duration_seconds != 2 * 3600
