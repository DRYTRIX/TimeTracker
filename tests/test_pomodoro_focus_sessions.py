"""Tests for PomodoroService and focus-session export wiring."""

from app.models.focus_session import FocusSession
from app.services.pomodoro_service import PomodoroService
from app.utils.data_export import _focus_session_to_dict


def test_pomodoro_start_cycle_interrupt_end(app, test_user):
    with app.app_context():
        svc = PomodoroService()
        started = svc.start_session(user_id=test_user.id, pomodoro_length=25)
        assert started["success"] is True
        session_id = started["session"]["id"]

        active = svc.get_active_session(test_user.id)
        assert active is not None
        assert active.id == session_id

        # Second start should fail while active
        again = svc.start_session(user_id=test_user.id)
        assert again["success"] is False

        cycle = svc.complete_cycle(session_id)
        assert cycle["success"] is True
        assert cycle["session"]["cycles_completed"] == 1

        interrupt = svc.log_interruption(session_id, reason="phone")
        assert interrupt["session"]["interruptions"] == 1

        ended = svc.end_session(session_id, notes="done")
        assert ended["success"] is True
        assert ended["session"]["ended_at"] is not None

        assert svc.get_active_session(test_user.id) is None
        stats = svc.get_session_stats(test_user.id, days=7)
        assert stats["total_sessions"] >= 1
        assert stats["total_cycles"] >= 1


def test_focus_session_export_dict_fields(app, test_user):
    with app.app_context():
        svc = PomodoroService()
        started = svc.start_session(user_id=test_user.id)
        fs_id = started["session"]["id"]
        svc.end_session(fs_id)
        fs = FocusSession.query.get(fs_id)
        data = _focus_session_to_dict(fs)
        assert "started_at" in data
        assert "ended_at" in data
        assert "start_time" not in data
        assert data["duration_minutes"] is not None
