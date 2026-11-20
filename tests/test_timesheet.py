"""Timesheet: a day view and a week grid of one's own time entries (Time > Timesheet).

The day: week tabs, Track time (hours on a day, or a timer today), Start and Stop on a row, Edit and
Delete. The week: one row per project and task, saved cell by cell. Only the person's own entries.
Writes go through TimeTrackingService.
"""

from datetime import date, datetime, timedelta

import pytest

from app import db
from app.models import Task, TimeEntry
from app.models.time_entry import local_now
from app.services.timesheet_service import build_day, fmt_hm, parse_hours

pytestmark = [pytest.mark.integration]

DAY = date(2026, 11, 16)  # a Monday


def _entry(user, project, start, hours, notes=None, task=None):
    e = TimeEntry(
        user_id=user.id,
        project_id=project.id,
        task_id=task.id if task else None,
        start_time=start,
        end_time=start + timedelta(hours=hours),
        notes=notes,
        source="manual",
        billable=True,
    )
    e.calculate_duration()
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


# --- Hours as people type them ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, seconds",
    [
        ("1:30", 5400),
        ("1.5", 5400),
        ("1,5", 5400),
        ("90m", 5400),
        ("2h", 7200),
        ("1h 30m", 5400),
        ("1h30", 5400),
        ("0:45", 2700),
        (" 8 ", 8 * 3600),
    ],
)
def test_parse_hours(raw, seconds):
    assert parse_hours(raw) == seconds


@pytest.mark.parametrize("raw", ["", None, "0", "0:00", "abc", "25", "1:75", "-1"])
def test_parse_hours_rejects(raw):
    assert parse_hours(raw) is None


def test_fmt_hm():
    assert fmt_hm(0) == "0:00"
    assert fmt_hm(5400) == "1:30"
    assert fmt_hm(65) == "0:01"


# --- The day and its week --------------------------------------------------------------------------


def test_build_day_counts_tabs_and_lists_the_day(app, user, project):
    _entry(user, project, datetime(2026, 11, 16, 9, 0), 2, notes="Созвон")
    _entry(user, project, datetime(2026, 11, 16, 11, 0), 1)
    _entry(user, project, datetime(2026, 11, 18, 9, 0), 3)
    _entry(user, project, datetime(2026, 11, 9, 9, 0), 5)  # last week, not counted
    view = build_day(user, DAY)
    assert [t.total for t in view.tabs] == ["3:00", "0:00", "3:00", "0:00", "0:00", "0:00", "0:00"]
    assert fmt_hm(view.week_seconds) == "6:00"
    assert [e.notes for e in view.entries] == ["Созвон", None]
    assert view.overwork_level is None


def test_build_day_flags_a_long_day(app, user, project):
    _entry(user, project, datetime(2026, 11, 16, 8, 0), 13)
    assert build_day(user, DAY).overwork_level == "long_day"


def test_page_shows_notes_and_week(app, authenticated_client, user, project):
    _entry(user, project, datetime(2026, 11, 16, 9, 0), 2, notes="Валюта в форме счёта")
    html = authenticated_client.get("/timesheet?date=2026-11-16").get_data(as_text=True)
    assert "Валюта в форме счёта" in html
    assert "Week total" in html
    assert "2:00" in html


def test_page_shows_only_own_entries(app, authenticated_client, user, admin_user, project):
    _entry(admin_user, project, datetime(2026, 11, 16, 9, 0), 2, notes="чужая запись")
    html = authenticated_client.get("/timesheet?date=2026-11-16").get_data(as_text=True)
    assert "чужая запись" not in html


def test_sidebar_track_opens_the_timesheet(app, authenticated_client):
    import re

    html = authenticated_client.get("/timesheet").get_data(as_text=True)
    track = re.search(r'<a [^>]*href="([^"]*)"[^>]*>\s*<i class="fas fa-play w-4', html)
    assert track and track.group(1) == "/timesheet"


# --- Track time ------------------------------------------------------------------------------------


def test_hours_on_a_past_day_go_after_the_last_entry(app, authenticated_client, user, project):
    _entry(user, project, datetime(2026, 11, 16, 9, 0), 2)
    resp = authenticated_client.post(
        "/timesheet/api/entries",
        json={"project_id": project.id, "date": "2026-11-16", "hours": "1:30", "notes": "задним числом"},
    )
    assert resp.status_code == 201, resp.get_json()
    entries = _day_entries(user, DAY)
    assert [(e.start_time.hour, e.start_time.minute) for e in entries] == [(9, 0), (11, 0)]
    assert entries[1].duration_seconds == 5400
    assert entries[1].notes == "задним числом"


