"""
Service for daily/weekly working time limit detection and violations.
"""

from datetime import date, datetime
from typing import Any, Dict, Optional, Tuple

from app import db
from app.models import Settings, User, WorkingTimeViolation
from app.models.time_entry import local_now
from app.services.workday_session_service import WorkdaySessionService
from app.utils.db import safe_commit
from app.utils.overtime import get_week_start_for_date


class WorkingTimeLimitService:
    """Detect limit exceedances and manage violation records."""

    def __init__(self):
        self.workday_service = WorkdaySessionService()

    def get_limits_for_user(self, user: User) -> Tuple[float, float, bool]:
        """Return (daily_limit, weekly_limit, limits_enabled)."""
        settings = Settings.get_settings()
        enabled = bool(getattr(settings, "hour_limits_enabled", True))
        daily = user.daily_hour_limit_override
        weekly = user.weekly_hour_limit_override
        if daily is None:
            daily = float(getattr(settings, "daily_hour_limit", 10.0) or 10.0)
        if weekly is None:
            weekly = float(getattr(settings, "weekly_hour_limit", 48.0) or 48.0)
        return float(daily), float(weekly), enabled

    def get_worked_hours_for_day(self, user_id: int, day: date) -> float:
        """Hours worked on the workday axis; fallback to time entries if no sessions."""
        hours = self.workday_service.get_total_hours(user_id, day, day)
        if hours > 0:
            return hours
        start_dt = datetime.combine(day, datetime.min.time())
        end_dt = datetime.combine(day, datetime.max.time())
        from app.repositories import TimeEntryRepository

        seconds = TimeEntryRepository().get_total_duration(user_id=user_id, start_date=start_dt, end_date=end_dt)
        return round(seconds / 3600, 2)

    def get_worked_hours_for_week(self, user: User, week_start: date, week_end: date) -> float:
        hours = self.workday_service.get_total_hours(user.id, week_start, week_end)
        if hours > 0:
            return hours
        start_dt = datetime.combine(week_start, datetime.min.time())
        end_dt = datetime.combine(week_end, datetime.max.time())
        from app.repositories import TimeEntryRepository

        seconds = TimeEntryRepository().get_total_duration(user_id=user.id, start_date=start_dt, end_date=end_dt)
        return round(seconds / 3600, 2)

    def get_or_create_violation(
        self,
        user: User,
        period_type: str,
        period_start: date,
        period_end: date,
        limit_hours: float,
        actual_hours: float,
    ) -> WorkingTimeViolation:
        existing = WorkingTimeViolation.query.filter_by(
            user_id=user.id,
            period_type=period_type,
            period_start=period_start,
        ).first()
        if existing:
            existing.actual_hours = actual_hours
            existing.hours_over = round(max(0, actual_hours - limit_hours), 2)
            existing.limit_hours = limit_hours
            return existing

        violation = WorkingTimeViolation(
            user_id=user.id,
            period_type=period_type,
            period_start=period_start,
            period_end=period_end,
            limit_hours=limit_hours,
            actual_hours=actual_hours,
            hours_over=round(max(0, actual_hours - limit_hours), 2),
            status=WorkingTimeViolation.STATUS_PENDING,
        )
        db.session.add(violation)
        return violation

    def check_user_limits(self, user: User) -> list:
        """Check daily and weekly limits; create/update violations. Returns new violations needing email."""
        daily_limit, weekly_limit, enabled = self.get_limits_for_user(user)
        if not enabled:
            return []

        settings = Settings.get_settings()
        if not getattr(settings, "hour_limit_email_enabled", True):
            pass  # still create violations; email sent only when enabled below

        today = local_now().date()
        week_start = get_week_start_for_date(today, user)
        week_end = today
        new_for_email = []

        day_hours = self.get_worked_hours_for_day(user.id, today)
        if day_hours > daily_limit:
            v = self.get_or_create_violation(
                user, WorkingTimeViolation.PERIOD_DAILY, today, today, daily_limit, day_hours
            )
            if v.notified_at is None:
                new_for_email.append(v)

        week_hours = self.get_worked_hours_for_week(user, week_start, week_end)
        if week_hours > weekly_limit:
            v = self.get_or_create_violation(
                user, WorkingTimeViolation.PERIOD_WEEKLY, week_start, week_end, weekly_limit, week_hours
            )
            if v.notified_at is None:
                new_for_email.append(v)

        safe_commit("check_user_limits", {"user_id": user.id})
        return new_for_email

    def submit_justification(self, violation_id: int, user_id: int, justification: str) -> Dict[str, Any]:
        violation = WorkingTimeViolation.query.filter_by(id=violation_id, user_id=user_id).first()
        if not violation:
            return {"success": False, "message": "Violation not found", "error": "not_found"}
        if not justification or not justification.strip():
            return {"success": False, "message": "Justification is required", "error": "validation"}

        violation.justification = justification.strip()
        violation.justification_submitted_at = local_now()
        violation.status = WorkingTimeViolation.STATUS_SUBMITTED

        if not safe_commit("submit_justification", {"violation_id": violation_id}):
            return {"success": False, "message": "Database error", "error": "database_error"}

        return {"success": True, "message": "Justification submitted", "violation": violation}

    def acknowledge_violation(self, violation_id: int, admin_user_id: int) -> Dict[str, Any]:
        violation = WorkingTimeViolation.query.get(violation_id)
        if not violation:
            return {"success": False, "message": "Violation not found", "error": "not_found"}

        violation.status = WorkingTimeViolation.STATUS_ACKNOWLEDGED
        violation.acknowledged_by_user_id = admin_user_id
        violation.acknowledged_at = local_now()

        if not safe_commit("acknowledge_violation", {"violation_id": violation_id}):
            return {"success": False, "message": "Database error", "error": "database_error"}

        return {"success": True, "message": "Acknowledged", "violation": violation}

    def get_pending_violations_for_user(self, user_id: int):
        return (
            WorkingTimeViolation.query.filter(
                WorkingTimeViolation.user_id == user_id,
                WorkingTimeViolation.status.in_(
                    [WorkingTimeViolation.STATUS_PENDING, WorkingTimeViolation.STATUS_SUBMITTED]
                ),
            )
            .order_by(WorkingTimeViolation.created_at.desc())
            .all()
        )

    def get_violations_needing_justification(self, user_id: int):
        return (
            WorkingTimeViolation.query.filter(
                WorkingTimeViolation.user_id == user_id,
                WorkingTimeViolation.status == WorkingTimeViolation.STATUS_PENDING,
            )
            .order_by(WorkingTimeViolation.created_at.desc())
            .all()
        )
