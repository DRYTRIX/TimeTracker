"""Utilization (billable vs total hours) calculations."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import case, func

from app import db
from app.models import Project, TimeEntry, User


class UtilizationService:
    @staticmethod
    def _seconds_to_hours(value) -> float:
        return round((value or 0) / 3600.0, 2)

    @classmethod
    def for_user_period(cls, user_id: int, start: datetime, end: datetime) -> Dict[str, Any]:
        rows = cls._aggregate(start, end, user_ids=[user_id], group_by="user")
        if not rows:
            return {"billable_hours": 0.0, "total_hours": 0.0, "utilization_rate": 0.0}
        return rows[0]

    @classmethod
    def _aggregate(
        cls,
        start: datetime,
        end: datetime,
        user_ids: Optional[List[int]] = None,
        group_by: str = "user",
    ) -> List[Dict[str, Any]]:
        billable_seconds = func.sum(case((TimeEntry.billable.is_(True), TimeEntry.duration_seconds), else_=0))
        total_seconds = func.sum(TimeEntry.duration_seconds)

        if group_by == "project":
            query = db.session.query(
                TimeEntry.project_id.label("group_id"),
                Project.name.label("group_name"),
                billable_seconds.label("billable_seconds"),
                total_seconds.label("total_seconds"),
            ).outerjoin(Project, TimeEntry.project_id == Project.id)
        else:
            query = db.session.query(
                TimeEntry.user_id.label("group_id"),
                User.username.label("group_name"),
                User.full_name.label("full_name"),
                billable_seconds.label("billable_seconds"),
                total_seconds.label("total_seconds"),
            ).join(User, TimeEntry.user_id == User.id)

        query = query.filter(
            TimeEntry.end_time.isnot(None),
            TimeEntry.start_time >= start,
            TimeEntry.start_time <= end,
        )
        if user_ids:
            query = query.filter(TimeEntry.user_id.in_(user_ids))

        if group_by == "project":
            query = query.group_by(TimeEntry.project_id, Project.name)
        else:
            query = query.group_by(TimeEntry.user_id, User.username, User.full_name)

        results = []
        for row in query.all():
            total = cls._seconds_to_hours(row.total_seconds)
            billable = cls._seconds_to_hours(row.billable_seconds)
            rate = round((billable / total) * 100, 1) if total else 0.0
            name = getattr(row, "full_name", None) or row.group_name or ("Unassigned" if group_by == "project" else "")
            results.append(
                {
                    "id": row.group_id,
                    "name": name,
                    "billable_hours": billable,
                    "non_billable_hours": round(total - billable, 2),
                    "total_hours": total,
                    "utilization_rate": rate,
                }
            )
        results.sort(key=lambda r: r["utilization_rate"], reverse=True)
        return results
