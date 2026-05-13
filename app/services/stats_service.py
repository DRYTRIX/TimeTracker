"""Aggregated productivity stats for the Value Dashboard (cached, SQL-efficient)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import Integer, and_, case, func
from sqlalchemy.orm import aliased

from app import db
from app.config import Config
from app.models import Client, Project, TimeEntry
from app.models.time_entry import local_now
from app.utils.cache_redis import cache_key, get_cache, set_cache
from app.utils.overtime import get_week_start_for_date

_CACHE_PREFIX = "value_dashboard"
_CACHE_TTL_SEC = 600

# SQLite strftime('%%w') and PostgreSQL EXTRACT(dow): 0=Sunday .. 6=Saturday
_DOW_ENGLISH = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")


class StatsService:
    """Read-only aggregates over time entries for dashboard insights."""

    @classmethod
    def get_value_dashboard(cls, user) -> Dict[str, Any]:
        """Return value-dashboard payload for the given user (session user). Cached 10 min when Redis is up."""
        uid = int(getattr(user, "id", 0) or 0)
        key = cache_key(_CACHE_PREFIX, uid)
        cached = get_cache(key, default=None)
        if cached is not None:
            return cached

        payload = cls._compute_value_dashboard(user)
        set_cache(key, payload, ttl=_CACHE_TTL_SEC)
        return payload

    @classmethod
    def _compute_value_dashboard(cls, user) -> Dict[str, Any]:
        from app.models.settings import Settings

        user_id = int(user.id)
        now = local_now()
        today: date = now.date()
        week_start = get_week_start_for_date(today, user)
        month_start = today.replace(day=1)
        day_after_today = today + timedelta(days=1)
        range_start_date = today - timedelta(days=6)

        end_exclusive = datetime.combine(day_after_today, time.min)
        week_start_dt = datetime.combine(week_start, time.min)
        month_start_dt = datetime.combine(month_start, time.min)
        range_start_dt = datetime.combine(range_start_date, time.min)

        base_filter = and_(TimeEntry.user_id == user_id, TimeEntry.end_time.isnot(None))

        week_cond = and_(TimeEntry.start_time >= week_start_dt, TimeEntry.start_time < end_exclusive)
        month_cond = and_(TimeEntry.start_time >= month_start_dt, TimeEntry.start_time < end_exclusive)

        main_row = (
            db.session.query(
                func.coalesce(func.sum(TimeEntry.duration_seconds), 0).label("total_sec"),
                func.count(TimeEntry.id).label("entry_count"),
                func.count(func.distinct(func.date(TimeEntry.start_time))).label("active_days"),
                func.coalesce(
                    func.sum(case((week_cond, TimeEntry.duration_seconds), else_=0)),
                    0,
                ).label("week_sec"),
                func.coalesce(
                    func.sum(case((month_cond, TimeEntry.duration_seconds), else_=0)),
                    0,
                ).label("month_sec"),
            )
            .filter(base_filter)
            .one()
        )

        total_sec = int(main_row.total_sec or 0)
        entries_count = int(main_row.entry_count or 0)
        active_days = int(main_row.active_days or 0)
        total_hours = round(total_sec / 3600.0, 2)
        this_week_hours = round(int(main_row.week_sec or 0) / 3600.0, 2)
        this_month_hours = round(int(main_row.month_sec or 0) / 3600.0, 2)
        avg_session_length = round(total_hours / entries_count, 2) if entries_count else 0.0

        most_productive_day = cls._most_productive_day_english(base_filter)
        last_7_days = cls._last_7_days_hours(base_filter, range_start_dt, end_exclusive, range_start_date, today)
        estimated_value_tracked = cls._estimated_value_tracked(base_filter)

        settings = Settings.get_settings()
        currency = (getattr(settings, "currency", None) or Config.CURRENCY or "EUR").strip()[:3] or "EUR"

        payload: Dict[str, Any] = {
            "total_hours": total_hours,
            "entries_count": entries_count,
            "active_days": active_days,
            "avg_session_length": avg_session_length,
            "most_productive_day": most_productive_day,
            "this_week_hours": this_week_hours,
            "this_month_hours": this_month_hours,
            "last_7_days": last_7_days,
            "estimated_value_tracked": (
                round(estimated_value_tracked, 2) if estimated_value_tracked and estimated_value_tracked > 0 else None
            ),
            "estimated_value_currency": currency,
        }
        return payload

    @classmethod
    def _dow_expression(cls):
        bind = db.session.get_bind()
        dialect = (bind.dialect.name if bind else "") or ""
        if dialect == "sqlite":
            return func.strftime("%w", TimeEntry.start_time)
        return func.cast(func.extract("dow", TimeEntry.start_time), Integer)

    @classmethod
    def _most_productive_day_english(cls, base_filter) -> Optional[str]:
        dow_col = cls._dow_expression().label("dow")
        rows = (
            db.session.query(dow_col, func.coalesce(func.sum(TimeEntry.duration_seconds), 0).label("sec"))
            .filter(base_filter)
            .group_by(dow_col)
            .all()
        )
        if not rows:
            return None
        best_dow: Optional[int] = None
        best_sec = -1
        for dow, sec in rows:
            s = int(sec or 0)
            if s > best_sec:
                best_sec = s
                try:
                    di = int(dow) if dow is not None else None
                except (TypeError, ValueError):
                    di = None
                best_dow = di
        if best_dow is None or best_sec <= 0:
            return None
        if 0 <= best_dow <= 6:
            return _DOW_ENGLISH[best_dow]
        return None

    @classmethod
    def _last_7_days_hours(
        cls,
        base_filter,
        range_start_dt: datetime,
        end_exclusive: datetime,
        range_start_date: date,
        today: date,
    ) -> List[Dict[str, Any]]:
        q = (
            db.session.query(
                func.date(TimeEntry.start_time).label("day"),
                func.coalesce(func.sum(TimeEntry.duration_seconds), 0).label("sec"),
            )
            .filter(
                base_filter,
                TimeEntry.start_time >= range_start_dt,
                TimeEntry.start_time < end_exclusive,
            )
            .group_by(func.date(TimeEntry.start_time))
        )
        by_day: Dict[date, float] = {}
        for row in q:
            d = row.day
            if d is None:
                continue
            if hasattr(d, "date") and callable(getattr(d, "date")) and not isinstance(d, date):
                try:
                    d = d.date()
                except Exception:
                    continue
            elif isinstance(d, str):
                try:
                    d = date.fromisoformat(d[:10])
                except ValueError:
                    continue
            by_day[d] = round(int(row.sec or 0) / 3600.0, 2)

        out: List[Dict[str, Any]] = []
        cur = range_start_date
        while cur <= today:
            out.append({"date": cur.isoformat(), "hours": by_day.get(cur, 0.0)})
            cur += timedelta(days=1)
        return out

    @classmethod
    def _estimated_value_tracked(cls, base_filter) -> float:
        """Sum (hours * effective rate) using project rate, else client defaults."""
        ClientDirect = aliased(Client)
        ClientProj = aliased(Client)
        hours = func.coalesce(TimeEntry.duration_seconds, 0) / 3600.0
        rate = func.coalesce(Project.hourly_rate, ClientDirect.default_hourly_rate, ClientProj.default_hourly_rate, 0)

        total = (
            db.session.query(func.coalesce(func.sum(hours * rate), 0))
            .select_from(TimeEntry)
            .outerjoin(Project, Project.id == TimeEntry.project_id)
            .outerjoin(ClientDirect, ClientDirect.id == TimeEntry.client_id)
            .outerjoin(ClientProj, ClientProj.id == Project.client_id)
            .filter(base_filter)
            .scalar()
        )

        return float(total or 0)


# Expose for tests (bypass cache)
def compute_value_dashboard_for_tests(user) -> Dict[str, Any]:
    return StatsService._compute_value_dashboard(user)
