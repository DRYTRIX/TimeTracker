"""Timesheet: one person's day and week of entries, day totals, and the rules for hours typed in.

Entries are counted on the day they start, like the dashboard and reports. A running timer counts up to
now. Writes go through TimeTrackingService only, so locked periods, required fields and rounding work
exactly as elsewhere in the app.
"""

import re
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import joinedload

from app.models import TimeEntry
from app.models.time_entry import local_now
from app.utils.overwork_notes import level_for

MAX_SECONDS = 24 * 3600

_HM = re.compile(r"^(\d{1,2}):([0-5]\d)$")
_DECIMAL = re.compile(r"^(\d{1,2}(?:[.,]\d+)?)\s*h?$")
_MINUTES = re.compile(r"^(\d{1,4})\s*m$")
_HOURS_MINUTES = re.compile(r"^(\d{1,2})\s*h\s*(\d{1,2})\s*m?$")


def parse_hours(raw) -> Optional[int]:
    """Seconds from what people type: "1:30", "1.5", "1,5", "90m", "2h", "1h 30m". None if empty or wrong.

    Zero and anything longer than a day are wrong too.
    """
    text = str(raw or "").strip().lower()
    if not text:
        return None
    seconds = None
    if m := _HM.match(text):
        seconds = int(m.group(1)) * 3600 + int(m.group(2)) * 60
    elif m := _HOURS_MINUTES.match(text):
        seconds = int(m.group(1)) * 3600 + int(m.group(2)) * 60
    elif m := _MINUTES.match(text):
        seconds = int(m.group(1)) * 60
    elif m := _DECIMAL.match(text):
        seconds = int(round(float(m.group(1).replace(",", ".")) * 3600))
    if not seconds or seconds <= 0 or seconds > MAX_SECONDS:
        return None
    return seconds


def fmt_hm(seconds) -> str:
    """1:05 style, the way Harvest shows hours."""
    minutes = int(round((seconds or 0) / 60))
    return f"{minutes // 60}:{minutes % 60:02d}"


def week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def entry_seconds(entry: TimeEntry) -> int:
    if entry.end_time is None:
        return int(entry.current_duration_seconds or 0)
    return int(entry.duration_seconds or 0)


@dataclass
class DayTab:
    day: date
    seconds: int = 0

    @property
    def total(self) -> str:
        return fmt_hm(self.seconds)


@dataclass
class DayView:
    day: date
    today: date
    tabs: List[DayTab]
    entries: List[TimeEntry]
    seconds_by_entry: Dict[int, int] = field(default_factory=dict)
    running: Optional[TimeEntry] = None
    overwork_level: Optional[str] = None

    @property
    def day_seconds(self) -> int:
        return sum(self.seconds_by_entry.get(e.id, 0) for e in self.entries)

    @property
    def week_seconds(self) -> int:
        return sum(t.seconds for t in self.tabs)

    @property
    def is_today(self) -> bool:
        return self.day == self.today

    @property
    def is_future(self) -> bool:
        return self.day > self.today


def build_day(user, day: date) -> DayView:
    """The week around ``day`` for ``user``: tab totals, the day's entries in order, and the running timer."""
    monday = week_start(day)
    start = datetime.combine(monday, time(0, 0))
    entries = (
        TimeEntry.query.options(
            joinedload(TimeEntry.project),
            joinedload(TimeEntry.client),
            joinedload(TimeEntry.task),
        )
        .filter(
            TimeEntry.user_id == user.id,
            TimeEntry.start_time >= start,
            TimeEntry.start_time < start + timedelta(days=7),
        )
        .order_by(TimeEntry.start_time, TimeEntry.id)
        .all()
    )
    tabs = [DayTab(monday + timedelta(days=i)) for i in range(7)]
    seconds_by_entry = {}
    day_entries = []
    running = None
    for e in entries:
        secs = entry_seconds(e)
        seconds_by_entry[e.id] = secs
        tabs[(e.start_time.date() - monday).days].seconds += secs
        if e.start_time.date() == day:
            day_entries.append(e)
        if e.end_time is None:
            running = e
    view = DayView(
        day=day,
        today=local_now().date(),
        tabs=tabs,
        entries=day_entries,
        seconds_by_entry=seconds_by_entry,
        running=running,
    )
    view.overwork_level = level_for(view.day_seconds / 3600, getattr(user, "standard_hours_per_day", None))
    return view


