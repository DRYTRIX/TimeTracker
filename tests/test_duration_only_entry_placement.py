"""Hours logged without a start time are placed after the day's last entry.

Dashboard Log Time ended entries at 12:00 and manual entry ended them "now", ignoring the chosen date, so a
second entry on the same day failed with "overlaps". Now the entry goes after that day's last entry, from 09:00,
and on a day too long for that, into the latest earlier free gap (for example before 09:00).
"""

from datetime import date, datetime, timedelta

import pytest

from app import db
from app.models import TimeEntry
from app.services.time_tracking_service import TimeTrackingService

pytestmark = [pytest.mark.integration]

DAY = date(2026, 11, 16)


def _entry(user, project, start, hours):
    e = TimeEntry(
        user_id=user.id,
        project_id=project.id,
        start_time=start,
        end_time=start + timedelta(hours=hours),
        source="manual",
        billable=True,
    )
    db.session.add(e)
    db.session.commit()
    return e


def _day_entries(user, day):
    start = datetime.combine(day, datetime.min.time())
    return (
        TimeEntry.query.filter(
            TimeEntry.user_id == user.id,
            TimeEntry.start_time >= start,
            TimeEntry.start_time < start + timedelta(days=1),
        )
        .order_by(TimeEntry.start_time)
        .all()
    )


# --- placement ---------------------------------------------------------------------------------------


def test_empty_day_starts_at_nine(app, user):
    res = TimeTrackingService().place_duration_entry(user.id, DAY, 2 * 3600)
    assert res["success"]
    assert res["start_time"] == datetime(2026, 11, 16, 9, 0)
    assert res["end_time"] == datetime(2026, 11, 16, 11, 0)


def test_goes_after_last_entry_of_the_day(app, user, project):
    _entry(user, project, datetime(2026, 11, 16, 9, 0), 2)
    _entry(user, project, datetime(2026, 11, 16, 13, 0), 1)
    res = TimeTrackingService().place_duration_entry(user.id, DAY, 3600)
    assert res["start_time"] == datetime(2026, 11, 16, 14, 0)


def test_fills_the_day_up_to_midnight(app, user, project):
    _entry(user, project, datetime(2026, 11, 16, 9, 0), 12)  # until 21:00
    res = TimeTrackingService().place_duration_entry(user.id, DAY, 3 * 3600)
    assert res["success"]
    assert res["start_time"] == datetime(2026, 11, 16, 21, 0)
    assert res["end_time"] == datetime(2026, 11, 17, 0, 0)


def test_long_release_day_uses_the_morning(app, user, project):
    _entry(user, project, datetime(2026, 11, 16, 9, 0), 14)  # until 23:00
    res = TimeTrackingService().place_duration_entry(user.id, DAY, 2 * 3600)
    assert res["success"]
    assert res["start_time"] == datetime(2026, 11, 16, 7, 0)
    assert res["end_time"] == datetime(2026, 11, 16, 9, 0)


def test_takes_a_gap_between_entries(app, user, project):
    _entry(user, project, datetime(2026, 11, 16, 0, 0), 12)  # 00:00-12:00
    _entry(user, project, datetime(2026, 11, 16, 14, 0), 9)  # 14:00-23:00
    res = TimeTrackingService().place_duration_entry(user.id, DAY, 2 * 3600)
    assert (res["start_time"], res["end_time"]) == (datetime(2026, 11, 16, 12, 0), datetime(2026, 11, 16, 14, 0))


def test_full_day_reports_no_room(app, user, project):
    _entry(user, project, datetime(2026, 11, 16, 1, 0), 22)  # 01:00-23:00, two free hours left in pieces
    res = TimeTrackingService().place_duration_entry(user.id, DAY, 3 * 3600)
    assert not res["success"]
    assert res["error"] == "no_room_in_day"


def test_rejects_bad_duration(app, user):
    svc = TimeTrackingService()
    assert not svc.place_duration_entry(user.id, DAY, 0)["success"]
    assert not svc.place_duration_entry(user.id, DAY, "abc")["success"]


# --- the paths that log hours without a start time ---------------------------------------------------


def test_dashboard_log_time_twice_same_day(app, authenticated_client, user, project):
    for hours in (2, 1):
        resp = authenticated_client.post(
            "/api/entries",
            json={"project_id": project.id, "date": DAY.isoformat(), "duration_seconds": hours * 3600},
        )
        assert resp.status_code == 201, resp.get_json()
    entries = _day_entries(user, DAY)
    assert [(e.start_time.hour, e.end_time.hour) for e in entries] == [(9, 11), (11, 12)]


def test_api_entries_still_takes_start_and_end(app, authenticated_client, user, project):
    resp = authenticated_client.post(
        "/api/entries",
        json={"project_id": project.id, "start_time": "2026-11-16T15:00:00", "end_time": "2026-11-16T16:00:00"},
    )
    assert resp.status_code == 201, resp.get_json()


def test_api_entries_needs_times_or_date_and_duration(app, authenticated_client, project):
    resp = authenticated_client.post("/api/entries", json={"project_id": project.id, "date": DAY.isoformat()})
    assert resp.status_code == 400


def test_dashboard_log_time_sends_date_and_duration(app, authenticated_client):
    html = authenticated_client.get("/dashboard").get_data(as_text=True)
    assert "T12:00:00" not in html
    assert "duration_seconds: durationSec" in html


def test_manual_entry_hours_only_uses_the_chosen_date(app, authenticated_client, user, project):
    for worked in ("02:00", "01:30"):
        resp = authenticated_client.post(
            "/timer/manual",
            data={
                "project_id": project.id,
                "start_date": DAY.isoformat(),
                "worked_time": worked,
                "worked_time_mode": "explicit",
                "billable": "on",
            },
            follow_redirects=False,
        )
        assert resp.status_code in (200, 302)
    entries = _day_entries(user, DAY)
    assert len(entries) == 2
    assert entries[0].start_time == datetime(2026, 11, 16, 9, 0)
    assert entries[1].start_time == entries[0].end_time
