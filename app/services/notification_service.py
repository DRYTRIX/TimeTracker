"""Smart in-app notifications: eligibility, ranking, and dismissal-aware payloads."""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from flask import current_app
from sqlalchemy import func

from app import db
from app.models import TimeEntry, UserSmartNotificationDismissal
from app.utils.db import safe_commit

KIND_NO_TRACKING = "no_tracking_today"
KIND_LONG_TIMER = "timer_running_long"
KIND_DAILY_SUMMARY = "daily_summary"
KIND_BREAK_REMINDER = "break_reminder"
KIND_END_OF_DAY = "end_of_day_reminder"
KIND_MISSED_CLOCK_IN = "missed_clock_in"

_HHMM_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


def get_today_summary_for_user(user) -> Dict[str, Any]:
    """Hours and distinct project count for completed entries in the user's local today."""
    start_utc, end_utc, _local_date = user_local_today_bounds_utc(user)
    hours = _completed_hours_today(user.id, start_utc, end_utc)
    projects = completed_projects_today_count(user.id, start_utc, end_utc)
    return {"hours": round(hours, 2), "projects": projects}


def parse_hhmm(raw: Optional[str]) -> Optional[Tuple[int, int]]:
    if not raw or not isinstance(raw, str):
        return None
    s = raw.strip()
    m = _HHMM_RE.match(s)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def user_local_today_bounds_utc(user) -> Tuple[datetime, datetime, str]:
    """Return (start_utc, end_utc_exclusive, local_date_iso) for the user's current local calendar day."""
    from datetime import time as dt_time

    from app.utils.timezone import get_timezone_for_user, now_in_user_timezone

    user_now = now_in_user_timezone(user)
    user_tz = get_timezone_for_user(user)
    user_today: date = user_now.date()
    start_local = datetime.combine(user_today, dt_time.min).replace(tzinfo=user_tz)
    end_local = start_local + timedelta(days=1)
    start_utc = start_local.astimezone(timezone.utc)
    end_utc = end_local.astimezone(timezone.utc)
    local_date_iso = user_today.isoformat()
    return start_utc, end_utc, local_date_iso


def _entry_start_as_utc_aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _dismissed_kinds(user_id: int, local_date: str) -> Set[str]:
    rows = (
        UserSmartNotificationDismissal.query.filter_by(user_id=user_id, local_date=local_date)
        .with_entities(UserSmartNotificationDismissal.kind)
        .all()
    )
    return {r[0] for r in rows}


def _completed_hours_today(user_id: int, start_utc: datetime, end_utc: datetime) -> float:
    total_seconds = (
        db.session.query(func.coalesce(func.sum(TimeEntry.duration_seconds), 0))
        .filter(
            TimeEntry.user_id == user_id,
            TimeEntry.start_time >= start_utc,
            TimeEntry.start_time < end_utc,
            TimeEntry.end_time.isnot(None),
        )
        .scalar()
        or 0
    )
    return float(total_seconds) / 3600.0


def completed_projects_today_count(user_id: int, start_utc: datetime, end_utc: datetime) -> int:
    q = (
        db.session.query(func.count(func.distinct(TimeEntry.project_id)))
        .filter(
            TimeEntry.user_id == user_id,
            TimeEntry.start_time >= start_utc,
            TimeEntry.start_time < end_utc,
            TimeEntry.end_time.isnot(None),
            TimeEntry.project_id.isnot(None),
        )
        .scalar()
    )
    return int(q or 0)


def _completed_entry_count_today(user_id: int, start_utc: datetime, end_utc: datetime) -> int:
    return TimeEntry.query.filter(
        TimeEntry.user_id == user_id,
        TimeEntry.start_time >= start_utc,
        TimeEntry.start_time < end_utc,
        TimeEntry.end_time.isnot(None),
    ).count()


def _in_hour_slot(user_local_now: datetime, target_hour: int, slot_minutes: int) -> bool:
    """Match remind-to-log style: fire during `target_hour` when minute < slot_minutes (e.g. 16:00–16:29)."""
    return user_local_now.hour == target_hour and user_local_now.minute < slot_minutes


