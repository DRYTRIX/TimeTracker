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

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app import db
from app.models import Expense, Invoice, InvoiceItem, Payment, Project, ProjectCost, TimeEntry, User
from app.repositories import ExpenseRepository, InvoiceRepository, ProjectRepository, TimeEntryRepository


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

        # Count entries without loading all rows
        total_entries = self.time_entry_repo.count_for_date_range(
            start_date=start_date, end_date=end_date, user_id=user_id, project_id=project_id
        )

        return {
            "total_hours": round(total_hours, 2),
            "billable_hours": round(billable_hours, 2),
            "non_billable_hours": round(total_hours - billable_hours, 2),
            "total_entries": total_entries,
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

    def get_week_in_review(self, user_id: Optional[int] = None, is_admin: bool = False) -> Dict[str, Any]:
        """
        Get a summary of the current week: total hours, billable vs non-billable, top projects.
        Uses the user's week_start_day for "this week" boundaries.
        """
        from app.models import User
        from app.utils.overtime import get_week_start_for_date

        user = User.query.get(user_id) if user_id else None
        if not user and user_id:
            return {"error": "User not found"}
        today = date.today() if hasattr(date, "today") else datetime.utcnow().date()
        week_start = get_week_start_for_date(today, user or object())
        week_end = week_start + timedelta(days=6)
        start_dt = datetime.combine(week_start, datetime.min.time())
        end_dt = datetime.combine(week_end, datetime.max.time().replace(microsecond=0))

        time_summary = self.get_time_summary(user_id=user_id, start_date=start_dt, end_date=end_dt, billable_only=False)
        entries = self.time_entry_repo.get_by_date_range(
            start_date=start_dt, end_date=end_dt, user_id=user_id, include_relations=True
        )

        project_hours = {}
        for entry in entries:
            key = (entry.project_id, entry.project.name if entry.project else "No project")
            if entry.project_id is None and entry.client_id:
                key = (None, entry.client.name if entry.client else "Direct (client)")
            elif entry.project_id is None:
                key = (None, "No project")
            name = key[1]
            if name not in project_hours:
                project_hours[name] = {"name": name, "hours": 0.0, "billable_hours": 0.0}
            h = (entry.duration_seconds or 0) / 3600
            project_hours[name]["hours"] += h
            if entry.billable:
                project_hours[name]["billable_hours"] += h

        top_projects = sorted(project_hours.values(), key=lambda x: x["hours"], reverse=True)[:10]

        return {
            "total_hours": time_summary["total_hours"],
            "billable_hours": time_summary["billable_hours"],
            "non_billable_hours": time_summary.get(
                "non_billable_hours", time_summary["total_hours"] - time_summary["billable_hours"]
            ),
            "entry_count": time_summary.get("total_entries", len(entries)),
            "top_projects": top_projects,
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
        }

    def get_comparison_data(
        self, period: str = "month", user_id: Optional[int] = None, can_view_all: bool = False
    ) -> Dict[str, Any]:
        """
        Get period-over-period comparison (current vs previous period hours).

        Args:
            period: "month" or "year"
            user_id: Current user ID (used when can_view_all is False)
            can_view_all: If True, include all users' time

        Returns:
            dict with current hours, previous hours, and change percent
        """
        now = datetime.utcnow()
        if period == "month":
            this_period_start = datetime(now.year, now.month, 1)
            last_period_start = (this_period_start - timedelta(days=1)).replace(day=1)
            last_period_end = this_period_start - timedelta(seconds=1)
        else:
            this_period_start = datetime(now.year, 1, 1)
            last_period_start = datetime(now.year - 1, 1, 1)
            last_period_end = datetime(now.year, 1, 1) - timedelta(seconds=1)

        current_query = db.session.query(func.sum(TimeEntry.duration_seconds)).filter(
            TimeEntry.end_time.isnot(None),
            TimeEntry.start_time >= this_period_start,
            TimeEntry.start_time <= now,
        )
        if not can_view_all and user_id is not None:
            current_query = current_query.filter(TimeEntry.user_id == user_id)
        current_seconds = current_query.scalar() or 0

        previous_query = db.session.query(func.sum(TimeEntry.duration_seconds)).filter(
            TimeEntry.end_time.isnot(None),
            TimeEntry.start_time >= last_period_start,
            TimeEntry.start_time <= last_period_end,
        )
        if not can_view_all and user_id is not None:
            previous_query = previous_query.filter(TimeEntry.user_id == user_id)
        previous_seconds = previous_query.scalar() or 0

        current_hours = round(current_seconds / 3600, 2)
        previous_hours = round(previous_seconds / 3600, 2)
        change = ((current_hours - previous_hours) / previous_hours * 100) if previous_hours > 0 else 0

        return {
            "current": {"hours": current_hours},
            "previous": {"hours": previous_hours},
            "change": round(change, 1),
        }

    def get_project_report_data(
        self,
        start_dt: datetime,
        end_dt: datetime,
        project_id: Optional[int] = None,
        user_id_filter: Optional[int] = None,
        current_user_id: int = None,
        can_view_all: bool = False,
    ) -> Dict[str, Any]:
        """
        Get aggregated project report data (entries, projects_data, summary).

        Caller must enforce permission: if not can_view_all and user_id_filter != current_user_id, do not call.
        """
        query = TimeEntry.query.filter(
            TimeEntry.end_time.isnot(None),
            TimeEntry.start_time >= start_dt,
            TimeEntry.start_time <= end_dt,
        )
        if not can_view_all and current_user_id is not None:
            query = query.filter(TimeEntry.user_id == current_user_id)
        if project_id:
            query = query.filter(TimeEntry.project_id == project_id)
        if user_id_filter is not None:
            query = query.filter(TimeEntry.user_id == user_id_filter)

        entries = (
            query.options(
                joinedload(TimeEntry.project).joinedload(Project.client_obj),
                joinedload(TimeEntry.user),
            )
            .order_by(TimeEntry.start_time.desc())
            .all()
        )

        projects_map = {}
        for entry in entries:
            project = entry.project
            if not project:
                continue
            if project.id not in projects_map:
                projects_map[project.id] = {
                    "id": project.id,
                    "name": project.name,
                    "client": project.client,
                    "description": project.description,
                    "billable": project.billable,
                    "hourly_rate": float(project.hourly_rate) if project.hourly_rate else None,
                    "total_hours": 0.0,
                    "billable_hours": 0.0,
                    "billable_amount": 0.0,
                    "total_costs": 0.0,
                    "billable_costs": 0.0,
                    "total_value": 0.0,
                    "user_totals": {},
                }
            agg = projects_map[project.id]
            hours = entry.duration_hours
            agg["total_hours"] += hours
            if entry.billable and project.billable:
                agg["billable_hours"] += hours
                if project.hourly_rate:
                    agg["billable_amount"] += hours * float(project.hourly_rate)
            username = entry.user.display_name if entry.user else "Unknown"
            agg["user_totals"][username] = agg["user_totals"].get(username, 0.0) + hours

        for pid, agg in projects_map.items():
            costs_query = ProjectCost.query.filter(
                ProjectCost.project_id == pid,
                ProjectCost.cost_date >= start_dt.date(),
                ProjectCost.cost_date <= end_dt.date(),
            )
            if user_id_filter is not None:
                costs_query = costs_query.filter(ProjectCost.user_id == user_id_filter)
            for cost in costs_query.all():
                agg["total_costs"] += float(cost.amount)
                if cost.billable:
                    agg["billable_costs"] += float(cost.amount)
            agg["total_value"] = agg["billable_amount"] + agg["billable_costs"]

        projects_data = []
        total_hours = 0.0
        billable_hours = 0.0
        total_billable_amount = 0.0
        total_costs = 0.0
        total_billable_costs = 0.0
        total_project_value = 0.0
        for agg in projects_map.values():
            total_hours += agg["total_hours"]
            billable_hours += agg["billable_hours"]
            total_billable_amount += agg["billable_amount"]
            total_costs += agg["total_costs"]
            total_billable_costs += agg["billable_costs"]
            total_project_value += agg["total_value"]
            agg["total_hours"] = round(agg["total_hours"], 1)
            agg["billable_hours"] = round(agg["billable_hours"], 1)
            agg["billable_amount"] = round(agg["billable_amount"], 2)
            agg["total_costs"] = round(agg["total_costs"], 2)
            agg["billable_costs"] = round(agg["billable_costs"], 2)
            agg["total_value"] = round(agg["total_value"], 2)
            agg["user_totals"] = [{"username": u, "hours": round(h, 1)} for u, h in agg["user_totals"].items()]
            projects_data.append(agg)

        summary = {
            "total_hours": round(total_hours, 1),
            "billable_hours": round(billable_hours, 1),
            "total_billable_amount": round(total_billable_amount, 2),
            "total_costs": round(total_costs, 2),
            "total_billable_costs": round(total_billable_costs, 2),
            "total_project_value": round(total_project_value, 2),
            "projects_count": len(projects_data),
        }
        return {"entries": entries, "projects_data": projects_data, "summary": summary}

    def get_unpaid_hours_report_data(
        self,
        start_dt: datetime,
        end_dt: datetime,
        client_id: Optional[int] = None,
        current_user_id: Optional[int] = None,
        can_view_all: bool = False,
    ) -> Dict[str, Any]:
        """
        Get unpaid hours report data: billable entries not in fully-paid invoices, grouped by client.

        Returns:
            dict with client_data (list of client aggregates) and summary.
        """
        from sqlalchemy.orm import joinedload

        query = TimeEntry.query.options(
            joinedload(TimeEntry.user),
            joinedload(TimeEntry.project),
            joinedload(TimeEntry.task),
            joinedload(TimeEntry.client),
        ).filter(
            TimeEntry.end_time.isnot(None),
            TimeEntry.billable == True,
            TimeEntry.start_time >= start_dt,
            TimeEntry.start_time <= end_dt,
        )
        if not can_view_all and current_user_id is not None:
            query = query.filter(TimeEntry.user_id == current_user_id)
        if client_id:
            query = query.filter(TimeEntry.client_id == client_id)
        all_entries = query.all()

        all_invoice_items = (
            InvoiceItem.query.join(Invoice)
            .filter(InvoiceItem.time_entry_ids.isnot(None), InvoiceItem.time_entry_ids != "")
            .all()
        )
        billed_entry_ids = set()
        for item in all_invoice_items:
            if not item.time_entry_ids:
                continue
            entry_ids = [int(eid.strip()) for eid in item.time_entry_ids.split(",") if eid.strip().isdigit()]
            inv = item.invoice
            if inv and getattr(inv, "payment_status", None) == "fully_paid":
                billed_entry_ids.update(entry_ids)
        unpaid_entries = [e for e in all_entries if e.id not in billed_entry_ids]

        client_totals = {}
        for entry in unpaid_entries:
            client = None
            if entry.client_id:
                client = getattr(entry, "client", None)
            elif entry.project and getattr(entry.project, "client_id", None):
                client = getattr(entry.project, "client_obj", None)
            if not client:
                continue
            cid = client.id
            if cid not in client_totals:
                client_totals[cid] = {
                    "client": client,
                    "total_hours": 0.0,
                    "billable_hours": 0.0,
                    "estimated_amount": 0.0,
                    "entries": [],
                    "projects": {},
                }
            hours = entry.duration_hours
            client_totals[cid]["total_hours"] += hours
            client_totals[cid]["billable_hours"] += hours
            client_totals[cid]["entries"].append(entry)
            if entry.project:
                pid = entry.project.id
                if pid not in client_totals[cid]["projects"]:
                    client_totals[cid]["projects"][pid] = {
                        "project": entry.project,
                        "hours": 0.0,
                        "rate": float(entry.project.hourly_rate) if entry.project.hourly_rate else 0.0,
                    }
                client_totals[cid]["projects"][pid]["hours"] += hours
            rate = 0.0
            if entry.project and entry.project.hourly_rate:
                rate = float(entry.project.hourly_rate)
            elif client and getattr(client, "default_hourly_rate", None):
                rate = float(client.default_hourly_rate)
            client_totals[cid]["estimated_amount"] += hours * rate

        client_data = []
        total_unpaid_hours = 0.0
        total_estimated_amount = 0.0
        for cid, data in client_totals.items():
            data["total_hours"] = round(data["total_hours"], 2)
            data["billable_hours"] = round(data["billable_hours"], 2)
            data["estimated_amount"] = round(data["estimated_amount"], 2)
            data["projects"] = list(data["projects"].values())
            for proj in data["projects"]:
                proj["hours"] = round(proj["hours"], 2)
            client_data.append(data)
            total_unpaid_hours += data["total_hours"]
            total_estimated_amount += data["estimated_amount"]
        client_data.sort(key=lambda x: x["total_hours"], reverse=True)
        summary = {
            "total_unpaid_hours": round(total_unpaid_hours, 2),
            "total_estimated_amount": round(total_estimated_amount, 2),
            "clients_count": len(client_data),
        }
        return {"client_data": client_data, "summary": summary}
