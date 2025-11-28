"""
Service for reporting and analytics business logic.

This service handles all reporting operations including:
- Time tracking summaries
- Project reports
- User reports
- Payment statistics
- Comparison reports (month-over-month, etc.)

All methods use the repository pattern for data access and include
optimized queries to prevent performance issues.

Example:
    service = ReportingService()
    summary = service.get_reports_summary(user_id=1, is_admin=False)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
from decimal import Decimal
from app import db
from app.repositories import TimeEntryRepository, ProjectRepository, InvoiceRepository, ExpenseRepository
from app.models import TimeEntry, Project, Invoice, Expense, Payment, User
from sqlalchemy import func


class ReportingService:
    """
    Service for reporting and analytics operations.

    Provides comprehensive reporting capabilities with optimized queries
    and aggregated statistics.
    """

    def __init__(self):
        """Initialize ReportingService with required repositories."""
        self.time_entry_repo = TimeEntryRepository()
        self.project_repo = ProjectRepository()
        self.invoice_repo = InvoiceRepository()
        self.expense_repo = ExpenseRepository()

    def get_time_summary(
        self,
        user_id: Optional[int] = None,
        project_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        billable_only: bool = False,
    ) -> Dict[str, Any]:
        """
        Get time tracking summary.

        Returns:
            dict with total hours, billable hours, entries count, etc.
        """
        if not start_date:
            start_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if not end_date:
            end_date = datetime.now()

        # Get total duration
        total_seconds = self.time_entry_repo.get_total_duration(
            user_id=user_id,
            project_id=project_id,
            start_date=start_date,
            end_date=end_date,
            billable_only=billable_only,
        )

        total_hours = total_seconds / 3600

        # Get billable duration
        billable_seconds = self.time_entry_repo.get_total_duration(
            user_id=user_id, project_id=project_id, start_date=start_date, end_date=end_date, billable_only=True
        )
        billable_hours = billable_seconds / 3600

        # Get entries
        entries = self.time_entry_repo.get_by_date_range(
            start_date=start_date, end_date=end_date, user_id=user_id, project_id=project_id, include_relations=False
        )

        return {
            "total_hours": round(total_hours, 2),
            "billable_hours": round(billable_hours, 2),
            "non_billable_hours": round(total_hours - billable_hours, 2),
            "total_entries": len(entries),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

    def get_reports_summary(self, user_id: Optional[int] = None, is_admin: bool = False) -> Dict[str, Any]:
        """
        Get comprehensive reports summary for dashboard.
        Uses optimized queries to prevent N+1 problems.

        Args:
            user_id: User ID for filtering (non-admin users)
            is_admin: Whether user is admin

        Returns:
            dict with summary statistics including:
            - total_hours, billable_hours
            - active_projects, total_users
            - payment statistics
            - recent_entries
            - month-over-month comparison
        """
        # Build base queries
        totals_query = db.session.query(func.sum(TimeEntry.duration_seconds)).filter(TimeEntry.end_time.isnot(None))
        billable_query = db.session.query(func.sum(TimeEntry.duration_seconds)).filter(
            TimeEntry.end_time.isnot(None), TimeEntry.billable == True
        )
        entries_query = TimeEntry.query.filter(TimeEntry.end_time.isnot(None))

        # Apply user filter if not admin
        if not is_admin and user_id:
            totals_query = totals_query.filter(TimeEntry.user_id == user_id)
            billable_query = billable_query.filter(TimeEntry.user_id == user_id)
            entries_query = entries_query.filter(TimeEntry.user_id == user_id)

        total_seconds = totals_query.scalar() or 0
        billable_seconds = billable_query.scalar() or 0

        # Get payment statistics (last 30 days)
        payment_query = db.session.query(
            func.sum(Payment.amount).label("total_payments"),
            func.count(Payment.id).label("payment_count"),
            func.sum(Payment.gateway_fee).label("total_fees"),
        ).filter(Payment.payment_date >= datetime.utcnow() - timedelta(days=30), Payment.status == "completed")

        if not is_admin and user_id:
            payment_query = (
                payment_query.join(Invoice).join(Project).join(TimeEntry).filter(TimeEntry.user_id == user_id)
            )

        payment_result = payment_query.first()

        # Get project and user counts
        active_projects = Project.query.filter_by(status="active").count()
        total_users = User.query.filter_by(is_active=True).count() if is_admin else 1

        summary = {
            "total_hours": round(total_seconds / 3600, 2),
            "billable_hours": round(billable_seconds / 3600, 2),
            "active_projects": active_projects,
            "total_users": total_users,
            "total_payments": float(payment_result.total_payments or 0) if payment_result else 0,
            "payment_count": payment_result.payment_count or 0 if payment_result else 0,
            "payment_fees": float(payment_result.total_fees or 0) if payment_result else 0,
        }

        # Get recent entries with eager loading
        from sqlalchemy.orm import joinedload

        recent_entries = (
            entries_query.options(joinedload(TimeEntry.project), joinedload(TimeEntry.user), joinedload(TimeEntry.task))
            .order_by(TimeEntry.start_time.desc())
            .limit(10)
            .all()
        )

        # Get comparison data for this month vs last month
        now = datetime.utcnow()
        this_month_start = datetime(now.year, now.month, 1)
        last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
        last_month_end = this_month_start - timedelta(seconds=1)

        # Get hours for this month
        this_month_query = db.session.query(func.sum(TimeEntry.duration_seconds)).filter(
            TimeEntry.end_time.isnot(None), TimeEntry.start_time >= this_month_start, TimeEntry.start_time <= now
        )
        if not is_admin and user_id:
            this_month_query = this_month_query.filter(TimeEntry.user_id == user_id)
        this_month_seconds = this_month_query.scalar() or 0

        # Get hours for last month
        last_month_query = db.session.query(func.sum(TimeEntry.duration_seconds)).filter(
            TimeEntry.end_time.isnot(None),
            TimeEntry.start_time >= last_month_start,
            TimeEntry.start_time <= last_month_end,
        )
        if not is_admin and user_id:
            last_month_query = last_month_query.filter(TimeEntry.user_id == user_id)
        last_month_seconds = last_month_query.scalar() or 0

        comparison = {
            "this_month": {"hours": round(this_month_seconds / 3600, 2)},
            "last_month": {"hours": round(last_month_seconds / 3600, 2)},
            "change": (
                ((this_month_seconds - last_month_seconds) / last_month_seconds * 100) if last_month_seconds > 0 else 0
            ),
        }

        return {"summary": summary, "recent_entries": recent_entries, "comparison": comparison}

    def get_project_summary(
        self, project_id: int, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get project summary with time, expenses, and invoices.

        Returns:
            dict with project statistics
        """
        project = self.project_repo.get_by_id(project_id)
        if not project:
            return {"error": "Project not found"}

        # Get time summary
        time_summary = self.get_time_summary(project_id=project_id, start_date=start_date, end_date=end_date)

        # Get expenses
        expenses = self.expense_repo.get_by_project(
            project_id=project_id,
            start_date=start_date.date() if start_date else None,
            end_date=end_date.date() if end_date else None,
        )
        total_expenses = sum(exp.amount for exp in expenses)

        # Get invoices
        invoices = self.invoice_repo.get_by_project(project_id)
        total_invoiced = sum(inv.total_amount for inv in invoices)

        # Calculate revenue
        billable_hours = time_summary["billable_hours"]
        hourly_rate = float(project.hourly_rate or Decimal("0"))
        potential_revenue = billable_hours * hourly_rate

        return {
            "project_id": project_id,
            "project_name": project.name,
            "time": time_summary,
            "expenses": {
                "total": float(total_expenses),
                "count": len(expenses),
                "billable": sum(exp.amount for exp in expenses if exp.billable),
            },
            "invoices": {
                "total": float(total_invoiced),
                "count": len(invoices),
                "paid": sum(inv.amount_paid or 0 for inv in invoices),
            },
            "revenue": {
                "potential": potential_revenue,
                "invoiced": float(total_invoiced),
                "paid": sum(float(inv.amount_paid or 0) for inv in invoices),
            },
        }

    def get_user_productivity(
        self, user_id: int, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get user productivity metrics.

        Returns:
            dict with productivity statistics
        """
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        # Get time summary
        time_summary = self.get_time_summary(user_id=user_id, start_date=start_date, end_date=end_date)

        # Get entries by project
        entries = self.time_entry_repo.get_by_date_range(
            start_date=start_date, end_date=end_date, user_id=user_id, include_relations=True
        )

        # Group by project
        project_hours = {}
        for entry in entries:
            project_id = entry.project_id
            hours = (entry.duration_seconds or 0) / 3600
            if project_id not in project_hours:
                project_hours[project_id] = {
                    "project_id": project_id,
                    "project_name": entry.project.name if entry.project else "Unknown",
                    "hours": 0,
                    "entries": 0,
                }
            project_hours[project_id]["hours"] += hours
            project_hours[project_id]["entries"] += 1

        return {
            "user_id": user_id,
            "time_summary": time_summary,
            "projects": list(project_hours.values()),
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": (end_date - start_date).days,
            },
        }
