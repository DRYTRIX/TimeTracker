"""
Service for analytics and insights business logic.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, case, func
from sqlalchemy.orm import joinedload

from app import db
from app.models import Project, TimeEntry
from app.repositories import ExpenseRepository, InvoiceRepository, ProjectRepository, TimeEntryRepository


class AnalyticsService:
    """Service for analytics operations"""

    def __init__(self):
        self.time_entry_repo = TimeEntryRepository()
        self.project_repo = ProjectRepository()
        self.invoice_repo = InvoiceRepository()
        self.expense_repo = ExpenseRepository()

    def get_dashboard_stats(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get dashboard statistics.

        Returns:
            dict with dashboard metrics
        """
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        # Today's time
        today_seconds = self.time_entry_repo.get_total_duration(
            user_id=user_id, start_date=today, end_date=datetime.now()
        )

        # This week's time
        week_seconds = self.time_entry_repo.get_total_duration(
            user_id=user_id, start_date=week_start, end_date=datetime.now()
        )

        # This month's time
        month_seconds = self.time_entry_repo.get_total_duration(
            user_id=user_id, start_date=month_start, end_date=datetime.now()
        )

        # Active projects
        active_projects = self.project_repo.get_active_projects(user_id=user_id)

        # Recent invoices
        recent_invoices = self.invoice_repo.get_by_status("sent", include_relations=False)[:5]

        # Overdue invoices
        overdue_invoices = self.invoice_repo.get_overdue(include_relations=False)

        return {
            "time_tracking": {
                "today_hours": round(today_seconds / 3600, 2),
                "week_hours": round(week_seconds / 3600, 2),
                "month_hours": round(month_seconds / 3600, 2),
            },
            "projects": {"active_count": len(active_projects)},
            "invoices": {
                "recent_count": len(recent_invoices),
                "overdue_count": len(overdue_invoices),
                "overdue_amount": sum(float(inv.total_amount - (inv.amount_paid or 0)) for inv in overdue_invoices),
            },
        }

    def get_dashboard_top_projects(self, user_id: int, days: int = 30, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get top projects by hours for the dashboard (DB GROUP BY to avoid loading all entries).
        Returns list of dicts with keys: project, hours, billable_hours (sorted by hours desc, limited).
        """
        period_start = datetime.utcnow().date() - timedelta(days=days)
        rows = (
            db.session.query(
                TimeEntry.project_id,
                func.sum(TimeEntry.duration_seconds).label("total_seconds"),
                func.sum(
                    case(
                        (and_(TimeEntry.billable == True, Project.billable == True), TimeEntry.duration_seconds),
                        else_=0,
                    )
                ).label("billable_seconds"),
            )
            .join(Project, TimeEntry.project_id == Project.id)
            .filter(
                TimeEntry.end_time.isnot(None),
                TimeEntry.start_time >= period_start,
                TimeEntry.user_id == user_id,
                TimeEntry.project_id.isnot(None),
            )
            .group_by(TimeEntry.project_id)
            .order_by(func.sum(TimeEntry.duration_seconds).desc())
            .limit(limit)
            .all()
        )
        project_ids = [r.project_id for r in rows]
        projects_by_id = (
            {p.id: p for p in Project.query.filter(Project.id.in_(project_ids)).all()} if project_ids else {}
        )
        result = []
        for r in rows:
            project = projects_by_id.get(r.project_id)
            if not project:
                continue
            total_seconds = int(r.total_seconds or 0)
            billable_seconds = int(r.billable_seconds or 0)
            result.append(
                {
                    "project": project,
                    "hours": round(total_seconds / 3600, 2),
                    "billable_hours": round(billable_seconds / 3600, 2),
                }
            )
        return result[:limit]

    def get_time_by_project_chart(self, user_id: int, days: int = 7, limit: int = 10) -> Dict[str, Any]:
        """
        Get time-by-project series for dashboard chart (DB GROUP BY to avoid loading all entries).
        Returns dict with keys: series (list of {label, hours}), chart_labels, chart_hours.
        """
        period_start = datetime.utcnow().date() - timedelta(days=days)
        rows = (
            db.session.query(
                Project.name,
                func.sum(TimeEntry.duration_seconds).label("total_seconds"),
            )
            .join(TimeEntry, TimeEntry.project_id == Project.id)
            .filter(
                TimeEntry.end_time.isnot(None),
                TimeEntry.start_time >= period_start,
                TimeEntry.user_id == user_id,
            )
            .group_by(TimeEntry.project_id, Project.name)
            .order_by(func.sum(TimeEntry.duration_seconds).desc())
            .limit(limit)
            .all()
        )
        series = [{"label": r.name or "", "hours": round((r.total_seconds or 0) / 3600, 2)} for r in rows]
        return {
            "series": series,
            "chart_labels": [x["label"] for x in series],
            "chart_hours": [x["hours"] for x in series],
        }

    def get_trends(self, user_id: Optional[int] = None, days: int = 30) -> Dict[str, Any]:
        """
        Get time tracking trends.

        Returns:
            dict with daily/hourly trends
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Get entries
        entries = self.time_entry_repo.get_by_date_range(
            start_date=start_date, end_date=end_date, user_id=user_id, include_relations=False
        )

        # Group by date
        daily_hours = {}
        for entry in entries:
            entry_date = entry.start_time.date()
            hours = (entry.duration_seconds or 0) / 3600
            if entry_date not in daily_hours:
                daily_hours[entry_date] = 0
            daily_hours[entry_date] += hours

        # Create trend data
        trend_data = []
        current_date = start_date.date()
        while current_date <= end_date.date():
            trend_data.append({"date": current_date.isoformat(), "hours": round(daily_hours.get(current_date, 0), 2)})
            current_date += timedelta(days=1)

        return {
            "period": {
                "start_date": start_date.date().isoformat(),
                "end_date": end_date.date().isoformat(),
                "days": days,
            },
            "daily_trends": trend_data,
            "total_hours": round(sum(daily_hours.values()), 2),
            "average_daily_hours": round(sum(daily_hours.values()) / days, 2) if days > 0 else 0,
        }
