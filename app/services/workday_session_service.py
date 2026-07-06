"""
Service for workday clock-in/clock-out sessions.
Delegates to AttendanceComplianceService for unified compliance records.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from app import db
from app.models import WorkdaySession
from app.models.time_entry import local_now
from app.services.attendance_compliance_service import AttendanceComplianceService
from app.utils.db import safe_commit


class WorkdaySessionService:
    """Business logic for workday sessions (legacy API, compliance-backed)."""

    def __init__(self):
        self.compliance = AttendanceComplianceService()

    def get_active_session(self, user_id: int) -> Optional[WorkdaySession]:
        return WorkdaySession.get_active_for_user(user_id)

    def can_start_workday(self, user_id: int) -> tuple[bool, Optional[str]]:
        return self.compliance.can_start_work(user_id)

    def start_workday(
        self,
        user_id: int,
        notes: Optional[str] = None,
        source: str = "manual",
    ) -> Dict[str, Any]:
        result = self.compliance.clock_in(user_id, notes=notes, source=source)
        if not result.get("success"):
            return result

        period = result["period"]
        session = WorkdaySession(
            user_id=user_id,
            start_time=period.start_time,
            notes=notes,
            source=source,
        )
        db.session.add(session)
        db.session.flush()
        period.workday_session_id = session.id

        if not safe_commit("start_workday", {"user_id": user_id}):
            return {
                "success": False,
                "message": "Could not start workday due to a database error",
                "error": "database_error",
            }

        return {"success": True, "message": "Workday started", "session": session}

    def end_workday(self, user_id: int, notes: Optional[str] = None) -> Dict[str, Any]:
        session = self.get_active_session(user_id)
        if not session:
            return {"success": False, "message": "No active workday session", "error": "no_active_workday"}

        result = self.compliance.clock_out(user_id, notes=notes)
        if not result.get("success"):
            return result

        period = result["period"]
        session.end_time = period.end_time
        if notes:
            session.notes = (session.notes or "") + ("\n" if session.notes else "") + notes.strip()
        session.calculate_duration()

        if not safe_commit("end_workday", {"user_id": user_id, "session_id": session.id}):
            return {
                "success": False,
                "message": "Could not end workday due to a database error",
                "error": "database_error",
            }

        return {"success": True, "message": "Workday ended", "session": session}

    def get_session_for_day(self, user_id: int, day) -> list:
        start_dt = datetime.combine(day, datetime.min.time())
        end_dt = datetime.combine(day, datetime.max.time())
        return (
            WorkdaySession.query.filter(
                WorkdaySession.user_id == user_id,
                WorkdaySession.start_time >= start_dt,
                WorkdaySession.start_time <= end_dt,
            )
            .order_by(WorkdaySession.start_time.desc())
            .all()
        )

    def get_total_hours(self, user_id: int, start_date, end_date) -> float:
        hours = self.compliance.get_total_hours(user_id, start_date, end_date)
        if hours > 0:
            return hours
        return WorkdaySession.get_total_hours_for_period(user_id, start_date, end_date)

    def auto_close_stale_sessions(self, max_hours: int = 18) -> int:
        compliance_closed = self.compliance.auto_close_stale_sessions(max_hours=max_hours)
        cutoff = local_now() - timedelta(hours=max_hours)
        stale = WorkdaySession.query.filter(
            WorkdaySession.end_time.is_(None),
            WorkdaySession.start_time < cutoff,
        ).all()
        count = 0
        for session in stale:
            session.end_time = session.start_time + timedelta(hours=max_hours)
            session.auto_closed = True
            session.calculate_duration()
            self.compliance.mirror_workday_session(session)
            count += 1
        if count:
            safe_commit("auto_close_stale_workday_sessions", {"count": count})
        return max(count, compliance_closed)
