"""
Client Report Service

Builds client-visible report data from get_portal_data and client-scoped queries.
All data respects client visibility boundaries (client_id, project_ids).
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.models import Project, Task
from app.models.client import Client


def build_report_data(
    client: Client,
    portal_data: Dict[str, Any],
    date_range_days: Optional[int] = 30,
) -> Dict[str, Any]:
    """
    Build first-version report data for the client portal.
    All inputs must already be client-scoped (portal_data from get_portal_data(client)).
    """
    projects = portal_data.get("projects") or []
    invoices = portal_data.get("invoices") or []
    time_entries = portal_data.get("time_entries") or []

    project_ids = [p.id for p in projects]

    # Time tracking summary
    total_hours = sum(entry.duration_hours for entry in time_entries)

    # Project hours and progress
    project_hours = {}
    for entry in time_entries:
        if entry.project_id:
            if entry.project_id not in project_hours:
                proj = entry.project
                project_hours[entry.project_id] = {
                    "project": proj,
                    "hours": 0.0,
                    "billable_hours": 0.0,
                    "estimated_hours": getattr(proj, "estimated_hours", None) if proj else None,
                    "budget_amount": getattr(proj, "budget_amount", None) if proj else None,
                }
            project_hours[entry.project_id]["hours"] += entry.duration_hours
            if getattr(entry, "billable", False):
                project_hours[entry.project_id]["billable_hours"] += entry.duration_hours

    # Ensure all client projects appear (even with 0 hours)
    for p in projects:
        if p.id not in project_hours:
            project_hours[p.id] = {
                "project": p,
                "hours": 0.0,
                "billable_hours": 0.0,
                "estimated_hours": getattr(p, "estimated_hours", None),
                "budget_amount": getattr(p, "budget_amount", None),
            }

    # Invoice / payment summary
    invoice_summary = {
        "total": sum(inv.total_amount for inv in invoices),
        "paid": sum(inv.total_amount for inv in invoices if inv.payment_status == "fully_paid"),
        "unpaid": sum(inv.outstanding_amount for inv in invoices if inv.payment_status != "fully_paid"),
        "overdue": sum(inv.outstanding_amount for inv in invoices if getattr(inv, "is_overdue", False)),
    }

    # Task/status summary (tasks under client's projects)
    task_summary = _task_summary_for_projects(project_ids)

    # Time by date (last N days)
    time_by_date = []
    if date_range_days and time_entries:
        cutoff = datetime.utcnow() - timedelta(days=date_range_days)
        by_date: Dict[str, float] = {}
        for entry in time_entries:
            if entry.start_time and entry.start_time >= cutoff:
                key = entry.start_time.date().isoformat()
                by_date[key] = by_date.get(key, 0) + entry.duration_hours
        time_by_date = [{"date": k, "hours": round(v, 2)} for k, v in sorted(by_date.items(), reverse=True)[:31]]

    # Recent time entries (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_entries = [e for e in time_entries if e.start_time and e.start_time >= thirty_days_ago]

    return {
        "total_hours": round(total_hours, 2),
        "project_hours": list(project_hours.values()),
        "invoice_summary": invoice_summary,
        "task_summary": task_summary,
        "time_by_date": time_by_date,
        "recent_entries": recent_entries,
    }


def _task_summary_for_projects(project_ids: List[int]) -> Dict[str, Any]:
    """Task counts by status for the given project IDs. Returns totals and per-project if small set."""
    if not project_ids:
        return {"by_status": {}, "total": 0, "by_project": []}
    tasks = Task.query.filter(Task.project_id.in_(project_ids)).all()
    by_status: Dict[str, int] = {}
    by_project: Dict[int, Dict[str, int]] = {}
    for t in tasks:
        status = t.status or "todo"
        by_status[status] = by_status.get(status, 0) + 1
        if t.project_id not in by_project:
            by_project[t.project_id] = {}
        by_project[t.project_id][status] = by_project[t.project_id].get(status, 0) + 1
    by_project_list = [
        {"project_id": pid, "by_status": by_project[pid]}
        for pid in sorted(by_project.keys())
    ]
    return {"by_status": by_status, "total": len(tasks), "by_project": by_project_list}
