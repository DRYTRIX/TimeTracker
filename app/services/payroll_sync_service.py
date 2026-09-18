"""Build and push payroll batches to Gusto / ADP."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional

from app import db
from app.models import TimeEntry, User
from app.models.payroll_sync_log import PayrollSyncLog
from app.utils.db import safe_commit

logger = logging.getLogger(__name__)


class PayrollSyncService:
    """Aggregate time entries into payroll batches and push via connectors."""

    def build_batch(self, period_start: date, period_end: date) -> Dict[str, Any]:
        entries = (
            TimeEntry.query.filter(TimeEntry.start_time >= datetime.combine(period_start, datetime.min.time()))
            .filter(TimeEntry.start_time < datetime.combine(period_end + timedelta(days=1), datetime.min.time()))
            .filter(TimeEntry.end_time.isnot(None))
            .all()
        )
        by_user: Dict[int, float] = {}
        for e in entries:
            hours = 0.0
            if hasattr(e, "duration_hours") and e.duration_hours is not None:
                hours = float(e.duration_hours)
            elif e.start_time and e.end_time:
                hours = (e.end_time - e.start_time).total_seconds() / 3600.0
            by_user[e.user_id] = by_user.get(e.user_id, 0.0) + hours

        employees = []
        for user_id, hours in by_user.items():
            user = User.query.get(user_id)
            employees.append(
                {
                    "user_id": user_id,
                    "employee_id": getattr(user, "employee_id", None) or str(user_id),
                    "email": getattr(user, "email", None),
                    "name": getattr(user, "username", None) or str(user_id),
                    "hours": round(hours, 2),
                    "job_worked": {"hours": round(hours, 2)},
                    "workerID": str(getattr(user, "employee_id", None) or user_id),
                    "payInputs": [{"hoursQuantity": round(hours, 2)}],
                }
            )

        return {
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "employees": employees,
            "employee_count": len(employees),
            "hours_total": round(sum(by_user.values()), 2),
        }

    def push_period(
        self,
        *,
        provider: str,
        integration,
        connector,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
        created_by: Optional[int] = None,
    ) -> Dict[str, Any]:
        today = date.today()
        if period_end is None:
            period_end = today
        if period_start is None:
            period_start = period_end - timedelta(days=13)

        batch = self.build_batch(period_start, period_end)
        log = PayrollSyncLog(
            provider=provider,
            integration_id=integration.id if integration else None,
            period_start=period_start,
            period_end=period_end,
            status="pending",
            employee_count=batch["employee_count"],
            hours_total=batch["hours_total"],
            payload_summary={"employees": [{"user_id": e["user_id"], "hours": e["hours"]} for e in batch["employees"]]},
            created_by=created_by,
        )
        db.session.add(log)
        safe_commit("payroll_sync_log_create", {"provider": provider})

        try:
            result = connector.push_payroll_batch(batch)
            if result.get("success"):
                log.status = "success"
                log.external_batch_id = result.get("external_batch_id")
            else:
                log.status = "failed"
                log.error_message = result.get("message") or "Push failed"
            log.completed_at = datetime.utcnow()
            safe_commit("payroll_sync_log_complete", {"id": log.id, "status": log.status})
            return {
                "success": bool(result.get("success")),
                "synced": batch["employee_count"] if result.get("success") else 0,
                "log": log.to_dict(),
                "message": result.get("message") or log.status,
            }
        except Exception as exc:
            logger.exception("Payroll push failed")
            log.status = "failed"
            log.error_message = str(exc)
            log.completed_at = datetime.utcnow()
            safe_commit("payroll_sync_log_error", {"id": log.id})
            return {"success": False, "synced": 0, "message": str(exc), "log": log.to_dict()}
