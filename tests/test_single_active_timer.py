"""Unit tests: can_start_timer always blocks a second active timer.

``Settings.single_active_timer`` is not consulted for enforcement (see
TimeTrackingService.can_start_timer and migration 010).
"""

from datetime import datetime

import pytest

from app import db
from app.models import Settings, TimeEntry
from app.services.time_tracking_service import TimeTrackingService

pytestmark = [pytest.mark.unit]


def test_can_start_timer_false_when_active_even_if_setting_off(app, user, project):
    with app.app_context():
        settings = Settings.get_settings()
        settings.single_active_timer = False
        db.session.commit()

        running = TimeEntry(
            user_id=user.id,
            project_id=project.id,
            start_time=datetime.utcnow(),
            end_time=None,
            source="manual",
            billable=True,
        )
        db.session.add(running)
        db.session.commit()

        ok, message = TimeTrackingService().can_start_timer(user.id)
        assert ok is False
        assert message is not None
        assert "active timer" in message.lower()


def test_can_start_timer_true_when_no_active(app, user, project):
    with app.app_context():
        settings = Settings.get_settings()
        settings.single_active_timer = False
        db.session.commit()

        ok, message = TimeTrackingService().can_start_timer(user.id)
        assert ok is True
        assert message is None
