"""A note when a day's hours go past the person's norm (default 8h) or past 12 hours.

The entry is always saved. Past the norm the note is gentle, past 12 hours it is a caring warning.
Three texts per level are shown in turn.
"""

from datetime import date, datetime, timedelta

import pytest

from app.utils.overwork_notes import NOTES, level_for

pytestmark = [pytest.mark.integration]

DAY = date(2026, 11, 16)


_cursor = {}


def _log(client, project, hours):
    """Log ``hours`` on DAY right after the previous test entry, with explicit times."""
    start = _cursor.get(id(client), datetime(2026, 11, 16, 0, 0))
    end = start + timedelta(seconds=int(hours * 3600))
    _cursor[id(client)] = end
    resp = client.post(
        "/api/entries",
        json={"project_id": project.id, "start_time": start.isoformat(), "end_time": end.isoformat()},
    )
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


def test_levels_follow_the_norm_and_twelve_hours():
    assert level_for(8.0, 8) is None
    assert level_for(8.5, 8) == "overtime"
    assert level_for(12.0, 8) == "overtime"
    assert level_for(12.5, 8) == "long_day"
    assert level_for(7.0, 6) == "overtime"  # part-time norm
    assert level_for(9.0, None) == "overtime"  # no norm set: 8h


def test_no_note_within_the_norm(app, authenticated_client, project):
    assert "notice" not in _log(authenticated_client, project, 5)


def test_overtime_note_past_the_norm(app, authenticated_client, project):
    _log(authenticated_client, project, 5)
    body = _log(authenticated_client, project, 4)
    assert body["notice"]["level"] == "overtime"
    assert "9h 00m" in body["notice"]["text"]
    assert "on Mon, 16 Nov" in body["notice"]["text"]


def test_long_day_note_past_twelve_hours(app, authenticated_client, project):
    _log(authenticated_client, project, 8)
    body = _log(authenticated_client, project, 5)
    assert body["notice"]["level"] == "long_day"
    assert "13h 00m" in body["notice"]["text"]


def test_texts_take_turns(app, authenticated_client, project):
    _log(authenticated_client, project, 8.5)
    texts = [_log(authenticated_client, project, 0.25)["notice"]["text"] for _ in range(4)]
    assert len(set(texts[:3])) == 3
    assert texts[3].split(".")[0] == texts[0].split(".")[0]  # back to the first wording
    assert len(NOTES["overtime"]) == 3 and len(NOTES["long_day"]) == 3


def test_notes_can_be_turned_off(app, authenticated_client, project):
    app.config["OVERWORK_NOTES"] = False
    try:
        _log(authenticated_client, project, 8)
        assert "notice" not in _log(authenticated_client, project, 5)
    finally:
        app.config["OVERWORK_NOTES"] = True


def test_manual_entry_flashes_the_note(app, authenticated_client, project):
    _log(authenticated_client, project, 8)  # 00:00-08:00
    resp = authenticated_client.post(
        "/timer/manual",
        data={
            "project_id": project.id,
            "start_date": DAY.isoformat(),
            "start_time": "08:00",
            "end_date": DAY.isoformat(),
            "end_time": "09:00",
            "billable": "on",
        },
        follow_redirects=True,
    )
    html = resp.get_data(as_text=True)
    assert "9h 00m" in html
