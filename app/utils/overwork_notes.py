"""A note for the person when a day's logged hours go past their daily norm or past 12 hours.

The entry is always saved; the note only tells the person who logged it. There are three texts per level,
shown in turn (the turn is kept in the session, so nothing is stored). Set OVERWORK_NOTES=false to turn
the notes off.
"""

from datetime import date, datetime, time, timedelta
from typing import Optional

from flask_babel import lazy_gettext as _l

STRONG_HOURS = 12.0

NOTES = {
    "overtime": (
        _l("Saved. That's %(hours)s %(day)s – more than a usual day. Overtime counts, so it's logged as is."),
        _l("Saved. %(hours)s %(day)s – a long one. Hope it was worth it, and that the next day is lighter."),
        _l("Saved. %(hours)s %(day)s. Overtime noted – go get some air."),
    ),
    "long_day": (
        _l(
            "Saved. %(hours)s %(day)s is a lot. Logging it is right, but this pace doesn't last – take a proper "
            "break, and if it keeps happening, tell your lead so the plan can change."
        ),
        _l(
            "Saved, but hey – %(hours)s in one day. Nothing should be on fire enough for this to be normal. "
            "Close the laptop, eat something, get some sleep. The work will still be here tomorrow."
        ),
        _l("%(hours)s %(day)s. Logged. Now please stop – the release will survive an evening without you."),
    ),
}


def day_hours(user_id: int, day: date) -> float:
    """Finished hours the user has on ``day`` (entries are counted on the day they start)."""
    from app import db
    from app.models import TimeEntry

    start = datetime.combine(day, time(0, 0))
    total = (
        db.session.query(db.func.sum(TimeEntry.duration_seconds))
        .filter(
            TimeEntry.user_id == user_id,
            TimeEntry.start_time >= start,
            TimeEntry.start_time < start + timedelta(days=1),
        )
        .scalar()
    )
    return (total or 0) / 3600


def _fmt_hours(hours: float) -> str:
    minutes = int(round(hours * 60))
    return f"{minutes // 60}h {minutes % 60:02d}m"


def _fmt_day(day: date, today: date) -> str:
    from flask_babel import gettext as _

    if day == today:
        return _("today")
    return _("on %(day)s", day=day.strftime("%a, %d %b").replace(" 0", " "))


def level_for(hours: float, norm: Optional[float]) -> Optional[str]:
    norm = float(norm or 8.0)
    if hours > STRONG_HOURS:
        return "long_day"
    if hours > norm:
        return "overtime"
    return None


def note_for_day(user, day: date) -> Optional[dict]:
    """The note to show after an entry was saved on ``day``, or None. Rotates the text in the session."""
    from flask import current_app

    from app.models.time_entry import local_now

    if not current_app.config.get("OVERWORK_NOTES", True):
        return None
    hours = day_hours(user.id, day)
    level = level_for(hours, getattr(user, "standard_hours_per_day", None))
    if not level:
        return None
    index = 0
    try:
        from flask import session

        key = f"overwork_note_{level}"
        index = int(session.get(key, 0)) % len(NOTES[level])
        session[key] = index + 1
    except Exception:
        pass
    text = str(NOTES[level][index]) % {"hours": _fmt_hours(hours), "day": _fmt_day(day, local_now().date())}
    return {"level": level, "hours": round(hours, 2), "text": text}
