"""Personal productivity stats for the per-user productivity dashboard.

All methods are read-only, take ``user`` as the first argument, and never
raise — they return safe defaults on any error so the dashboard always
renders. Time bucketing is performed in the user's local timezone.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func

from app import db
from app.models import Project, TimeEntry
from app.utils.timezone import get_timezone_for_user, get_timezone_obj, now_in_user_timezone

logger = logging.getLogger(__name__)

# Deterministic palette indexed by project_id % 10 (matches template legend).
_PROJECT_PALETTE = [
    "#3b82f6",
    "#10b981",
    "#f59e0b",
    "#ef4444",
    "#8b5cf6",
    "#ec4899",
    "#14b8a6",
    "#f97316",
    "#6366f1",
    "#84cc16",
]

_DOW_NAMES = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)


def _safe_user_id(user) -> Optional[int]:
    try:
        uid = int(getattr(user, "id", 0) or 0)
        return uid if uid > 0 else None
    except (TypeError, ValueError):
        return None


def _user_today(user) -> date:
    try:
        return now_in_user_timezone(user).date()
    except Exception:
        return datetime.utcnow().date()


def _week_start_for(user, today: date) -> date:
    """Return the Monday on or before ``today`` (always Monday per spec)."""
    return today - timedelta(days=today.weekday())


def _user_day_bounds_app_naive(user, day: date):
    """Return (start_naive, end_naive_exclusive) in app TZ for the given user-local calendar day.

    TimeEntry.start_time is stored as naive datetime in the application timezone, so
    we project the user's local day boundaries into the app TZ (and strip tzinfo) to
    keep filters compatible with the rest of the codebase.
    """
    try:
        user_tz = get_timezone_for_user(user)
        app_tz = get_timezone_obj()
        start_local = datetime.combine(day, time.min).replace(tzinfo=user_tz)
        end_local = start_local + timedelta(days=1)
        start_app = start_local.astimezone(app_tz).replace(tzinfo=None)
        end_app = end_local.astimezone(app_tz).replace(tzinfo=None)
        return start_app, end_app
    except Exception:
        # Fallback: treat the user date as naive app-local
        start = datetime.combine(day, time.min)
        return start, start + timedelta(days=1)


def _user_period_bounds_app_naive(user, start_day: date, end_day_inclusive: date):
    """Return (start_naive, end_naive_exclusive) in app TZ for [start_day, end_day_inclusive]."""
    start_app, _ = _user_day_bounds_app_naive(user, start_day)
    _, end_app = _user_day_bounds_app_naive(user, end_day_inclusive)
    return start_app, end_app


def _to_user_local(dt, user_tz, app_tz):
    """Convert a (naive app-local) datetime into the user's local timezone."""
    if dt is None:
        return None
    try:
        if dt.tzinfo is None:
            aware = dt.replace(tzinfo=app_tz)
        else:
            aware = dt
        return aware.astimezone(user_tz)
    except Exception:
        return None


def _format_active_timer(timer) -> Optional[Dict[str, Any]]:
    if timer is None:
        return None
    try:
        return {
            "id": int(timer.id),
            "project_name": timer.project.name if getattr(timer, "project", None) else None,
            "task_name": timer.task.name if getattr(timer, "task", None) else None,
            "start_time": timer.start_time.isoformat() if timer.start_time else None,
            "duration_seconds": int(timer.current_duration_seconds or 0),
        }
    except Exception:
        return None