def test_two_entries_on_the_same_past_day_do_not_clash(app, authenticated_client, user, project):
    for _ in range(2):
        resp = authenticated_client.post(
            "/timesheet/api/entries", json={"project_id": project.id, "date": "2026-11-16", "hours": "2"}
        )
        assert resp.status_code == 201, resp.get_json()
    assert len(_day_entries(user, DAY)) == 2


def test_task_must_belong_to_the_project(app, authenticated_client, user, project, task):
    from app.models import Project

    other = Project(name="Other project", client_id=project.client_id)
    db.session.add(other)
    db.session.commit()
    stray = Task(name="Elsewhere", project_id=other.id, created_by=user.id)
    db.session.add(stray)
    db.session.commit()
    resp = authenticated_client.post(
        "/timesheet/api/entries",
        json={"project_id": project.id, "task_id": stray.id, "date": "2026-11-16", "hours": "1"},
    )
    assert resp.status_code == 400
    resp = authenticated_client.post(
        "/timesheet/api/entries",
        json={"project_id": project.id, "task_id": task.id, "date": "2026-11-16", "hours": "1"},
    )
    assert resp.status_code == 201
    assert _day_entries(user, DAY)[0].task_id == task.id


def test_wrong_hours_are_refused(app, authenticated_client, project):
    resp = authenticated_client.post(
        "/timesheet/api/entries", json={"project_id": project.id, "date": "2026-11-16", "hours": "lots"}
    )
    assert resp.status_code == 400
    assert "1:30" in resp.get_json()["error"]


def test_no_hours_starts_a_timer_today_only(app, authenticated_client, user, project):
    resp = authenticated_client.post("/timesheet/api/entries", json={"project_id": project.id, "date": "2026-11-16"})
    assert resp.status_code == 400
    today = local_now().date().isoformat()
    resp = authenticated_client.post("/timesheet/api/entries", json={"project_id": project.id, "date": today})
    assert resp.status_code == 201, resp.get_json()
    assert TimeEntry.query.filter_by(user_id=user.id, end_time=None).count() == 1


def test_overwork_note_comes_back(app, authenticated_client, user, project):
    _entry(user, project, datetime(2026, 11, 16, 9, 0), 8)
    resp = authenticated_client.post(
        "/timesheet/api/entries", json={"project_id": project.id, "date": "2026-11-16", "hours": "1"}
    )
    assert resp.status_code == 201
    assert resp.get_json()["notice"]["level"] == "overtime"


# --- Edit, delete, Start and Stop ------------------------------------------------------------------


def test_edit_notes_and_hours_in_place(app, authenticated_client, user, project):
    e = _entry(user, project, datetime(2026, 11, 16, 9, 0), 1)
    resp = authenticated_client.patch(f"/timesheet/api/entries/{e.id}", json={"hours": "2:15", "notes": "правка"})
    assert resp.status_code == 200, resp.get_json()
    db.session.refresh(e)
    assert e.start_time == datetime(2026, 11, 16, 9, 0)
    assert e.duration_seconds == 2 * 3600 + 15 * 60
    assert e.notes == "правка"


def test_longer_entry_moves_instead_of_clashing(app, authenticated_client, user, project):
    first = _entry(user, project, datetime(2026, 11, 16, 9, 0), 2)
    _entry(user, project, datetime(2026, 11, 16, 11, 0), 2)
    resp = authenticated_client.patch(f"/timesheet/api/entries/{first.id}", json={"hours": "3"})
    assert resp.status_code == 200, resp.get_json()
    db.session.refresh(first)
    assert first.duration_seconds == 3 * 3600
    assert first.start_time == datetime(2026, 11, 16, 13, 0)  # after the other one


def test_cannot_touch_someone_elses_entry(app, authenticated_client, admin_user, project):
    e = _entry(admin_user, project, datetime(2026, 11, 16, 9, 0), 1)
    assert authenticated_client.patch(f"/timesheet/api/entries/{e.id}", json={"notes": "x"}).status_code == 404
    assert authenticated_client.delete(f"/timesheet/api/entries/{e.id}").status_code == 404
    assert authenticated_client.post(f"/timesheet/api/entries/{e.id}/start").status_code == 404


