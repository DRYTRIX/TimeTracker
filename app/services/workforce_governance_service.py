from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import func, or_

from app import db
from app.models import AuditLog, TimeEntry, User
from app.models.time_entry import local_now
from app.models.time_off import CompanyHoliday, LeaveType, TimeOffRequest, TimeOffRequestStatus
from app.models.timesheet_period import TimesheetPeriod, TimesheetPeriodStatus
from app.models.timesheet_policy import TimesheetPolicy


class WorkforceGovernanceService:
    """Timesheet periods, time-off and compliance/capacity helpers."""

    def get_or_create_default_policy(self) -> TimesheetPolicy:
        policy = TimesheetPolicy.query.order_by(TimesheetPolicy.id.asc()).first()
        if policy:
            return policy
        policy = TimesheetPolicy()
        db.session.add(policy)
        db.session.commit()
        return policy

    def resolve_period_range(self, reference: date, period_type: str = "weekly") -> Dict[str, date]:
        if period_type != "weekly":
            period_type = "weekly"
        start = reference - timedelta(days=reference.weekday())
        end = start + timedelta(days=6)
        return {"period_start": start, "period_end": end}

    def get_or_create_period_for_date(self, user_id: int, reference: date, period_type: str = "weekly") -> TimesheetPeriod:
        rng = self.resolve_period_range(reference, period_type=period_type)
        period = TimesheetPeriod.query.filter_by(
            user_id=user_id,
            period_type=period_type,
            period_start=rng["period_start"],
            period_end=rng["period_end"],
        ).first()
        if period:
            return period
        period = TimesheetPeriod(
            user_id=user_id,
            period_type=period_type,
            period_start=rng["period_start"],
            period_end=rng["period_end"],
            status=TimesheetPeriodStatus.DRAFT,
        )
        db.session.add(period)
        db.session.commit()
        return period

    def list_periods(
        self,
        *,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
    ) -> List[TimesheetPeriod]:
        query = TimesheetPeriod.query
        if user_id is not None:
            query = query.filter(TimesheetPeriod.user_id == user_id)
        if status:
            query = query.filter(TimesheetPeriod.status == status)
        if period_start:
            query = query.filter(TimesheetPeriod.period_end >= period_start)
        if period_end:
            query = query.filter(TimesheetPeriod.period_start <= period_end)
        return query.order_by(TimesheetPeriod.period_start.desc()).all()

    def _has_open_timer_in_range(self, user_id: int, period: TimesheetPeriod) -> bool:
        open_timer = TimeEntry.query.filter(
            TimeEntry.user_id == user_id,
            TimeEntry.end_time.is_(None),
            TimeEntry.start_time >= datetime.combine(period.period_start, datetime.min.time()),
            TimeEntry.start_time <= datetime.combine(period.period_end, datetime.max.time()),
        ).first()
        return open_timer is not None

    def submit_period(self, period_id: int, actor_id: int) -> Dict[str, Any]:
        period = TimesheetPeriod.query.get(period_id)
        if not period:
            return {"success": False, "message": "Timesheet period not found"}
        if period.user_id != actor_id:
            return {"success": False, "message": "You can only submit your own period"}
        if period.status == TimesheetPeriodStatus.CLOSED:
            return {"success": False, "message": "Closed period cannot be submitted"}
        if self._has_open_timer_in_range(period.user_id, period):
            return {"success": False, "message": "Stop active timers in this period before submitting"}

        period.status = TimesheetPeriodStatus.SUBMITTED
        period.submitted_at = local_now()
        period.submitted_by = actor_id
        db.session.commit()
        return {"success": True, "period": period}

    def approve_period(self, period_id: int, approver_id: int, comment: Optional[str] = None) -> Dict[str, Any]:
        period = TimesheetPeriod.query.get(period_id)
        if not period:
            return {"success": False, "message": "Timesheet period not found"}
        if period.status not in (TimesheetPeriodStatus.SUBMITTED, TimesheetPeriodStatus.REJECTED):
            return {"success": False, "message": "Only submitted/rejected periods can be approved"}
        period.status = TimesheetPeriodStatus.APPROVED
        period.approved_by = approver_id
        period.approved_at = local_now()
        if comment:
            period.close_reason = comment
        db.session.commit()
        return {"success": True, "period": period}

    def reject_period(self, period_id: int, approver_id: int, reason: str) -> Dict[str, Any]:
        period = TimesheetPeriod.query.get(period_id)
        if not period:
            return {"success": False, "message": "Timesheet period not found"}
        if period.status != TimesheetPeriodStatus.SUBMITTED:
            return {"success": False, "message": "Only submitted periods can be rejected"}
        period.status = TimesheetPeriodStatus.REJECTED
        period.rejected_by = approver_id
        period.rejected_at = local_now()
        period.rejection_reason = reason
        db.session.commit()
        return {"success": True, "period": period}

    def close_period(self, period_id: int, closer_id: int, reason: Optional[str] = None) -> Dict[str, Any]:
        period = TimesheetPeriod.query.get(period_id)
        if not period:
            return {"success": False, "message": "Timesheet period not found"}
        if period.status == TimesheetPeriodStatus.CLOSED:
            return {"success": True, "period": period}

        period.status = TimesheetPeriodStatus.CLOSED
        period.closed_by = closer_id
        period.closed_at = local_now()
        if reason:
            period.close_reason = reason
        db.session.commit()
        return {"success": True, "period": period}

    def is_time_entry_locked(self, user_id: int, start_time: datetime, end_time: Optional[datetime] = None) -> bool:
        if end_time is None:
            end_time = start_time
        start_date = start_time.date()
        end_date = end_time.date()
        locked = TimesheetPeriod.query.filter(
            TimesheetPeriod.user_id == user_id,
            TimesheetPeriod.status == TimesheetPeriodStatus.CLOSED,
            TimesheetPeriod.period_start <= end_date,
            TimesheetPeriod.period_end >= start_date,
        ).first()
        return locked is not None

    def apply_auto_lock(self, actor_id: Optional[int] = None) -> int:
        policy = self.get_or_create_default_policy()
        if policy.auto_lock_days is None:
            return 0
        threshold = date.today() - timedelta(days=int(policy.auto_lock_days))
        candidates = TimesheetPeriod.query.filter(
            TimesheetPeriod.period_end <= threshold,
            TimesheetPeriod.status.in_([TimesheetPeriodStatus.APPROVED, TimesheetPeriodStatus.SUBMITTED]),
        ).all()
        count = 0
        for period in candidates:
            period.status = TimesheetPeriodStatus.CLOSED
            period.closed_at = local_now()
            period.closed_by = actor_id
            count += 1
        if count:
            db.session.commit()
        return count

    def list_leave_types(self, enabled_only: bool = True) -> List[LeaveType]:
        q = LeaveType.query
        if enabled_only:
            q = q.filter(LeaveType.enabled.is_(True))
        return q.order_by(LeaveType.name.asc()).all()

    def get_overtime_leave_type(self) -> Optional[LeaveType]:
        """Return the leave type used for overtime-as-paid-leave (code 'overtime'), if present."""
        return LeaveType.query.filter_by(code="overtime", enabled=True).first()

    def create_leave_request(
        self,
        *,
        user_id: int,
        leave_type_id: int,
        start_date: date,
        end_date: date,
        requested_hours: Optional[Decimal],
        comment: Optional[str],
        submit_now: bool = True,
    ) -> Dict[str, Any]:
        leave_type = LeaveType.query.get(leave_type_id)
        if not leave_type or not leave_type.enabled:
            return {"success": False, "message": "Invalid leave type"}
        if end_date < start_date:
            return {"success": False, "message": "end_date must be after start_date"}

        # When requesting overtime-as-leave, cap requested_hours at accumulated YTD overtime
        if leave_type.code == "overtime" and requested_hours is not None and requested_hours > 0:
            from app.utils.overtime import get_overtime_ytd

            user = User.query.get(user_id)
            if user:
                ytd = get_overtime_ytd(user)
                ytd_overtime = float(ytd.get("overtime_hours", 0) or 0)
                if float(requested_hours) > ytd_overtime:
                    return {
                        "success": False,
                        "message": f"Requested hours ({requested_hours}) exceed your accumulated overtime (YTD: {ytd_overtime:.2f}h). Please request at most {ytd_overtime:.2f} hours.",
                    }
            else:
                return {"success": False, "message": "User not found"}

        status = TimeOffRequestStatus.SUBMITTED if submit_now else TimeOffRequestStatus.DRAFT
        req = TimeOffRequest(
            user_id=user_id,
            leave_type_id=leave_type_id,
            start_date=start_date,
            end_date=end_date,
            requested_hours=requested_hours,
            requested_comment=comment,
            status=status,
            submitted_at=local_now() if submit_now else None,
        )
        db.session.add(req)
        db.session.commit()
        return {"success": True, "request": req}

    def review_leave_request(
        self,
        *,
        request_id: int,
        reviewer_id: int,
        approve: bool,
        comment: Optional[str],
    ) -> Dict[str, Any]:
        req = TimeOffRequest.query.get(request_id)
        if not req:
            return {"success": False, "message": "Request not found"}
        if req.status not in (TimeOffRequestStatus.SUBMITTED, TimeOffRequestStatus.DRAFT):
            return {"success": False, "message": "Request has already been processed"}

        req.status = TimeOffRequestStatus.APPROVED if approve else TimeOffRequestStatus.REJECTED
        req.reviewed_at = local_now()
        req.reviewed_by = reviewer_id
        req.review_comment = comment
        db.session.commit()
        return {"success": True, "request": req}

    def get_leave_balance(self, user_id: int) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        leave_types = self.list_leave_types(enabled_only=True)

        approved = (
            db.session.query(TimeOffRequest.leave_type_id, func.sum(TimeOffRequest.requested_hours))
            .filter(
                TimeOffRequest.user_id == user_id,
                TimeOffRequest.status == TimeOffRequestStatus.APPROVED,
                TimeOffRequest.requested_hours.isnot(None),
            )
            .group_by(TimeOffRequest.leave_type_id)
            .all()
        )
        used_by_type = {leave_type_id: float(total or 0) for leave_type_id, total in approved}

        for lt in leave_types:
            allowance = float(lt.annual_allowance_hours) if lt.annual_allowance_hours is not None else None
            used = used_by_type.get(lt.id, 0.0)
            remaining = None if allowance is None else round(allowance - used, 2)
            result.append(
                {
                    "leave_type_id": lt.id,
                    "leave_type_code": lt.code,
                    "leave_type_name": lt.name,
                    "allowance_hours": allowance,
                    "used_hours": used,
                    "remaining_hours": remaining,
                }
            )
        return result

    def is_holiday(self, day: date) -> bool:
        holiday = CompanyHoliday.query.filter(
            CompanyHoliday.enabled.is_(True),
            CompanyHoliday.start_date <= day,
            CompanyHoliday.end_date >= day,
        ).first()
        return holiday is not None

    def capacity_report(self, start_date: date, end_date: date, team_user_ids: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        user_query = User.query
        if team_user_ids:
            user_query = user_query.filter(User.id.in_(team_user_ids))
        users = user_query.order_by(User.username.asc()).all()

        rows: List[Dict[str, Any]] = []
        for user in users:
            default_daily_hours = float(getattr(user, "default_daily_working_hours", 8) or 8)
            working_days = 0
            day = start_date
            while day <= end_date:
                if day.weekday() < 5 and not self.is_holiday(day):
                    working_days += 1
                day += timedelta(days=1)
            expected_hours = round(working_days * default_daily_hours, 2)

            entry_seconds = (
                db.session.query(func.sum(TimeEntry.duration_seconds))
                .filter(
                    TimeEntry.user_id == user.id,
                    TimeEntry.start_time >= datetime.combine(start_date, datetime.min.time()),
                    TimeEntry.start_time <= datetime.combine(end_date, datetime.max.time()),
                    TimeEntry.end_time.isnot(None),
                )
                .scalar()
                or 0
            )
            allocated_hours = round(float(entry_seconds) / 3600.0, 2)

            leave_hours = (
                db.session.query(func.sum(TimeOffRequest.requested_hours))
                .filter(
                    TimeOffRequest.user_id == user.id,
                    TimeOffRequest.status == TimeOffRequestStatus.APPROVED,
                    TimeOffRequest.start_date <= end_date,
                    TimeOffRequest.end_date >= start_date,
                    TimeOffRequest.requested_hours.isnot(None),
                )
                .scalar()
                or 0
            )
            leave_hours = round(float(leave_hours), 2)

            available_hours = round(max(expected_hours - leave_hours - allocated_hours, 0), 2)
            utilization_pct = round((allocated_hours / expected_hours * 100.0), 2) if expected_hours > 0 else 0

            rows.append(
                {
                    "user_id": user.id,
                    "username": user.username,
                    "expected_hours": expected_hours,
                    "allocated_hours": allocated_hours,
                    "time_off_hours": leave_hours,
                    "available_hours": available_hours,
                    "utilization_pct": utilization_pct,
                }
            )
        return rows

    def locked_periods_report(self, start_date: Optional[date], end_date: Optional[date]) -> List[Dict[str, Any]]:
        query = TimesheetPeriod.query.filter(TimesheetPeriod.status == TimesheetPeriodStatus.CLOSED)
        if start_date:
            query = query.filter(TimesheetPeriod.period_end >= start_date)
        if end_date:
            query = query.filter(TimesheetPeriod.period_start <= end_date)
        periods = query.order_by(TimesheetPeriod.period_start.desc()).all()
        return [p.to_dict() for p in periods]

    def compliance_audit_events(
        self,
        *,
        start_date: Optional[date],
        end_date: Optional[date],
        user_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        query = AuditLog.query
        if user_id is not None:
            query = query.filter(AuditLog.user_id == user_id)
        if start_date:
            query = query.filter(AuditLog.created_at >= datetime.combine(start_date, datetime.min.time()))
        if end_date:
            query = query.filter(AuditLog.created_at <= datetime.combine(end_date, datetime.max.time()))

        query = query.filter(
            or_(
                AuditLog.entity_type.ilike("%timeentry%"),
                AuditLog.entity_type.ilike("%timesheet%"),
            )
        )

        events = query.order_by(AuditLog.created_at.desc()).limit(5000).all()
        rows: List[Dict[str, Any]] = []
        for ev in events:
            rows.append(
                {
                    "id": ev.id,
                    "created_at": ev.created_at.isoformat() if ev.created_at else None,
                    "user_id": ev.user_id,
                    "action": ev.action,
                    "entity_type": ev.entity_type,
                    "entity_id": ev.entity_id,
                    "entity_name": ev.entity_name,
                    "change_description": ev.change_description,
                    "reason": ev.reason,
                }
            )
        return rows

    def payroll_rows(
        self,
        *,
        start_date: date,
        end_date: date,
        user_id: Optional[int],
        approved_only: bool = False,
        closed_only: bool = False,
    ) -> List[Dict[str, Any]]:
        entries_query = TimeEntry.query.filter(
            TimeEntry.end_time.isnot(None),
            TimeEntry.start_time >= datetime.combine(start_date, datetime.min.time()),
            TimeEntry.start_time <= datetime.combine(end_date, datetime.max.time()),
        )
        if user_id is not None:
            entries_query = entries_query.filter(TimeEntry.user_id == user_id)

        rows: Dict[tuple, Dict[str, Any]] = {}
        for entry in entries_query.all():
            key = (entry.user_id, entry.start_time.date().isocalendar()[:2])

            if approved_only or closed_only:
                period = self.get_or_create_period_for_date(entry.user_id, entry.start_time.date(), period_type="weekly")
                status_value = period.status.value if hasattr(period.status, "value") else str(period.status)
                if approved_only and status_value != TimesheetPeriodStatus.APPROVED.value:
                    continue
                if closed_only and status_value != TimesheetPeriodStatus.CLOSED.value:
                    continue

            if key not in rows:
                week_year, week_no = entry.start_time.date().isocalendar()[0], entry.start_time.date().isocalendar()[1]
                rows[key] = {
                    "user_id": entry.user_id,
                    "username": entry.user.username if entry.user else None,
                    "week_year": week_year,
                    "week_number": week_no,
                    "period_start": None,
                    "period_end": None,
                    "hours": 0.0,
                    "billable_hours": 0.0,
                    "non_billable_hours": 0.0,
                }

            h = float(entry.duration_seconds or 0) / 3600.0
            rows[key]["hours"] += h
            if entry.billable:
                rows[key]["billable_hours"] += h
            else:
                rows[key]["non_billable_hours"] += h

        out = list(rows.values())
        for item in out:
            ref = date.fromisocalendar(item["week_year"], item["week_number"], 1)
            rng = self.resolve_period_range(ref, period_type="weekly")
            item["period_start"] = rng["period_start"].isoformat()
            item["period_end"] = rng["period_end"].isoformat()
            item["hours"] = round(item["hours"], 2)
            item["billable_hours"] = round(item["billable_hours"], 2)
            item["non_billable_hours"] = round(item["non_billable_hours"], 2)
        out.sort(key=lambda x: (x["week_year"], x["week_number"], x["username"] or ""))
        return out

    def delete_period(self, period_id: int, actor_id: int) -> Dict[str, Any]:
        """Delete a timesheet period. Only draft or rejected periods; actor must be owner or admin."""
        period = TimesheetPeriod.query.get(period_id)
        if not period:
            return {"success": False, "message": "Timesheet period not found"}
        user = User.query.get(actor_id)
        if not user:
            return {"success": False, "message": "User not found"}
        if period.user_id != actor_id and not user.is_admin:
            return {"success": False, "message": "Only the period owner or an admin can delete it"}
        status = period.status.value if hasattr(period.status, "value") else str(period.status)
        if status not in (TimesheetPeriodStatus.DRAFT.value, TimesheetPeriodStatus.REJECTED.value):
            return {"success": False, "message": "Only draft or rejected periods can be deleted"}
        db.session.delete(period)
        db.session.commit()
        return {"success": True}

    def delete_leave_request(
        self, request_id: int, actor_id: int, actor_can_approve: bool = False
    ) -> Dict[str, Any]:
        """Delete a time-off request. Only draft, submitted, or cancelled; actor must be owner or approver."""
        req = TimeOffRequest.query.get(request_id)
        if not req:
            return {"success": False, "message": "Time-off request not found"}
        if req.user_id != actor_id and not actor_can_approve:
            return {"success": False, "message": "Only the request owner or an approver can delete it"}
        status = req.status.value if hasattr(req.status, "value") else str(req.status)
        if status not in (
            TimeOffRequestStatus.DRAFT.value,
            TimeOffRequestStatus.SUBMITTED.value,
            TimeOffRequestStatus.CANCELLED.value,
        ):
            return {"success": False, "message": "Only draft, submitted, or cancelled requests can be deleted"}
        db.session.delete(req)
        db.session.commit()
        return {"success": True}

    def delete_leave_type(self, leave_type_id: int) -> Dict[str, Any]:
        """Delete a leave type. Fails if any time-off request references it."""
        leave_type = LeaveType.query.get(leave_type_id)
        if not leave_type:
            return {"success": False, "message": "Leave type not found"}
        if leave_type.requests.count() > 0:
            return {
                "success": False,
                "message": "Cannot delete leave type that has time-off requests",
            }
        db.session.delete(leave_type)
        db.session.commit()
        return {"success": True}

    def delete_holiday(self, holiday_id: int) -> Dict[str, Any]:
        """Delete a company holiday."""
        holiday = CompanyHoliday.query.get(holiday_id)
        if not holiday:
            return {"success": False, "message": "Holiday not found"}
        db.session.delete(holiday)
        db.session.commit()
        return {"success": True}
