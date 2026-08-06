"""
Service for workday clock-in/clock-out sessions.
Delegates to AttendanceComplianceService for unified compliance records.
"""

from datetime import datetime, time, timedelta
from typing import Any, Dict, Optional

from app import db
from app.models import WorkdaySession
from app.models.attendance_compliance import AttendanceCorrection, AttendanceCorrectionStatus, AttendanceWorkPeriod
from app.models.time_entry import local_now
from app.services.attendance_compliance_service import AttendanceComplianceService
from app.utils.db import safe_commit


def parse_workday_end_time(raw: Optional[str]) -> Optional[datetime]:
    """Parse an optional leave time from form/JSON (ISO or datetime-local)."""
    if not raw or not isinstance(raw, str):
        return None
    s = raw.strip()
    if not s:
        return None
    # datetime-local: YYYY-MM-DDTHH:MM (optionally with seconds)
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


class WorkdaySessionService:
    """Business logic for workday sessions (legacy API, compliance-backed)."""

    def __init__(self):
        self.compliance = AttendanceComplianceService()

    def get_active_session(self, user_id: int) -> Optional[WorkdaySession]:
        return WorkdaySession.get_active_for_user(user_id)

    def is_overnight_open_session(self, session: Optional[WorkdaySession]) -> bool:
        """True when an active session started on a previous local calendar day."""
        if not session or not session.start_time or session.end_time is not None:
            return False
        return session.start_time.date() < local_now().date()

    def suggested_leave_datetime_local(self, session: WorkdaySession, user=None) -> str:
        """Default leave time for datetime-local inputs (start day at end-of-day preference)."""
        start_day = session.start_time.date()
        eod = "17:00"
        if user is not None:
            eod = (getattr(user, "smart_notify_end_of_day_time", None) or eod).strip() or eod
        try:
            parts = eod.split(":")
            hour, minute = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
        except (TypeError, ValueError, IndexError):
            hour, minute = 17, 0
        leave = datetime.combine(start_day, time(hour, minute))
        if leave <= session.start_time:
            leave = session.start_time + timedelta(hours=1)
        now = local_now()
        if leave > now:
            leave = now
        return leave.strftime("%Y-%m-%dT%H:%M")

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

    def end_workday(
        self,
        user_id: int,
        notes: Optional[str] = None,
        at_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        session = self.get_active_session(user_id)
        if not session:
            return {"success": False, "message": "No active workday session", "error": "no_active_workday"}

        if at_time is not None:
            if at_time.tzinfo is not None:
                at_time = at_time.replace(tzinfo=None)
            now = local_now()
            if at_time <= session.start_time:
                return {
                    "success": False,
                    "message": "Leave time must be after workday start",
                    "error": "invalid_end_time",
                }
            if at_time > now:
                return {
                    "success": False,
                    "message": "Leave time cannot be in the future",
                    "error": "invalid_end_time",
                }

        result = self.compliance.clock_out(user_id, notes=notes, at_time=at_time)
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

    def get_unconfirmed_auto_closed_session(
        self, user_id: int, lookback_days: int = 7
    ) -> Optional[WorkdaySession]:
        """Most recent auto-closed session the user has not yet confirmed or corrected."""
        cutoff = local_now() - timedelta(days=lookback_days)
        return (
            WorkdaySession.query.filter(
                WorkdaySession.user_id == user_id,
                WorkdaySession.auto_closed.is_(True),
                WorkdaySession.auto_close_confirmed_at.is_(None),
                WorkdaySession.start_time >= cutoff,
            )
            .order_by(WorkdaySession.start_time.desc())
            .first()
        )

    def resolve_auto_closed_session(
        self,
        user_id: int,
        session_id: int,
        *,
        end_time: Optional[datetime] = None,
        keep: bool = False,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Confirm or correct an auto-closed workday session."""
        session = WorkdaySession.query.filter_by(id=session_id, user_id=user_id).first()
        if not session:
            return {"success": False, "message": "Workday session not found", "error": "not_found"}
        if not session.auto_closed:
            return {"success": False, "message": "Session was not auto-closed", "error": "not_auto_closed"}
        if session.auto_close_confirmed_at is not None:
            return {
                "success": True,
                "message": "Auto-closed session already resolved",
                "session": session,
                "already_resolved": True,
            }

        now = local_now()
        auto_closed_end = session.end_time
        if not auto_closed_end:
            return {"success": False, "message": "Auto-closed session has no end time", "error": "invalid_session"}

        if keep:
            session.auto_close_confirmed_at = now
            if not safe_commit("confirm_auto_closed_workday", {"session_id": session_id}):
                return {"success": False, "message": "Could not save confirmation", "error": "database_error"}
            return {"success": True, "message": "Recorded time accepted", "session": session, "applied": True}

        if end_time is None:
            return {"success": False, "message": "Leave time is required", "error": "missing_end_time"}

        if end_time.tzinfo is not None:
            end_time = end_time.replace(tzinfo=None)

        max_end = min(now, auto_closed_end)
        if end_time <= session.start_time:
            return {
                "success": False,
                "message": "Leave time must be after workday start",
                "error": "invalid_end_time",
            }
        if end_time > now:
            return {
                "success": False,
                "message": "Leave time cannot be in the future",
                "error": "invalid_end_time",
            }
        if end_time > auto_closed_end:
            return {
                "success": False,
                "message": "Leave time cannot be later than the auto-closed end time",
                "error": "invalid_end_time",
            }

        work_date = session.start_time.date()
        period = AttendanceWorkPeriod.query.filter_by(workday_session_id=session.id).first()
        entity_id = period.id if period else 0
        original_values = period.to_dict() if period else {"end_time": auto_closed_end.isoformat()}
        corrected_values = {
            "start_time": session.start_time.isoformat(),
            "end_time": end_time.isoformat(),
        }
        correction_reason = (reason or "").strip() or "Corrected auto-closed workday leave time"

        day = self.compliance.get_or_create_day(user_id, work_date)
        locked = self.compliance.is_day_locked(user_id, work_date)

        if locked:
            result = self.compliance.request_correction(
                attendance_day_id=day.id,
                entity_type="AttendanceWorkPeriod",
                entity_id=entity_id,
                corrected_values=corrected_values,
                reason=correction_reason,
                requested_by=user_id,
                allow_locked=True,
            )
            if not result.get("success"):
                return result
            session.auto_close_confirmed_at = now
            audit_note = f"Auto-close correction submitted for review (requested leave: {end_time.isoformat()})"
            session.notes = (session.notes or "") + ("\n" if session.notes else "") + audit_note
            if not safe_commit("submit_auto_closed_correction", {"session_id": session_id}):
                return {"success": False, "message": "Could not save correction request", "error": "database_error"}
            return {
                "success": True,
                "message": "Correction submitted for admin review",
                "session": session,
                "correction": result.get("correction"),
                "applied": False,
                "pending_review": True,
            }

        session.end_time = end_time
        session.calculate_duration()
        audit_note = f"Auto-close corrected by user (leave: {end_time.isoformat()})"
        session.notes = (session.notes or "") + ("\n" if session.notes else "") + audit_note
        session.auto_close_confirmed_at = now
        self.compliance.mirror_workday_session(session)

        correction = AttendanceCorrection(
            attendance_day_id=day.id,
            entity_type="AttendanceWorkPeriod",
            entity_id=entity_id,
            original_values=original_values,
            corrected_values=corrected_values,
            reason=correction_reason,
            requested_by=user_id,
            status=AttendanceCorrectionStatus.APPLIED,
            applied_at=now,
        )
        db.session.add(correction)

        if not safe_commit("resolve_auto_closed_workday", {"session_id": session_id}):
            return {"success": False, "message": "Could not save corrected workday", "error": "database_error"}

        return {"success": True, "message": "Leave time corrected", "session": session, "applied": True}

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
