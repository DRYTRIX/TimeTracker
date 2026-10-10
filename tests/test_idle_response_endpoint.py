"""Tests for POST /api/v1/timer/idle-response (Issue #722).

The single idempotent endpoint every client answers the "Still working?"
prompt through: the first device wins via the idle_notified_at check token,
stale answers are reported as already_resolved, and stop/trim credit time
the same way the server sweep does.
"""

from datetime import timedelta

from app import db
from app.models.time_entry import TimeEntry, local_now


def _make_notified_timer(user, project):
    """Open timer past the idle window with a pending idle check."""
    now = local_now()
    timer = TimeEntry(
        user_id=user.id,
        project_id=project.id,
        start_time=now - timedelta(hours=3),
        source="auto",
        billable=True,
    )
    timer.last_heartbeat_at = now - timedelta(hours=2)
    timer.idle_notified_at = now - timedelta(minutes=2)
    db.session.add(timer)
    db.session.commit()
    db.session.refresh(timer)
    return timer


def _token_of(timer):
    return timer.idle_notified_at.isoformat()


def test_yes_resets_the_idle_window(client_with_token, user, project):
    timer = _make_notified_timer(user, project)

    response = client_with_token.post(
        "/api/v1/timer/idle-response",
        json={"answer": "yes", "notified_at": _token_of(timer)},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["ok"] is True
    assert data["already_resolved"] is False
    assert data["stopped"] is False

    db.session.refresh(timer)
    assert timer.end_time is None
    # record_heartbeat clears the pending check and refreshes activity
    assert timer.idle_notified_at is None
    assert timer.idle_flagged_at is None


def test_stop_stops_at_now(client_with_token, user, project):
    timer = _make_notified_timer(user, project)

    response = client_with_token.post(
        "/api/v1/timer/idle-response",
        json={"answer": "stop", "notified_at": _token_of(timer)},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["stopped"] is True

    db.session.refresh(timer)
    assert timer.end_time is not None
    # Explicit "stop" records everything up to now (user confirmed it is done)
    assert timer.end_time >= local_now() - timedelta(seconds=5)


def test_trim_credits_last_activity_plus_idle_window(client_with_token, user, project):
    timer = _make_notified_timer(user, project)

    response = client_with_token.post(
        "/api/v1/timer/idle-response",
        json={"answer": "trim", "notified_at": _token_of(timer)},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["stopped"] is True

    db.session.refresh(timer)
    expected = timer.last_heartbeat_at + timedelta(minutes=30)
    assert timer.end_time is not None
    assert abs((timer.end_time - expected).total_seconds()) < 2


def test_stale_token_reports_already_resolved(client_with_token, user, project):
    timer = _make_notified_timer(user, project)

    response = client_with_token.post(
        "/api/v1/timer/idle-response",
        json={"answer": "stop", "notified_at": "2000-01-01T00:00:00"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["already_resolved"] is True

    db.session.refresh(timer)
    # The timer keeps running — the stale answer must not act
    assert timer.end_time is None
    assert timer.idle_notified_at is not None


def test_second_device_answer_is_already_resolved(client_with_token, user, project):
    timer = _make_notified_timer(user, project)
    token = _token_of(timer)

    first = client_with_token.post(
        "/api/v1/timer/idle-response",
        json={"answer": "yes", "notified_at": token},
    )
    assert first.status_code == 200
    assert first.get_json()["already_resolved"] is False

    # Another device answers the same check afterwards
    second = client_with_token.post(
        "/api/v1/timer/idle-response",
        json={"answer": "stop", "notified_at": token},
    )
    assert second.status_code == 200
    assert second.get_json()["already_resolved"] is True

    db.session.refresh(timer)
    # The "yes" won: the timer is still running
    assert timer.end_time is None


def test_answer_without_active_timer_rejected(client_with_token):
    response = client_with_token.post(
        "/api/v1/timer/idle-response",
        json={"answer": "yes"},
    )
    assert response.status_code == 400
    assert response.get_json()["error_code"] == "no_active_timer"


def test_invalid_answer_rejected(client_with_token, user, project):
    _make_notified_timer(user, project)
    response = client_with_token.post(
        "/api/v1/timer/idle-response",
        json={"answer": "maybe"},
    )
    assert response.status_code == 400