def _in_time_slot_after(user_local_now: datetime, target_h: int, target_m: int, slot_minutes: int) -> bool:
    """Fire once in the window [target_time, target_time + slot_minutes)."""
    target = user_local_now.replace(hour=target_h, minute=target_m, second=0, microsecond=0)
    slot_end = target + timedelta(minutes=slot_minutes)
    return target <= user_local_now < slot_end


def is_expected_work_day(user_id: int, work_date: date) -> bool:
    """Mon–Fri, excluding company holidays and approved time off."""
    if work_date.weekday() >= 5:
        return False
    from app.services.workforce_governance_service import WorkforceGovernanceService

    if WorkforceGovernanceService().is_holiday(work_date):
        return False
    from app.models.time_off import TimeOffRequest, TimeOffRequestStatus

    off = TimeOffRequest.query.filter(
        TimeOffRequest.user_id == user_id,
        TimeOffRequest.status == TimeOffRequestStatus.APPROVED,
        TimeOffRequest.start_date <= work_date,
        TimeOffRequest.end_date >= work_date,
    ).first()
    return off is None


def has_workday_started_today(user_id: int, work_date: date) -> bool:
    """True if the user has an active or completed work period for the given date."""
    from app.models.attendance_compliance import AttendanceWorkPeriod, DailyAttendanceRecord

    active = AttendanceWorkPeriod.query.filter_by(user_id=user_id, end_time=None).first()
    if active:
        return True
    day = DailyAttendanceRecord.query.filter_by(user_id=user_id, work_date=work_date).first()
    if not day:
        return False
    return AttendanceWorkPeriod.query.filter_by(attendance_day_id=day.id).count() > 0


def _bucket_marker_exists(user_id: int, kind: str, bucket_key: str) -> bool:
    """True if a UserSmartNotificationDismissal row already records this bucket (i.e. already fired)."""
    return (
        UserSmartNotificationDismissal.query.filter_by(user_id=user_id, kind=kind, local_date=bucket_key)
        .with_entities(UserSmartNotificationDismissal.id)
        .first()
        is not None
    )


def _record_bucket_marker(user_id: int, kind: str, bucket_key: str) -> bool:
    """Insert a marker row so this bucket only fires once. Returns True on success.

    Idempotent: if the row already exists (race), returns False so the caller does not
    emit a duplicate notification on this request.
    """
    try:
        db.session.add(
            UserSmartNotificationDismissal(
                user_id=user_id,
                local_date=bucket_key,
                kind=kind,
                dismissed_at=datetime.utcnow(),
            )
        )
        return bool(safe_commit())
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
        return False


