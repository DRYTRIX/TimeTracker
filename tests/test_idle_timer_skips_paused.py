"""Regression tests for the server-side idle sweep and paused timers.

A paused timer is intentionally accumulating no time, so ``check_idle_timers``
must never idle-notify, flag, or auto-stop it. The idle query guards
``TimeEntry.paused_at`` to make that true.
"""

from datetime import timedelta

from app import db
from app.models.time_entry import TimeEntry, local_now
from app.utils.scheduled_tasks import check_idle_timers


def _make_stale_active_timer(user, project, *, paused):
    """An open timer whose last heartbeat is well past the idle window."""
    now = local_now()
    timer = TimeEntry(
        user_id=user.id,
        project_id=project.id,
        start_time=now - timedelta(hours=3),
        source="auto",
        billable=True,
    )
    # Two hours idle — comfortably beyond the 30-minute default window.
    timer.last_heartbeat_at = now - timedelta(hours=2)
    if paused:
        timer.paused_at = now - timedelta(minutes=90)
    db.session.add(timer)
    db.session.commit()
    db.session.refresh(timer)
    return timer


def test_idle_sweep_skips_paused_timer(app, user, project):
    paused = _make_stale_active_timer(user, project, paused=True)

    check_idle_timers()
    db.session.refresh(paused)

    # A paused timer must not be idle-notified, flagged, or stopped.
    assert paused.idle_notified_at is None
    assert paused.idle_flagged_at is None
    assert paused.end_time is None


def test_idle_sweep_still_notifies_running_timer(app, user, project):
    """Control: a genuinely idle, non-paused timer is still swept."""
    running = _make_stale_active_timer(user, project, paused=False)

    check_idle_timers()
    db.session.refresh(running)

    assert running.idle_notified_at is not None
