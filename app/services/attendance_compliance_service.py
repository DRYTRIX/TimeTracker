"""
Unified attendance compliance service for Belgium/EU time registration requirements.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app import db
from app.models import Settings, User, WorkdaySession
from app.models.attendance_compliance import (
    AttendanceBreak,
    AttendanceBreakType,
    AttendanceCorrection,
    AttendanceCorrectionStatus,
    AttendanceDayStatus,
    AttendanceWorkPeriod,
    DailyAttendanceRecord,
)
from app.models.time_entry import local_now
from app.models.time_off import CompanyHoliday, TimeOffRequest, TimeOffRequestStatus
from app.models.timesheet_period import TimesheetPeriod, TimesheetPeriodStatus
from app.utils.db import safe_commit

BELGIUM_PRESET = {
    "compliance_jurisdiction_preset": "belgium",
    "compliance_standard_daily_hours": 8.0,
    "compliance_standard_weekly_hours": 38.0,
    "compliance_break_after_hours": 6.0,
    "compliance_min_break_minutes": 15,
    "compliance_min_daily_rest_hours": 11.0,
    "compliance_attendance_retention_years": 10,
    "compliance_require_workday_registration": True,
    "hour_limits_enabled": True,
    "daily_hour_limit": 10.0,
    "weekly_hour_limit": 48.0,
}


class AttendanceComplianceService:
    """Business logic for unified daily attendance compliance records."""

    def get_compliance_settings(self, user: Optional[User] = None) -> Dict[str, Any]:
        settings = Settings.get_settings()
        preset = getattr(settings, "compliance_jurisdiction_preset", "custom") or "custom"
        daily_hours = float(getattr(settings, "compliance_standard_daily_hours", 8.0) or 8.0)
        weekly_hours = float(getattr(settings, "compliance_standard_weekly_hours", 38.0) or 38.0)
        if user:
            if user.compliance_jurisdiction_preset:
                preset = user.compliance_jurisdiction_preset
            if user.compliance_standard_daily_hours is not None:
                daily_hours = float(user.compliance_standard_daily_hours)
            if user.compliance_standard_weekly_hours is not None:
                weekly_hours = float(user.compliance_standard_weekly_hours)
        return {
            "enabled": bool(getattr(settings, "compliance_enabled", False)),
            "jurisdiction_preset": preset,
            "standard_daily_hours": daily_hours,
            "standard_weekly_hours": weekly_hours,
            "break_after_hours": float(getattr(settings, "compliance_break_after_hours", 6.0) or 6.0),
            "min_break_minutes": int(getattr(settings, "compliance_min_break_minutes", 15) or 15),
            "min_daily_rest_hours": float(getattr(settings, "compliance_min_daily_rest_hours", 11.0) or 11.0),
            "retention_years": int(getattr(settings, "compliance_attendance_retention_years", 10) or 10),
            "require_workday_registration": bool(getattr(settings, "compliance_require_workday_registration", False)),
            "royal_decree_config": getattr(settings, "compliance_royal_decree_config", None),
        }

    def apply_belgium_preset(self, settings: Settings) -> None:
        for key, value in BELGIUM_PRESET.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        settings.compliance_enabled = True

    def get_or_create_day(self, user_id: int, work_date: date) -> DailyAttendanceRecord:
        record = DailyAttendanceRecord.query.filter_by(user_id=user_id, work_date=work_date).first()
        if record:
            return record
        record = DailyAttendanceRecord(user_id=user_id, work_date=work_date, status=AttendanceDayStatus.PRESENT)
        db.session.add(record)
        db.session.flush()
        return record

    def is_day_locked(self, user_id: int, work_date: date) -> bool:
        record = DailyAttendanceRecord.query.filter_by(user_id=user_id, work_date=work_date).first()
        if record and record.is_locked:
            return True
        locked_period = TimesheetPeriod.query.filter(
            TimesheetPeriod.user_id == user_id,
            TimesheetPeriod.status == TimesheetPeriodStatus.CLOSED,
            TimesheetPeriod.period_start <= work_date,
            TimesheetPeriod.period_end >= work_date,
        ).first()
        return locked_period is not None

    def get_active_work_period(self, user_id: int) -> Optional[AttendanceWorkPeriod]:
        return AttendanceWorkPeriod.query.filter_by(user_id=user_id, end_time=None).first()

    def get_active_break(self, user_id: int) -> Optional[AttendanceBreak]:
        return AttendanceBreak.query.filter_by(user_id=user_id, end_time=None).first()

    def can_start_work(self, user_id: int) -> Tuple[bool, Optional[str]]:
        if self.get_active_work_period(user_id):
            return False, "You already have an active workday session. End it before starting a new one."
        if self.get_active_break(user_id):
            return False, "End your break before starting work."
        return True, None

    def clock_in(
        self,
        user_id: int,
        notes: Optional[str] = None,
        source: str = "manual",
        at_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        now = at_time or local_now()
        work_date = now.date()
        if self.is_day_locked(user_id, work_date):
            return {
                "success": False,
                "message": "Attendance record is locked for this date",
                "error": "attendance_locked",
            }

        ok, msg = self.can_start_work(user_id)
        if not ok:
            return {"success": False, "message": msg, "error": "workday_already_active"}

        day = self.get_or_create_day(user_id, work_date)
        if day.status == AttendanceDayStatus.ABSENT:
            day.status = AttendanceDayStatus.PRESENT

        period = AttendanceWorkPeriod(
            attendance_day_id=day.id,
            user_id=user_id,
            start_time=now,
            notes=notes,
            source=source or "manual",
        )
        db.session.add(period)
        day.recalculate_totals()

        if not safe_commit("attendance_clock_in", {"user_id": user_id}):
            return {"success": False, "message": "Could not start workday", "error": "database_error"}

        return {"success": True, "message": "Workday started", "period": period, "day": day}

    def clock_out(
        self,
        user_id: int,
        notes: Optional[str] = None,
        at_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        now = at_time or local_now()
        period = self.get_active_work_period(user_id)
        if not period:
            return {"success": False, "message": "No active workday session", "error": "no_active_workday"}

        if self.is_day_locked(user_id, period.start_time.date()):
            return {
                "success": False,
                "message": "Attendance record is locked for this date",
                "error": "attendance_locked",
            }

        active_break = self.get_active_break(user_id)
        if active_break:
            self._end_break(active_break, now)

        period.end_time = now
        if notes:
            period.notes = (period.notes or "") + ("\n" if period.notes else "") + notes.strip()
        period.calculate_duration()

        day = period.attendance_day
        day.recalculate_totals()

        if not safe_commit("attendance_clock_out", {"user_id": user_id, "period_id": period.id}):
            return {"success": False, "message": "Could not end workday", "error": "database_error"}

        return {"success": True, "message": "Workday ended", "period": period, "day": day}

    def start_break(
        self,
        user_id: int,
        break_type: str = "rest",
        at_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        now = at_time or local_now()
        period = self.get_active_work_period(user_id)
        if not period:
            return {"success": False, "message": "Start work before taking a break", "error": "no_active_workday"}
        if self.get_active_break(user_id):
            return {"success": False, "message": "Break already in progress", "error": "break_already_active"}

        if self.is_day_locked(user_id, period.start_time.date()):
            return {
                "success": False,
                "message": "Attendance record is locked for this date",
                "error": "attendance_locked",
            }

        try:
            bt = AttendanceBreakType(break_type)
        except ValueError:
            bt = AttendanceBreakType.REST

        brk = AttendanceBreak(
            attendance_day_id=period.attendance_day_id,
            work_period_id=period.id,
            user_id=user_id,
            start_time=now,
            break_type=bt,
        )
        db.session.add(brk)
        period.attendance_day.recalculate_totals()

        if not safe_commit("attendance_start_break", {"user_id": user_id}):
            return {"success": False, "message": "Could not start break", "error": "database_error"}

        return {"success": True, "message": "Break started", "break": brk}

    def end_break(self, user_id: int, at_time: Optional[datetime] = None) -> Dict[str, Any]:
        now = at_time or local_now()
        brk = self.get_active_break(user_id)
        if not brk:
            return {"success": False, "message": "No active break", "error": "no_active_break"}

        if self.is_day_locked(user_id, brk.start_time.date()):
            return {
                "success": False,
                "message": "Attendance record is locked for this date",
                "error": "attendance_locked",
            }

        self._end_break(brk, now)
        day = brk.attendance_day
        day.recalculate_totals()

        if not safe_commit("attendance_end_break", {"user_id": user_id, "break_id": brk.id}):
            return {"success": False, "message": "Could not end break", "error": "database_error"}

        return {"success": True, "message": "Break ended", "break": brk}

    def _end_break(self, brk: AttendanceBreak, end_time: datetime) -> None:
        brk.end_time = end_time
        brk.calculate_duration()

    def get_status(self, user_id: int) -> Dict[str, Any]:
        period = self.get_active_work_period(user_id)
        brk = self.get_active_break(user_id)
        today = local_now().date()
        day = DailyAttendanceRecord.query.filter_by(user_id=user_id, work_date=today).first()
        return {
            "work_active": period is not None,
            "break_active": brk is not None,
            "work_period": period.to_dict() if period else None,
            "break": brk.to_dict() if brk else None,
            "today": day.to_dict(include_periods=True) if day else None,
        }

    def list_days(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> List[DailyAttendanceRecord]:
        from sqlalchemy.orm import joinedload

        query = DailyAttendanceRecord.query.filter(
            DailyAttendanceRecord.user_id == user_id,
            DailyAttendanceRecord.work_date >= start_date,
            DailyAttendanceRecord.work_date <= end_date,
        )
        query = query.options(joinedload(DailyAttendanceRecord.leave_type))
        return query.order_by(DailyAttendanceRecord.work_date.desc()).all()

    def sync_time_off_request(self, request: TimeOffRequest) -> int:
        if request.status != TimeOffRequestStatus.APPROVED:
            return 0
        count = 0
        day = request.start_date
        while day <= request.end_date:
            record = self.get_or_create_day(request.user_id, day)
            record.status = AttendanceDayStatus.ABSENT
            record.time_off_request_id = request.id
            record.leave_type_id = request.leave_type_id
            count += 1
            day += timedelta(days=1)
        safe_commit("sync_time_off_attendance", {"request_id": request.id, "count": count})
        return count

    def sync_all_approved_time_off(self, user_id: Optional[int] = None) -> int:
        query = TimeOffRequest.query.filter_by(status=TimeOffRequestStatus.APPROVED)
        if user_id is not None:
            query = query.filter_by(user_id=user_id)
        total = 0
        for req in query.all():
            total += self.sync_time_off_request(req)
        return total

    def sync_company_holidays(self, start_date: date, end_date: date) -> int:
        holidays = CompanyHoliday.query.filter(
            CompanyHoliday.enabled.is_(True),
            CompanyHoliday.end_date >= start_date,
            CompanyHoliday.start_date <= end_date,
        ).all()
        users = User.query.filter_by(is_active=True, portal_only=False).all()
        count = 0
        for holiday in holidays:
            day = max(holiday.start_date, start_date)
            last = min(holiday.end_date, end_date)
            while day <= last:
                for user in users:
                    record = self.get_or_create_day(user.id, day)
                    if record.status != AttendanceDayStatus.ABSENT:
                        record.status = AttendanceDayStatus.HOLIDAY
                        record.compliance_notes = holiday.name
                        count += 1
                day += timedelta(days=1)
        if count:
            safe_commit("sync_holiday_attendance", {"count": count})
        return count

    def lock_days_for_period(self, period: TimesheetPeriod, locker_id: int) -> int:
        days = DailyAttendanceRecord.query.filter(
            DailyAttendanceRecord.user_id == period.user_id,
            DailyAttendanceRecord.work_date >= period.period_start,
            DailyAttendanceRecord.work_date <= period.period_end,
        ).all()
        now = local_now()
        count = 0
        for day in days:
            if not day.is_locked:
                day.locked_at = now
                day.locked_by = locker_id
                day.timesheet_period_id = period.id
                count += 1
        if count:
            safe_commit("lock_attendance_days", {"period_id": period.id, "count": count})
        return count

    def compute_daily_rest_hours(self, user_id: int, work_date: date) -> Optional[float]:
        prev_day = work_date - timedelta(days=1)
        prev_periods = (
            AttendanceWorkPeriod.query.join(DailyAttendanceRecord)
            .filter(
                DailyAttendanceRecord.user_id == user_id,
                DailyAttendanceRecord.work_date == prev_day,
                AttendanceWorkPeriod.end_time.isnot(None),
            )
            .order_by(AttendanceWorkPeriod.end_time.desc())
            .all()
        )
        today_periods = (
            AttendanceWorkPeriod.query.join(DailyAttendanceRecord)
            .filter(
                DailyAttendanceRecord.user_id == user_id,
                DailyAttendanceRecord.work_date == work_date,
            )
            .order_by(AttendanceWorkPeriod.start_time.asc())
            .all()
        )
        if not prev_periods or not today_periods:
            return None
        prev_end = prev_periods[0].end_time
        today_start = today_periods[0].start_time
        if not prev_end or not today_start:
            return None
        return round((today_start - prev_end).total_seconds() / 3600.0, 2)

    def get_compliance_warnings(self, user_id: int, work_date: date) -> List[Dict[str, Any]]:
        user = User.query.get(user_id)
        if not user:
            return []
        cfg = self.get_compliance_settings(user)
        warnings: List[Dict[str, Any]] = []

        day = DailyAttendanceRecord.query.filter_by(user_id=user_id, work_date=work_date).first()
        if not day:
            return warnings

        work_hours = (day.total_work_seconds or 0) / 3600.0
        break_hours = (day.total_break_seconds or 0) / 3600.0

        if work_hours > cfg["standard_daily_hours"]:
            warnings.append(
                {
                    "type": "daily_hours_exceeded",
                    "message": f"Worked {work_hours:.2f}h exceeds standard {cfg['standard_daily_hours']}h",
                    "actual": work_hours,
                    "limit": cfg["standard_daily_hours"],
                }
            )

        if work_hours >= cfg["break_after_hours"] and break_hours < (cfg["min_break_minutes"] / 60.0):
            warnings.append(
                {
                    "type": "break_required",
                    "message": f"Break of at least {cfg['min_break_minutes']} min required after {cfg['break_after_hours']}h work",
                    "actual_break_minutes": int(break_hours * 60),
                    "required_minutes": cfg["min_break_minutes"],
                }
            )

        rest_hours = self.compute_daily_rest_hours(user_id, work_date)
        if rest_hours is not None and rest_hours < cfg["min_daily_rest_hours"]:
            warnings.append(
                {
                    "type": "insufficient_daily_rest",
                    "message": f"Only {rest_hours:.2f}h rest since previous shift (minimum {cfg['min_daily_rest_hours']}h)",
                    "actual": rest_hours,
                    "limit": cfg["min_daily_rest_hours"],
                }
            )

        return warnings

    def request_correction(
        self,
        *,
        attendance_day_id: int,
        entity_type: str,
        entity_id: int,
        corrected_values: Dict[str, Any],
        reason: str,
        requested_by: int,
    ) -> Dict[str, Any]:
        reason = (reason or "").strip()
        if not reason:
            return {"success": False, "message": "A reason is required for corrections"}

        day = DailyAttendanceRecord.query.get(attendance_day_id)
        if not day:
            return {"success": False, "message": "Attendance day not found"}
        requester = User.query.get(requested_by)
        if day.user_id != requested_by and not (requester and requester.is_admin):
            return {"success": False, "message": "You can only request corrections for your own attendance"}
        if day.is_locked:
            return {"success": False, "message": "Locked attendance records require admin-approved corrections"}

        if entity_type == "AddWorkPeriod":
            if day.work_periods.count() > 0:
                return {
                    "success": False,
                    "message": "This day already has work periods; edit an existing period instead",
                }
            if not corrected_values.get("start_time"):
                return {"success": False, "message": "Start time is required"}
            original_values: Dict[str, Any] = {}
        else:
            original_values = self._snapshot_entity(entity_type, entity_id)
            if original_values is None:
                return {"success": False, "message": "Entity not found"}

        correction = AttendanceCorrection(
            attendance_day_id=attendance_day_id,
            entity_type=entity_type,
            entity_id=entity_id or 0,
            original_values=original_values,
            corrected_values=corrected_values,
            reason=reason,
            requested_by=requested_by,
            status=AttendanceCorrectionStatus.PENDING,
        )
        db.session.add(correction)
        if not safe_commit("request_attendance_correction", {"correction_id": correction.id}):
            return {"success": False, "message": "Could not save correction request"}
        return {"success": True, "correction": correction}

    def request_missing_work_period(
        self,
        *,
        user_id: int,
        work_date: date,
        start_time: datetime,
        end_time: Optional[datetime],
        reason: str,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        if self.is_day_locked(user_id, work_date):
            return {"success": False, "message": "Attendance record is locked for this date"}
        day = self.get_or_create_day(user_id, work_date)
        corrected = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat() if end_time else None,
            "notes": notes,
        }
        return self.request_correction(
            attendance_day_id=day.id,
            entity_type="AddWorkPeriod",
            entity_id=0,
            corrected_values=corrected,
            reason=reason,
            requested_by=user_id,
        )

    def review_correction(
        self,
        correction_id: int,
        reviewer_id: int,
        approve: bool,
        review_comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        correction = AttendanceCorrection.query.get(correction_id)
        if not correction:
            return {"success": False, "message": "Correction not found"}
        if correction.status != AttendanceCorrectionStatus.PENDING:
            return {"success": False, "message": "Correction already reviewed"}

        correction.reviewed_by = reviewer_id
        correction.reviewed_at = local_now()
        correction.review_comment = review_comment

        if not approve:
            correction.status = AttendanceCorrectionStatus.REJECTED
            safe_commit("reject_attendance_correction", {"correction_id": correction_id})
            return {"success": True, "correction": correction, "applied": False}

        applied = self._apply_correction(correction)
        if not applied:
            return {"success": False, "message": "Could not apply correction"}

        correction.status = AttendanceCorrectionStatus.APPLIED
        correction.applied_at = local_now()
        safe_commit("apply_attendance_correction", {"correction_id": correction_id})
        return {"success": True, "correction": correction, "applied": True}

    def _snapshot_entity(self, entity_type: str, entity_id: int) -> Optional[Dict[str, Any]]:
        if entity_type == "AttendanceWorkPeriod":
            obj = AttendanceWorkPeriod.query.get(entity_id)
            return obj.to_dict() if obj else None
        if entity_type == "AttendanceBreak":
            obj = AttendanceBreak.query.get(entity_id)
            return obj.to_dict() if obj else None
        if entity_type == "DailyAttendanceRecord":
            obj = DailyAttendanceRecord.query.get(entity_id)
            return obj.to_dict() if obj else None
        return None

    def _apply_correction(self, correction: AttendanceCorrection) -> bool:
        values = correction.corrected_values or {}
        entity_type = correction.entity_type
        entity_id = correction.entity_id

        if entity_type == "AttendanceWorkPeriod":
            period = AttendanceWorkPeriod.query.get(entity_id)
            if not period:
                return False
            if "start_time" in values and values["start_time"]:
                period.start_time = datetime.fromisoformat(values["start_time"])
            if "end_time" in values:
                period.end_time = datetime.fromisoformat(values["end_time"]) if values["end_time"] else None
            if "notes" in values:
                period.notes = values["notes"]
            period.calculate_duration()
            period.attendance_day.recalculate_totals()
        elif entity_type == "AttendanceBreak":
            brk = AttendanceBreak.query.get(entity_id)
            if not brk:
                return False
            if "start_time" in values and values["start_time"]:
                brk.start_time = datetime.fromisoformat(values["start_time"])
            if "end_time" in values:
                brk.end_time = datetime.fromisoformat(values["end_time"]) if values["end_time"] else None
            brk.calculate_duration()
            brk.attendance_day.recalculate_totals()
        elif entity_type == "DailyAttendanceRecord":
            day = DailyAttendanceRecord.query.get(entity_id)
            if not day:
                return False
            if "status" in values:
                try:
                    day.status = AttendanceDayStatus(values["status"])
                except ValueError:
                    pass
            if "compliance_notes" in values:
                day.compliance_notes = values["compliance_notes"]
        elif entity_type == "AddWorkPeriod":
            day = DailyAttendanceRecord.query.get(correction.attendance_day_id)
            if not day:
                return False
            if day.work_periods.count() > 0:
                return False
            start_raw = values.get("start_time")
            if not start_raw:
                return False
            start_time = datetime.fromisoformat(start_raw)
            end_time = None
            if values.get("end_time"):
                end_time = datetime.fromisoformat(values["end_time"])
            period = AttendanceWorkPeriod(
                attendance_day_id=day.id,
                user_id=day.user_id,
                start_time=start_time,
                end_time=end_time,
                notes=values.get("notes"),
                source="correction",
            )
            db.session.add(period)
            period.calculate_duration()
            if day.status == AttendanceDayStatus.ABSENT:
                day.status = AttendanceDayStatus.PRESENT
            day.recalculate_totals()
        else:
            return False
        return True

    def auto_close_stale_sessions(self, max_hours: int = 18) -> int:
        cutoff = local_now() - timedelta(hours=max_hours)
        stale = AttendanceWorkPeriod.query.filter(
            AttendanceWorkPeriod.end_time.is_(None),
            AttendanceWorkPeriod.start_time < cutoff,
        ).all()
        count = 0
        for period in stale:
            period.end_time = period.start_time + timedelta(hours=max_hours)
            period.auto_closed = True
            period.calculate_duration()
            period.attendance_day.recalculate_totals()
            count += 1
        if count:
            safe_commit("auto_close_stale_attendance", {"count": count})
        return count

    def get_total_hours(self, user_id: int, start_date: date, end_date: date) -> float:
        records = self.list_days(user_id, start_date, end_date)
        total_seconds = sum(r.total_work_seconds or 0 for r in records)
        return round(total_seconds / 3600.0, 2)

    def belgium_inspector_rows(
        self,
        *,
        start_date: date,
        end_date: date,
        user_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        from app.compliance.belgium_config import merged_belgium_config

        settings = Settings.get_settings()
        decree_cfg = merged_belgium_config(settings)
        query = DailyAttendanceRecord.query.filter(
            DailyAttendanceRecord.work_date >= start_date,
            DailyAttendanceRecord.work_date <= end_date,
        )
        if user_id is not None:
            query = query.filter(DailyAttendanceRecord.user_id == user_id)
        records = query.order_by(DailyAttendanceRecord.work_date.asc(), DailyAttendanceRecord.user_id.asc()).all()

        rows: List[Dict[str, Any]] = []
        for record in records:
            user = record.user
            cfg = self.get_compliance_settings(user)
            periods = record.work_periods.order_by(AttendanceWorkPeriod.start_time.asc()).all()
            breaks = record.breaks.order_by(AttendanceBreak.start_time.asc()).all()
            corrections = record.corrections.order_by(AttendanceCorrection.created_at.desc()).all()

            work_starts = "; ".join(p.start_time.isoformat() for p in periods if p.start_time)
            work_ends = "; ".join(p.end_time.isoformat() for p in periods if p.end_time)
            break_starts = "; ".join(b.start_time.isoformat() for b in breaks if b.start_time)
            break_ends = "; ".join(b.end_time.isoformat() for b in breaks if b.end_time)

            status = record.status.value if isinstance(record.status, AttendanceDayStatus) else str(record.status)
            rest_hours = self.compute_daily_rest_hours(record.user_id, record.work_date)
            work_hours = round((record.total_work_seconds or 0) / 3600.0, 2)
            overtime = round(max(0, work_hours - cfg["standard_daily_hours"]), 2)

            rows.append(
                {
                    "user_id": record.user_id,
                    "username": user.username if user else "",
                    "display_name": user.display_name if user else "",
                    "work_date": record.work_date.isoformat(),
                    "status": status,
                    "absence_type": record.leave_type.name if record.leave_type else "",
                    "time_off_request_id": record.time_off_request_id,
                    "work_period_starts": work_starts,
                    "work_period_ends": work_ends,
                    "break_starts": break_starts,
                    "break_ends": break_ends,
                    "net_work_hours": work_hours,
                    "break_hours": round((record.total_break_seconds or 0) / 3600.0, 2),
                    "daily_rest_hours": rest_hours,
                    "standard_daily_hours": cfg["standard_daily_hours"],
                    "overtime_hours": overtime,
                    "correction_count": len(corrections),
                    "last_correction_reason": corrections[0].reason if corrections else "",
                    "locked": "yes" if record.is_locked else "no",
                    "locked_at": record.locked_at.isoformat() if record.locked_at else "",
                    "has_other_employers": "yes" if user and user.has_other_employers else "no",
                    "other_employers_note": (user.other_employers_note or "") if user else "",
                    "royal_decree_config_version": decree_cfg.get("version", ""),
                }
            )
            for col in decree_cfg.get("export_columns_extra") or []:
                if col not in rows[-1]:
                    rows[-1][col] = ""
        return rows

    def mirror_workday_session(self, session: WorkdaySession) -> None:
        """Keep legacy WorkdaySession in sync when created outside this service."""
        work_date = session.start_time.date()
        day = self.get_or_create_day(session.user_id, work_date)
        existing = AttendanceWorkPeriod.query.filter_by(workday_session_id=session.id).first()
        if existing:
            existing.start_time = session.start_time
            existing.end_time = session.end_time
            existing.duration_seconds = session.duration_seconds
            existing.auto_closed = session.auto_closed
            existing.notes = session.notes
            existing.source = session.source or "manual"
        else:
            period = AttendanceWorkPeriod(
                attendance_day_id=day.id,
                user_id=session.user_id,
                start_time=session.start_time,
                end_time=session.end_time,
                duration_seconds=session.duration_seconds,
                source=session.source or "manual",
                auto_closed=session.auto_closed,
                notes=session.notes,
                workday_session_id=session.id,
            )
            db.session.add(period)
        day.recalculate_totals()
