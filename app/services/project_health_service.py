"""Aggregated project health metrics."""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List

from sqlalchemy import func

from app import db
from app.models import Expense, Milestone, Project, Task, TimeEntry, User


class ProjectHealthService:
    @staticmethod
    def get_health(project: Project) -> Dict[str, Any]:
        tasks = Task.query.filter_by(project_id=project.id).all()
        total_tasks = len(tasks)
        done_tasks = sum(1 for t in tasks if t.status == "done")
        overdue_tasks = [t for t in tasks if t.is_overdue]
        completion = round((done_tasks / total_tasks) * 100, 1) if total_tasks else 0.0

        hours_tracked = float(project.actual_hours or 0)
        hours_budget = float(project.estimated_hours or 0)
        hours_remaining = round(hours_budget - hours_tracked, 2) if hours_budget else None

        time_cost = float(project.budget_consumed_amount or 0)
        extra_costs = float(project.total_costs or 0)
        expenses_total = float(
            db.session.query(func.coalesce(func.sum(Expense.amount + func.coalesce(Expense.tax_amount, 0)), 0))
            .filter(Expense.project_id == project.id)
            .scalar()
            or 0
        )
        consumed = time_cost + extra_costs + expenses_total
        budget = float(project.budget_amount) if project.budget_amount else 0.0
        burn_pct = round((consumed / budget) * 100, 1) if budget else 0.0

        milestones = Milestone.query.filter_by(project_id=project.id).all()
        upcoming = sum(1 for m in milestones if m.status in ("upcoming", "in_progress") and not m.is_overdue)
        missed = sum(1 for m in milestones if m.status == "missed" or m.is_overdue)
        completed_ms = sum(1 for m in milestones if m.status == "completed")

        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        contributor_rows = (
            db.session.query(
                User.id,
                User.username,
                User.full_name,
                func.sum(TimeEntry.duration_seconds).label("seconds"),
            )
            .join(TimeEntry, TimeEntry.user_id == User.id)
            .filter(
                TimeEntry.project_id == project.id,
                TimeEntry.end_time.isnot(None),
                TimeEntry.start_time >= month_start,
            )
            .group_by(User.id, User.username, User.full_name)
            .order_by(func.sum(TimeEntry.duration_seconds).desc())
            .limit(5)
            .all()
        )
        contributors = [
            {
                "id": row.id,
                "name": row.full_name or row.username,
                "hours": round((row.seconds or 0) / 3600, 2),
            }
            for row in contributor_rows
        ]

        weekly = ProjectHealthService._weekly_spend(project, weeks=12)

        if budget and burn_pct >= 100:
            status = "red"
        elif overdue_tasks or missed or (budget and burn_pct >= (project.budget_threshold_percent or 80)):
            status = "amber"
        else:
            status = "green"

        return {
            "status": status,
            "budget": {
                "amount": budget,
                "consumed": round(consumed, 2),
                "burn_percent": burn_pct,
            },
            "tasks": {
                "total": total_tasks,
                "done": done_tasks,
                "overdue": len(overdue_tasks),
                "completion_percent": completion,
            },
            "hours": {
                "tracked": round(hours_tracked, 2),
                "budget": hours_budget or None,
                "remaining": hours_remaining,
            },
            "milestones": {
                "total": len(milestones),
                "upcoming": upcoming,
                "missed": missed,
                "completed": completed_ms,
            },
            "contributors": contributors,
            "overdue_tasks": [
                {"id": t.id, "name": t.name, "due_date": t.due_date.isoformat() if t.due_date else None}
                for t in overdue_tasks[:20]
            ],
            "weekly_spend": weekly,
        }

    @staticmethod
    def _weekly_spend(project: Project, weeks: int = 12) -> List[Dict[str, Any]]:
        end = date.today()
        start = end - timedelta(days=weeks * 7)
        start_dt = datetime.combine(start, datetime.min.time())
        entries = (
            TimeEntry.query.filter(
                TimeEntry.project_id == project.id,
                TimeEntry.end_time.isnot(None),
                TimeEntry.start_time >= start_dt,
            )
            .with_entities(TimeEntry.start_time, TimeEntry.duration_seconds)
            .all()
        )
        buckets = {}
        for start_time, seconds in entries:
            if not start_time:
                continue
            iso = start_time.isocalendar()
            key = f"{iso[0]}-W{iso[1]:02d}"
            buckets[key] = buckets.get(key, 0) + (seconds or 0)
        rate = float(project.hourly_rate or 0)
        return [{"week": week, "amount": round((secs / 3600) * rate, 2)} for week, secs in sorted(buckets.items())]
