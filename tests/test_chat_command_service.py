"""Shared chat command service tests (mocked TimeTrackingService)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.chat_command_service import handle_timer_command


def test_help_text():
    user = SimpleNamespace(id=1)
    result = handle_timer_command(user, "")
    assert "start" in result["text"].lower()
    assert "stop" in result["text"].lower()


def test_start_success():
    user = SimpleNamespace(id=7)
    project = SimpleNamespace(id=3, name="Alpha")
    with patch("app.models.Project") as Project:
        Project.query.get.return_value = None
        Project.query.filter.return_value.first.return_value = project
        with patch("app.services.time_tracking_service.TimeTrackingService") as TTS:
            TTS.return_value.start_timer.return_value = {"success": True}
            result = handle_timer_command(user, "start Alpha")
    assert "Timer started" in result["text"]
    assert "Alpha" in result["text"]


def test_start_missing_project_arg():
    user = SimpleNamespace(id=1)
    result = handle_timer_command(user, "start")
    assert "Usage" in result["text"]


def test_stop_success():
    user = SimpleNamespace(id=2)
    entry = SimpleNamespace(duration_formatted="1h 2m")
    with patch("app.services.time_tracking_service.TimeTrackingService") as TTS:
        TTS.return_value.stop_timer.return_value = {"success": True, "entry": entry}
        result = handle_timer_command(user, "stop")
    assert "Timer stopped" in result["text"]


def test_status_no_timer():
    user = SimpleNamespace(id=1, active_timer=None)
    result = handle_timer_command(user, "status")
    assert "No active timer" in result["text"]


def test_today_summary():
    user = SimpleNamespace(id=1)
    with patch(
        "app.services.notification_service.get_today_summary_for_user",
        return_value={"hours": 3.5, "projects": 2},
    ):
        result = handle_timer_command(user, "today")
    assert "3.5h" in result["text"]
    assert "2" in result["text"]