class ProductivityService:
    """Aggregate personal productivity stats for the authenticated user."""

    # --------------------------------------------------------------- summary

    @classmethod
    def get_summary(cls, user) -> Dict[str, Any]:
        """Stats for today and the current week."""
        empty: Dict[str, Any] = {
            "today_hours": 0.0,
            "week_hours": 0.0,
            "week_goal_hours": 40.0,
            "week_goal_percent": 0,
            "active_timer": None,
            "billable_percent_week": 0,
            "top_project_week": None,
        }

        uid = _safe_user_id(user)
        if uid is None:
            return empty

        try:
            today = _user_today(user)
            week_start = _week_start_for(user, today)

            today_start, today_end = _user_day_bounds_app_naive(user, today)
            week_start_dt, week_end_dt = _user_period_bounds_app_naive(user, week_start, today)

            today_seconds = (
                db.session.query(func.coalesce(func.sum(TimeEntry.duration_seconds), 0))
                .filter(
                    TimeEntry.user_id == uid,
                    TimeEntry.end_time.isnot(None),
                    TimeEntry.start_time >= today_start,
                    TimeEntry.start_time < today_end,
                )
                .scalar()
                or 0
            )

            week_rows = (
                db.session.query(
                    func.coalesce(func.sum(TimeEntry.duration_seconds), 0).label("total_sec"),
                    func.coalesce(
                        func.sum(
                            db.case(
                                (TimeEntry.billable == True, TimeEntry.duration_seconds),  # noqa: E712
                                else_=0,
                            )
                        ),
                        0,
                    ).label("billable_sec"),
                )
                .filter(
                    TimeEntry.user_id == uid,
                    TimeEntry.end_time.isnot(None),
                    TimeEntry.start_time >= week_start_dt,
                    TimeEntry.start_time < week_end_dt,
                )
                .one()
            )

            today_hours = round(int(today_seconds) / 3600.0, 2)
            week_total_sec = int(week_rows.total_sec or 0)
            week_billable_sec = int(week_rows.billable_sec or 0)
            week_hours = round(week_total_sec / 3600.0, 2)

            standard_hours = float(getattr(user, "standard_hours_per_day", 8.0) or 8.0)

            # Resolve weekly goal: prefer WeeklyTimeGoal for current week, else
            # fall back to standard_hours_per_day * 5, defaulting to 40.
            week_goal_hours = round(standard_hours * 5, 2) if standard_hours else 40.0
            try:
                from app.models import WeeklyTimeGoal

                wgoal = WeeklyTimeGoal.get_current_week_goal(uid)
                if wgoal and getattr(wgoal, "target_hours", None):
                    week_goal_hours = float(wgoal.target_hours)
            except Exception:
                # Table missing or any other issue — use fallback.
                pass

            if not week_goal_hours or week_goal_hours <= 0:
                week_goal_hours = 40.0

            week_goal_percent = int(min(100, max(0, round(week_hours / week_goal_hours * 100))))
            billable_percent_week = int(round(week_billable_sec / week_total_sec * 100)) if week_total_sec > 0 else 0

            top_project_week = cls._top_project_for_period(uid, week_start_dt, week_end_dt)

            try:
                active = TimeEntry.get_user_active_timer(uid)
            except Exception:
                active = None

            return {
                "today_hours": today_hours,
                "week_hours": week_hours,
                "week_goal_hours": round(week_goal_hours, 2),
                "week_goal_percent": week_goal_percent,
                "active_timer": _format_active_timer(active),
                "billable_percent_week": billable_percent_week,
                "top_project_week": top_project_week,
            }
        except Exception:
            logger.exception("ProductivityService.get_summary failed for user %s", uid)
            return empty

    @staticmethod
    def _top_project_for_period(user_id: int, start_dt, end_dt) -> Optional[Dict[str, Any]]:
        try:
            row = (
                db.session.query(
                    Project.id,
                    Project.name,
                    func.coalesce(func.sum(TimeEntry.duration_seconds), 0).label("sec"),
                )
                .join(Project, Project.id == TimeEntry.project_id)
                .filter(
                    TimeEntry.user_id == user_id,
                    TimeEntry.end_time.isnot(None),
                    TimeEntry.start_time >= start_dt,
                    TimeEntry.start_time < end_dt,
                )
                .group_by(Project.id, Project.name)
                .order_by(func.sum(TimeEntry.duration_seconds).desc())
                .first()
            )
            if not row or not row.sec:
                return None
            return {"name": row.name, "hours": round(int(row.sec) / 3600.0, 2)}
        except Exception:
            return None

    # --------------------------------------------------------- daily breakdown

    @classmethod
    def get_daily_breakdown(cls, user, days: int = 14) -> List[Dict[str, Any]]:
        """One dict per calendar day for the last N days (oldest first)."""
        try:
            days = max(1, min(int(days), 90))
        except (TypeError, ValueError):
            days = 14

        uid = _safe_user_id(user)
        if uid is None:
            return []

        try:
            today = _user_today(user)
            start_day = today - timedelta(days=days - 1)
            start_dt, end_dt = _user_period_bounds_app_naive(user, start_day, today)

            user_tz = get_timezone_for_user(user)
            app_tz = get_timezone_obj()

            rows = (
                db.session.query(
                    TimeEntry.start_time,
                    TimeEntry.duration_seconds,
                    TimeEntry.billable,
                )
                .filter(
                    TimeEntry.user_id == uid,
                    TimeEntry.end_time.isnot(None),
                    TimeEntry.start_time >= start_dt,
                    TimeEntry.start_time < end_dt,
                )
                .all()
            )

            by_day_seconds: Dict[date, int] = defaultdict(int)
            by_day_billable: Dict[date, int] = defaultdict(int)
            by_day_count: Dict[date, int] = defaultdict(int)

            for start_time, duration_seconds, billable in rows:
                local_dt = _to_user_local(start_time, user_tz, app_tz)
                if local_dt is None:
                    continue
                d = local_dt.date()
                sec = int(duration_seconds or 0)
                by_day_seconds[d] += sec
                if billable:
                    by_day_billable[d] += sec
                by_day_count[d] += 1

            standard_hours = float(getattr(user, "standard_hours_per_day", 8.0) or 8.0)

            out: List[Dict[str, Any]] = []
            cur = start_day
            while cur <= today:
                sec = by_day_seconds.get(cur, 0)
                bsec = by_day_billable.get(cur, 0)
                out.append(
                    {
                        "date": cur.isoformat(),
                        "hours": round(sec / 3600.0, 2),
                        "billable_hours": round(bsec / 3600.0, 2),
                        "entry_count": int(by_day_count.get(cur, 0)),
                        "goal_hours": round(standard_hours, 2),
                    }
                )
                cur += timedelta(days=1)
            return out
        except Exception:
            logger.exception("ProductivityService.get_daily_breakdown failed for user %s", uid)
            return []

    # ---------------------------------------------------------------- streak

    @classmethod
    def get_streak(cls, user) -> Dict[str, Any]:
        empty = {
            "current_streak": 0,
            "longest_streak": 0,
            "tracked_days_this_month": 0,
            "total_days_this_month": 1,
        }

        uid = _safe_user_id(user)
        if uid is None:
            return empty

        try:
            today = _user_today(user)
            user_tz = get_timezone_for_user(user)
            app_tz = get_timezone_obj()

            # Pull all completed entry start_times for the user. For most users
            # this is bounded; for very heavy users we cap to ~3 years to stay safe.
            cutoff_day = today - timedelta(days=365 * 3)
            cutoff_dt, _ = _user_day_bounds_app_naive(user, cutoff_day)

            rows = (
                db.session.query(TimeEntry.start_time)
                .filter(
                    TimeEntry.user_id == uid,
                    TimeEntry.end_time.isnot(None),
                    TimeEntry.start_time >= cutoff_dt,
                )
                .all()
            )

            tracked_days: set = set()
            for (start_time,) in rows:
                local_dt = _to_user_local(start_time, user_tz, app_tz)
                if local_dt is not None:
                    tracked_days.add(local_dt.date())

            # Current streak: consecutive days back from today; if today has 0 hours,
            # start checking from yesterday.
            current_streak = 0
            anchor = today if today in tracked_days else today - timedelta(days=1)
            cursor = anchor
            while cursor in tracked_days:
                current_streak += 1
                cursor -= timedelta(days=1)

            # Longest streak across all tracked days
            longest_streak = 0
            if tracked_days:
                ordered = sorted(tracked_days)
                run = 1
                longest_streak = 1
                for i in range(1, len(ordered)):
                    if (ordered[i] - ordered[i - 1]).days == 1:
                        run += 1
                        longest_streak = max(longest_streak, run)
                    else:
                        run = 1

            month_start = today.replace(day=1)
            tracked_this_month = sum(1 for d in tracked_days if month_start <= d <= today)
            total_days_this_month = (today - month_start).days + 1

            return {
                "current_streak": int(current_streak),
                "longest_streak": int(longest_streak),
                "tracked_days_this_month": int(tracked_this_month),
                "total_days_this_month": int(max(1, total_days_this_month)),
            }
        except Exception:
            logger.exception("ProductivityService.get_streak failed for user %s", uid)
            return empty

    # ---------------------------------------------------------------- focus

    @classmethod
    def get_focus_stats(cls, user, days: int = 30) -> Dict[str, Any]:
        empty = {
            "avg_session_length_minutes": 0.0,
            "longest_session_hours": 0.0,
            "entries_per_day": 0.0,
            "most_productive_hour": None,
            "most_productive_day": None,
        }

        try:
            days = max(1, min(int(days), 90))
        except (TypeError, ValueError):
            days = 30

        uid = _safe_user_id(user)
        if uid is None:
            return empty

        try:
            today = _user_today(user)
            start_day = today - timedelta(days=days - 1)
            start_dt, end_dt = _user_period_bounds_app_naive(user, start_day, today)

            user_tz = get_timezone_for_user(user)
            app_tz = get_timezone_obj()

            rows = (
                db.session.query(TimeEntry.start_time, TimeEntry.duration_seconds)
                .filter(
                    TimeEntry.user_id == uid,
                    TimeEntry.end_time.isnot(None),
                    TimeEntry.start_time >= start_dt,
                    TimeEntry.start_time < end_dt,
                )
                .all()
            )

            qualifying_durations: List[int] = []
            longest_seconds = 0
            tracked_days: set = set()
            hour_seconds: Dict[int, int] = defaultdict(int)
            dow_seconds: Dict[int, int] = defaultdict(int)

            for start_time, duration_seconds in rows:
                sec = int(duration_seconds or 0)
                local_dt = _to_user_local(start_time, user_tz, app_tz)
                if local_dt is None:
                    continue
                tracked_days.add(local_dt.date())
                hour_seconds[local_dt.hour] += sec
                # python weekday(): Monday=0..Sunday=6 — matches _DOW_NAMES order.
                dow_seconds[local_dt.weekday()] += sec
                if sec >= 300:  # exclude entries shorter than 5 minutes
                    qualifying_durations.append(sec)
                if sec > longest_seconds:
                    longest_seconds = sec

            if qualifying_durations:
                avg_minutes = sum(qualifying_durations) / len(qualifying_durations) / 60.0
            else:
                avg_minutes = 0.0

            entries_per_day = round(len(rows) / len(tracked_days), 2) if tracked_days else 0.0

            most_productive_hour: Optional[int] = None
            if hour_seconds:
                most_productive_hour = int(max(hour_seconds.items(), key=lambda kv: kv[1])[0])

            most_productive_day: Optional[str] = None
            if dow_seconds:
                best_dow = max(dow_seconds.items(), key=lambda kv: kv[1])[0]
                if 0 <= best_dow <= 6:
                    most_productive_day = _DOW_NAMES[best_dow]

            # Build a 24-bar sparkline of hours per hour of day for the period.
            hour_distribution = [round(hour_seconds.get(h, 0) / 3600.0, 2) for h in range(24)]

            return {
                "avg_session_length_minutes": round(avg_minutes, 1),
                "longest_session_hours": round(longest_seconds / 3600.0, 2),
                "entries_per_day": float(entries_per_day),
                "most_productive_hour": most_productive_hour,
                "most_productive_day": most_productive_day,
                "hour_distribution": hour_distribution,
            }
        except Exception:
            logger.exception("ProductivityService.get_focus_stats failed for user %s", uid)
            return empty

    # ----------------------------------------------------- project breakdown

    @classmethod
    def get_project_breakdown(cls, user, days: int = 30) -> List[Dict[str, Any]]:
        try:
            days = max(1, min(int(days), 90))
        except (TypeError, ValueError):
            days = 30

        uid = _safe_user_id(user)
        if uid is None:
            return []

        try:
            today = _user_today(user)
            start_day = today - timedelta(days=days - 1)
            start_dt, end_dt = _user_period_bounds_app_naive(user, start_day, today)

            rows = (
                db.session.query(
                    Project.id,
                    Project.name,
                    func.coalesce(func.sum(TimeEntry.duration_seconds), 0).label("total_sec"),
                    func.coalesce(
                        func.sum(
                            db.case(
                                (TimeEntry.billable == True, TimeEntry.duration_seconds),  # noqa: E712
                                else_=0,
                            )
                        ),
                        0,
                    ).label("billable_sec"),
                    func.count(TimeEntry.id).label("entry_count"),
                )
                .join(Project, Project.id == TimeEntry.project_id)
                .filter(
                    TimeEntry.user_id == uid,
                    TimeEntry.end_time.isnot(None),
                    TimeEntry.start_time >= start_dt,
                    TimeEntry.start_time < end_dt,
                )
                .group_by(Project.id, Project.name)
                .order_by(func.sum(TimeEntry.duration_seconds).desc())
                .limit(8)
                .all()
            )

            out: List[Dict[str, Any]] = []
            for row in rows:
                total_sec = int(row.total_sec or 0)
                if total_sec <= 0:
                    continue
                billable_sec = int(row.billable_sec or 0)
                pid = int(row.id)
                out.append(
                    {
                        "project_id": pid,
                        "name": row.name,
                        "hours": round(total_sec / 3600.0, 2),
                        "billable_hours": round(billable_sec / 3600.0, 2),
                        "entry_count": int(row.entry_count or 0),
                        "color": _PROJECT_PALETTE[pid % len(_PROJECT_PALETTE)],
                    }
                )
            return out
        except Exception:
            logger.exception("ProductivityService.get_project_breakdown failed for user %s", uid)
            return []

    # -------------------------------------------------------- weekly heatmap

    @classmethod
    def get_weekly_heatmap(cls, user, weeks: int = 12) -> List[Dict[str, Any]]:
        try:
            weeks = max(1, min(int(weeks), 26))
        except (TypeError, ValueError):
            weeks = 12

        uid = _safe_user_id(user)
        if uid is None:
            return []

        days = weeks * 7

        try:
            today = _user_today(user)
            start_day = today - timedelta(days=days - 1)
            start_dt, end_dt = _user_period_bounds_app_naive(user, start_day, today)

            user_tz = get_timezone_for_user(user)
            app_tz = get_timezone_obj()

            rows = (
                db.session.query(TimeEntry.start_time, TimeEntry.duration_seconds)
                .filter(
                    TimeEntry.user_id == uid,
                    TimeEntry.end_time.isnot(None),
                    TimeEntry.start_time >= start_dt,
                    TimeEntry.start_time < end_dt,
                )
                .all()
            )

            by_day: Dict[date, int] = defaultdict(int)
            for start_time, duration_seconds in rows:
                local_dt = _to_user_local(start_time, user_tz, app_tz)
                if local_dt is None:
                    continue
                by_day[local_dt.date()] += int(duration_seconds or 0)

            out: List[Dict[str, Any]] = []
            cur = start_day
            while cur <= today:
                hours = round(by_day.get(cur, 0) / 3600.0, 2)
                if hours <= 0:
                    level = 0
                elif hours < 2:
                    level = 1
                elif hours < 4:
                    level = 2
                elif hours < 6:
                    level = 3
                else:
                    level = 4
                out.append({"date": cur.isoformat(), "hours": hours, "level": level})
                cur += timedelta(days=1)
            return out
        except Exception:
            logger.exception("ProductivityService.get_weekly_heatmap failed for user %s", uid)
            return []

    # ---------------------------------------------------------------- insights

    @classmethod
    def get_insights(
        cls,
        user,
        summary: Dict[str, Any],
        daily_breakdown: List[Dict[str, Any]],
        streak: Dict[str, Any],
        focus: Dict[str, Any],
        projects: List[Dict[str, Any]],
    ) -> List[str]:
        """Build up to 4 plain-text insights from already-computed data."""
        insights: List[str] = []
        try:
            # 1. Week-over-week comparison.
            try:
                this_week_hours = float(summary.get("week_hours") or 0.0)
                # daily_breakdown is oldest first; last 7 entries are this week (Mon..today),
                # the 7 entries before that are "last week" for comparison.
                if len(daily_breakdown) >= 14:
                    last_week_hours = sum(float(d.get("hours") or 0) for d in daily_breakdown[-14:-7])
                else:
                    last_week_hours = 0.0
                if last_week_hours > 0 and this_week_hours != last_week_hours:
                    diff = this_week_hours - last_week_hours
                    pct = abs(int(round(diff / last_week_hours * 100)))
                    if pct >= 1:
                        direction = "more" if diff > 0 else "less"
                        insights.append(f"You logged {pct}% {direction} this week than last week")
            except Exception:
                pass

            # 2. Streak insight.
            try:
                cur_streak = int(streak.get("current_streak") or 0)
                if cur_streak >= 3:
                    insights.append(f"You've tracked time {cur_streak} days in a row — keep it up!")
            except Exception:
                pass

            # 3. Peak hour insight.
            try:
                hour = focus.get("most_productive_hour")
                if hour is not None and 0 <= int(hour) <= 23:
                    h = int(hour)
                    next_h = (h + 1) % 24
                    insights.append(f"Your most productive time is {h:02d}:00–{next_h:02d}:00")
            except Exception:
                pass

            # 4. Top project insight.
            try:
                if projects:
                    total = sum(float(p.get("hours") or 0) for p in projects)
                    top = projects[0]
                    if total > 0 and top.get("hours"):
                        pct = int(round(float(top["hours"]) / total * 100))
                        if pct > 0:
                            insights.append(
                                f"{top.get('name', 'Top project')} accounted for " f"{pct}% of your tracked time"
                            )
            except Exception:
                pass

            # 5. Billable rate.
            try:
                billable = int(summary.get("billable_percent_week") or 0)
                if billable > 0:
                    insights.append(f"Your billable rate this week is {billable}%")
            except Exception:
                pass
        except Exception:
            logger.exception("ProductivityService.get_insights failed")

        return insights[:4]