def test_delete(app, authenticated_client, user, project):
    e = _entry(user, project, datetime(2026, 11, 16, 9, 0), 1)
    assert authenticated_client.delete(f"/timesheet/api/entries/{e.id}").status_code == 200
    assert _day_entries(user, DAY) == []


def test_start_on_a_row_stops_the_running_timer_and_copies_the_row(app, authenticated_client, user, project, task):
    row = _entry(user, project, datetime(2026, 11, 16, 9, 0), 1, notes="та же задача", task=task)
    resp = authenticated_client.post(f"/timesheet/api/entries/{row.id}/start")
    assert resp.status_code == 201, resp.get_json()
    first_timer = TimeEntry.query.filter_by(user_id=user.id, end_time=None).one()
    assert (first_timer.task_id, first_timer.notes) == (task.id, "та же задача")

    resp = authenticated_client.post(f"/timesheet/api/entries/{row.id}/start")
    assert resp.status_code == 201
    assert TimeEntry.query.filter_by(user_id=user.id, end_time=None).count() == 1
    db.session.refresh(first_timer)
    assert first_timer.end_time is not None

    assert authenticated_client.post("/timesheet/api/stop").status_code == 200
    assert TimeEntry.query.filter_by(user_id=user.id, end_time=None).count() == 0


def test_tasks_of_a_project(app, authenticated_client, project, task):
    data = authenticated_client.get(f"/timesheet/api/projects/{project.id}/tasks").get_json()
    assert [t["name"] for t in data["tasks"]] == [task.name]


# --- Module switch ---------------------------------------------------------------------------------


def test_module_off_hides_the_timesheet_and_track_goes_to_the_dashboard(app, authenticated_client):
    import re

    from app.models import Settings

    settings = Settings.get_settings()
    settings.disabled_module_ids = ["timesheet"]
    db.session.commit()
    assert authenticated_client.get("/timesheet").status_code in (302, 403, 404)
    html = authenticated_client.get("/dashboard").get_data(as_text=True)
    assert 'href="/timesheet"' not in html
    track = re.search(r'<a [^>]*href="([^"]*)"[^>]*>\s*<i class="fas fa-play w-4', html)
    assert track and track.group(1) == "/dashboard"


# --- Week grid -------------------------------------------------------------------------------------


def test_build_week_rows_and_cells(app, user, project, task):
    from app.services.timesheet_service import build_week

    _entry(user, project, datetime(2026, 11, 16, 9, 0), 2, task=task)
    _entry(user, project, datetime(2026, 11, 20, 9, 0), 2, task=task)
    _entry(user, project, datetime(2026, 11, 20, 11, 0), 1, task=task)
    _entry(user, project, datetime(2026, 11, 18, 9, 0), 3)  # same project, no task: a row of its own
    view = build_week(user, date(2026, 11, 19))
    assert view.monday == DAY
    assert len(view.rows) == 2
    with_task = next(r for r in view.rows if r.task)
    assert [len(c) for c in with_task.cells] == [1, 0, 0, 0, 2, 0, 0]
    assert fmt_hm(view.row_seconds(with_task)) == "5:00"
    assert fmt_hm(view.week_seconds) == "8:00"


def test_week_page_has_the_rows(app, authenticated_client, user, project):
    _entry(user, project, datetime(2026, 11, 17, 9, 0), 2, notes="вторник")
    html = authenticated_client.get("/timesheet/week?date=2026-11-17").get_data(as_text=True)
    import json

    assert json.dumps("вторник")[1:-1] in html  # in the grid's data, as JSON
    assert '"required": false' in html


def test_week_page_tells_the_grid_when_a_description_is_required(app, authenticated_client):
    from app.models import Settings

    settings = Settings.get_settings()
    settings.time_entry_require_description = True
    settings.time_entry_description_min_length = 20
    db.session.commit()
    html = authenticated_client.get("/timesheet/week").get_data(as_text=True)
    assert '"required": true' in html
    assert '"min_length": 20' in html


