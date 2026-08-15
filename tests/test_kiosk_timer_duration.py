"""Regression: kiosk stop must compute duration_seconds (not leave it NULL)."""

from datetime import timedelta

import pytest

from app import db
from app.models.time_entry import TimeEntry, local_now


@pytest.mark.integration
def test_kiosk_stop_timer_sets_duration_seconds(authenticated_client, active_timer, app, user):
    """Stopping via /api/kiosk/stop-timer must populate duration_seconds."""
    with app.app_context():
        timer = db.session.get(TimeEntry, active_timer.id)
        # Give the timer a measurable start so duration is clearly non-zero
        timer.start_time = local_now() - timedelta(minutes=12)
        db.session.commit()

        response = authenticated_client.post(
            "/api/kiosk/stop-timer",
            json={},
            headers={"Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest"},
        )
        assert response.status_code == 200, response.get_data(as_text=True)
        data = response.get_json()
        assert data.get("success") is True

        stopped = db.session.get(TimeEntry, active_timer.id)
        assert stopped.end_time is not None
        assert stopped.duration_seconds is not None
        assert stopped.duration_seconds > 0