class NotificationService:
    """Builds smart notification payloads for the authenticated user."""

    _PRIORITY = {
        KIND_LONG_TIMER: 0,
        KIND_MISSED_CLOCK_IN: 0,
        KIND_BREAK_REMINDER: 1,
        KIND_NO_TRACKING: 1,
        KIND_DAILY_SUMMARY: 2,
        KIND_END_OF_DAY: 3,
    }

    @classmethod
    def dismiss(cls, user, kind: str, local_date: str) -> bool:
        if kind not in (
            KIND_NO_TRACKING,
            KIND_LONG_TIMER,
            KIND_DAILY_SUMMARY,
            KIND_BREAK_REMINDER,
            KIND_END_OF_DAY,
            KIND_MISSED_CLOCK_IN,
        ):
            return False
        if not local_date or len(local_date) != 10:
            return False
        existing = UserSmartNotificationDismissal.query.filter_by(
            user_id=user.id, local_date=local_date, kind=kind
        ).first()
        if existing:
            return True
        db.session.add(
            UserSmartNotificationDismissal(
                user_id=user.id,
                local_date=local_date,
                kind=kind,
                dismissed_at=datetime.utcnow(),
            )
        )
        safe_commit()
        return True

    @classmethod
    def build_for_user(cls, user, now_utc: Optional[datetime] = None) -> Dict[str, Any]:
        from app.utils.timezone import now_in_user_timezone

        cfg = current_app.config
        max_per = int(cfg.get("SMART_NOTIFY_MAX_PER_DAY") or 2)
        slot_minutes = int(cfg.get("SMART_NOTIFY_SCHEDULER_SLOT_MINUTES") or 30)
        long_threshold_h = float(cfg.get("SMART_NOTIFY_LONG_TIMER_HOURS") or 4.0)

        default_nudge = (cfg.get("SMART_NOTIFY_NO_TRACKING_AFTER") or "16:00").strip()
        default_summary = (cfg.get("SMART_NOTIFY_SUMMARY_AT") or "18:00").strip()
        default_end_of_day = (cfg.get("SMART_NOTIFY_END_OF_DAY_AT") or "17:00").strip()
        default_missed_clock_in = (cfg.get("SMART_NOTIFY_MISSED_CLOCK_IN_AT") or "09:30").strip()

        meta_base = {
            "max_per_day": max_per,
            "scheduler_slot_minutes": slot_minutes,
            "long_timer_hours": long_threshold_h,
        }

        if not getattr(user, "is_active", True) or not getattr(user, "smart_notifications_enabled", False):
            start_utc, end_utc, local_date = user_local_today_bounds_utc(user)
            return {
                "notifications": [],
                "meta": {
                    **meta_base,
                    "local_date": local_date,
                    "enabled": False,
                    "no_tracking_after": (getattr(user, "smart_notify_no_tracking_after", None) or default_nudge),
                    "summary_at": (getattr(user, "smart_notify_summary_at", None) or default_summary),
                    "end_of_day_at": (getattr(user, "smart_notify_end_of_day_time", None) or default_end_of_day),
                    "missed_clock_in_at": (
                        getattr(user, "smart_notify_missed_clock_in_at", None) or default_missed_clock_in
                    ),
                    "browser_push": bool(getattr(user, "smart_notify_browser", False)),
                },
            }

        now_utc = now_utc or datetime.now(timezone.utc)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=timezone.utc)

        user_local_now = now_in_user_timezone(user)
        start_utc, end_utc, local_date = user_local_today_bounds_utc(user)

        nudge_t = parse_hhmm(getattr(user, "smart_notify_no_tracking_after", None)) or parse_hhmm(default_nudge)
        summary_t = parse_hhmm(getattr(user, "smart_notify_summary_at", None)) or parse_hhmm(default_summary)
        end_of_day_t = parse_hhmm(getattr(user, "smart_notify_end_of_day_time", None)) or parse_hhmm(default_end_of_day)
        missed_clock_in_t = parse_hhmm(getattr(user, "smart_notify_missed_clock_in_at", None)) or parse_hhmm(
            default_missed_clock_in
        )
        if not nudge_t:
            nudge_t = (16, 0)
        if not summary_t:
            summary_t = (18, 0)
        if not end_of_day_t:
            end_of_day_t = (17, 0)
        if not missed_clock_in_t:
            missed_clock_in_t = (9, 30)

        meta = {
            **meta_base,
            "local_date": local_date,
            "enabled": True,
            "no_tracking_after": f"{nudge_t[0]:02d}:{nudge_t[1]:02d}",
            "summary_at": f"{summary_t[0]:02d}:{summary_t[1]:02d}",
            "end_of_day_at": f"{end_of_day_t[0]:02d}:{end_of_day_t[1]:02d}",
            "missed_clock_in_at": f"{missed_clock_in_t[0]:02d}:{missed_clock_in_t[1]:02d}",
            "browser_push": bool(getattr(user, "smart_notify_browser", False)),
        }

        dismissed = _dismissed_kinds(user.id, local_date)
        candidates: List[Dict[str, Any]] = []

        # Long-running active timer
        if getattr(user, "smart_notify_long_timer", True) and KIND_LONG_TIMER not in dismissed:
            active = TimeEntry.get_user_active_timer(user.id)
            if active and active.start_time:
                start_u = _entry_start_as_utc_aware(active.start_time)
                if start_u:
                    elapsed_h = (now_utc - start_u).total_seconds() / 3600.0
                    if elapsed_h >= long_threshold_h:
                        h = int(elapsed_h)
                        m = int((elapsed_h - h) * 60)
                        candidates.append(
                            {
                                "kind": KIND_LONG_TIMER,
                                "title": "Timer still running",
                                "message": (
                                    f"Your timer has been running for about {h}h {m}m — still active?"
                                    if h or m
                                    else f"Your timer has been running for {long_threshold_h:g}h or more — still active?"
                                ),
                                "type": "warning",
                                "priority": "high",
                            }
                        )

        hours_today = _completed_hours_today(user.id, start_utc, end_utc)
        entry_count = _completed_entry_count_today(user.id, start_utc, end_utc)
        active_timer = TimeEntry.get_user_active_timer(user.id)

        # No tracking today (time slot, no completed entries, no active timer)
        if getattr(user, "smart_notify_no_tracking", True) and KIND_NO_TRACKING not in dismissed:
            if _in_hour_slot(user_local_now, nudge_t[0], slot_minutes):
                if entry_count == 0 and active_timer is None:
                    candidates.append(
                        {
                            "kind": KIND_NO_TRACKING,
                            "title": "No time logged yet",
                            "message": "You have not tracked anything today. Start a timer or add an entry.",
                            "type": "info",
                            "priority": "normal",
                        }
                    )

        # Daily summary (time slot)
        if getattr(user, "smart_notify_daily_summary", True) and KIND_DAILY_SUMMARY not in dismissed:
            if _in_hour_slot(user_local_now, summary_t[0], slot_minutes):
                candidates.append(
                    {
                        "kind": KIND_DAILY_SUMMARY,
                        "title": "Daily summary",
                        "message": f"Today you logged {hours_today:.1f}h in completed entries.",
                        "type": "success",
                        "priority": "normal",
                    }
                )

        # Break reminder: nudge once per interval bucket while a timer is running
        if (
            getattr(user, "smart_notify_break_reminder", False)
            and KIND_BREAK_REMINDER not in dismissed
            and active_timer is not None
            and active_timer.start_time is not None
        ):
            try:
                raw_interval = int(getattr(user, "smart_notify_break_interval_minutes", 60) or 60)
            except (TypeError, ValueError):
                raw_interval = 60
            interval_minutes = max(15, min(240, raw_interval))
            start_u = _entry_start_as_utc_aware(active_timer.start_time)
            if start_u:
                elapsed_minutes = (now_utc - start_u).total_seconds() / 60.0
                if elapsed_minutes >= interval_minutes:
                    bucket = int(elapsed_minutes // interval_minutes)
                    bucket_key = f"break_{active_timer.id}_{bucket}"
                    if not _bucket_marker_exists(user.id, KIND_BREAK_REMINDER, bucket_key):
                        if _record_bucket_marker(user.id, KIND_BREAK_REMINDER, bucket_key):
                            elapsed_h = int(elapsed_minutes // 60)
                            elapsed_m = int(elapsed_minutes - elapsed_h * 60)
                            candidates.append(
                                {
                                    "kind": KIND_BREAK_REMINDER,
                                    "title": "Time for a break",
                                    "message": (
                                        f"You've been tracking for {elapsed_h}h {elapsed_m}m. "
                                        f"Consider taking a short break."
                                    ),
                                    "type": "info",
                                    "priority": "normal",
                                    "action": {"label": "Pause timer", "url": "/timer/pause"},
                                }
                            )

        # Missed workday clock-in (morning reminder on expected work days)
        if getattr(user, "smart_notify_missed_clock_in", False) and KIND_MISSED_CLOCK_IN not in dismissed:
            user_today = user_local_now.date()
            if is_expected_work_day(user.id, user_today) and not has_workday_started_today(user.id, user_today):
                if _in_time_slot_after(user_local_now, missed_clock_in_t[0], missed_clock_in_t[1], slot_minutes):
                    candidates.append(
                        {
                            "kind": KIND_MISSED_CLOCK_IN,
                            "title": "Workday not started",
                            "message": (
                                "You have not started your workday yet. " "Press Start Workday when you begin working."
                            ),
                            "type": "warning",
                            "priority": "high",
                            "action": {"label": "Start workday", "url": "/"},
                        }
                    )

        # End-of-day reminder (time slot)
        if getattr(user, "smart_notify_end_of_day", False) and KIND_END_OF_DAY not in dismissed:
            if _in_hour_slot(user_local_now, end_of_day_t[0], slot_minutes):
                candidates.append(
                    {
                        "kind": KIND_END_OF_DAY,
                        "title": "End of day",
                        "message": (f"It's nearly end of day. You've logged {hours_today:.1f}h today."),
                        "type": "info",
                        "priority": "normal",
                        "action": {"label": "View today's entries", "url": "/time-entries"},
                    }
                )

        candidates.sort(key=lambda n: cls._PRIORITY.get(n["kind"], 99))
        notifications = candidates[:max_per]

        return {"notifications": notifications, "meta": meta}