def test_required_description_is_enforced_by_the_server(app, authenticated_client, user, project):
    from app.models import Settings

    settings = Settings.get_settings()
    settings.time_entry_require_description = True
    settings.time_entry_description_min_length = 20
    db.session.commit()
    short = authenticated_client.post(
        "/timesheet/api/entries",
        json={"project_id": project.id, "date": "2026-11-16", "hours": "1", "notes": "коротко"},
    )
    assert short.status_code == 400
    ok = authenticated_client.post(
        "/timesheet/api/entries",
        json={"project_id": project.id, "date": "2026-11-16", "hours": "1", "notes": "Разбор прогона eval по стране"},
    )
    assert ok.status_code == 201


def test_save_returns_the_hours_as_stored(app, authenticated_client, project):
    resp = authenticated_client.post(
        "/timesheet/api/entries", json={"project_id": project.id, "date": "2026-11-16", "hours": "1:30", "flash": False}
    )
    entry = resp.get_json()["entry"]
    assert entry["hours"] == "1:30"
    assert entry["date"] == "2026-11-16"


def test_grid_saves_do_not_leave_flash_messages(app, authenticated_client, user, project):
    _entry(user, project, datetime(2026, 11, 16, 9, 0), 8)
    resp = authenticated_client.post(
        "/timesheet/api/entries", json={"project_id": project.id, "date": "2026-11-16", "hours": "1", "flash": False}
    )
    assert resp.get_json()["notice"]["level"] == "overtime"
    with authenticated_client.session_transaction() as sess:
        assert not sess.get("_flashes")


def test_delete_returns_what_undo_needs(app, authenticated_client, user, project):
    e = _entry(user, project, datetime(2026, 11, 16, 9, 0), 1, notes="вернуть")
    deleted = authenticated_client.delete(f"/timesheet/api/entries/{e.id}").get_json()["deleted"]
    assert (deleted["date"], deleted["hours"], deleted["notes"]) == ("2026-11-16", "1:00", "вернуть")
    again = authenticated_client.post("/timesheet/api/entries", json={**deleted, "flash": False})
    assert again.status_code == 201


def test_running_timer_cannot_be_deleted_here(app, authenticated_client, user, project):
    today = local_now().date().isoformat()
    timer_id = authenticated_client.post(
        "/timesheet/api/entries", json={"project_id": project.id, "date": today}
    ).get_json()["entry_id"]
    assert authenticated_client.delete(f"/timesheet/api/entries/{timer_id}").status_code == 400


def test_remove_row_deletes_the_week_of_that_pair(app, authenticated_client, user, project, task):
    _entry(user, project, datetime(2026, 11, 16, 9, 0), 1, task=task)
    _entry(user, project, datetime(2026, 11, 18, 9, 0), 1, task=task)
    _entry(user, project, datetime(2026, 11, 18, 10, 0), 1)  # no task: another row, stays
    _entry(user, project, datetime(2026, 11, 23, 9, 0), 1, task=task)  # next week, stays
    resp = authenticated_client.post(
        "/timesheet/api/week/remove-row", json={"date": "2026-11-19", "project_id": project.id, "task_id": task.id}
    )
    assert resp.get_json()["deleted"] == 2
    left = TimeEntry.query.filter_by(user_id=user.id).order_by(TimeEntry.start_time).all()
    assert [(e.start_time.day, e.task_id) for e in left] == [(18, None), (23, task.id)]


def test_remove_row_refuses_while_its_timer_runs(app, authenticated_client, user, project):
    today = local_now().date().isoformat()
    authenticated_client.post("/timesheet/api/entries", json={"project_id": project.id, "date": today})
    resp = authenticated_client.post(
        "/timesheet/api/week/remove-row", json={"date": today, "project_id": project.id, "task_id": 0}
    )
    assert resp.status_code == 400
    assert TimeEntry.query.filter_by(user_id=user.id, end_time=None).count() == 1


def test_day_and_week_link_to_each_other(app, authenticated_client):
    day = authenticated_client.get("/timesheet?date=2026-11-18").get_data(as_text=True)
    assert "/timesheet/week?date=2026-11-18" in day
    week = authenticated_client.get("/timesheet/week?date=2026-11-18").get_data(as_text=True)
    assert "/timesheet?date=" in week


def test_day_and_week_offer_new_task(app, authenticated_client):
    for url in ("/timesheet", "/timesheet/week"):
        html = authenticated_client.get(url).get_data(as_text=True)
        assert "data-ts-new-task" in html
        assert 'id="createTaskInlineModal"' in html