def clashes(user_id: int, start: datetime, end: datetime, exclude_entry_id: Optional[int] = None) -> bool:
    """True if [start, end) overlaps another entry of the user (a running timer counts up to now)."""
    query = TimeEntry.query.filter(TimeEntry.user_id == user_id, TimeEntry.start_time < end)
    if exclude_entry_id is not None:
        query = query.filter(TimeEntry.id != exclude_entry_id)
    now = local_now()
    for e in query.all():
        e_end = e.end_time if e.end_time is not None else max(now, e.start_time)
        if e_end > start:
            return True
    return False


# --- Week grid --------------------------------------------------------------------------------------


@dataclass
class WeekRow:
    """One "project / task" pair of the week. ``cells`` holds the entries of each day, Monday first."""

    project: Optional[object]
    task: Optional[object]
    client: Optional[object] = None
    cells: List[List[TimeEntry]] = field(default_factory=lambda: [[] for _ in range(7)])

    @property
    def key(self) -> str:
        if self.project is None:
            return f"client-{self.client.id if self.client else 0}"
        return f"{self.project.id}:{self.task.id if self.task else 0}"

    @property
    def editable(self) -> bool:
        """Rows without a project (client-only entries) are shown but not edited here."""
        return self.project is not None

    @property
    def has_running(self) -> bool:
        return any(e.end_time is None for day in self.cells for e in day)

    @property
    def entry_count(self) -> int:
        return sum(len(day) for day in self.cells)


@dataclass
class WeekView:
    monday: date
    today: date
    days: List[date]
    rows: List[WeekRow]
    seconds_by_entry: Dict[int, int]
    running: Optional[TimeEntry] = None

    def cell_seconds(self, row: WeekRow, i: int) -> int:
        return sum(self.seconds_by_entry.get(e.id, 0) for e in row.cells[i])

    def row_seconds(self, row: WeekRow) -> int:
        return sum(self.cell_seconds(row, i) for i in range(7))

    def day_seconds(self, i: int) -> int:
        return sum(self.cell_seconds(row, i) for row in self.rows)

    @property
    def week_seconds(self) -> int:
        return sum(self.day_seconds(i) for i in range(7))


def build_week(user, day: date) -> WeekView:
    """The week of ``day`` as a grid: one row per project and task, entries counted on the day they start."""
    monday = week_start(day)
    start = datetime.combine(monday, time(0, 0))
    entries = (
        TimeEntry.query.options(
            joinedload(TimeEntry.project),
            joinedload(TimeEntry.client),
            joinedload(TimeEntry.task),
        )
        .filter(
            TimeEntry.user_id == user.id,
            TimeEntry.start_time >= start,
            TimeEntry.start_time < start + timedelta(days=7),
        )
        .order_by(TimeEntry.start_time, TimeEntry.id)
        .all()
    )
    rows: Dict[tuple, WeekRow] = {}
    seconds_by_entry = {}
    running = None
    for e in entries:
        key = (e.project_id or 0, e.task_id or 0, 0 if e.project_id else (e.client_id or 0))
        row = rows.get(key)
        if row is None:
            row = rows[key] = WeekRow(project=e.project, task=e.task, client=None if e.project else e.client)
        row.cells[(e.start_time.date() - monday).days].append(e)
        seconds_by_entry[e.id] = entry_seconds(e)
        if e.end_time is None:
            running = e

    def sort_key(row: WeekRow):
        project = (row.project.name if row.project else (row.client.name if row.client else "")) or ""
        return (project.lower(), ((row.task.name if row.task else "") or "").lower())

    return WeekView(
        monday=monday,
        today=local_now().date(),
        days=[monday + timedelta(days=i) for i in range(7)],
        rows=sorted(rows.values(), key=sort_key),
        seconds_by_entry=seconds_by_entry,
        running=running,
    )


def week_row_entries(user_id: int, monday: date, project_id: int, task_id: Optional[int]) -> List[TimeEntry]:
    """Entries of one "project / task" row in the week starting ``monday``."""
    start = datetime.combine(monday, time(0, 0))
    query = TimeEntry.query.filter(
        TimeEntry.user_id == user_id,
        TimeEntry.project_id == project_id,
        TimeEntry.start_time >= start,
        TimeEntry.start_time < start + timedelta(days=7),
    )
    query = query.filter(TimeEntry.task_id.is_(None) if not task_id else TimeEntry.task_id == task_id)
    return query.all()
