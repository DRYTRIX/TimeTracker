"""
Data export utilities for GDPR compliance and general export functionality
"""

import json
import csv
import os
from datetime import datetime, timedelta
from io import StringIO, BytesIO
from zipfile import ZipFile
from flask import current_app
from app import db
from app.models import (
    User,
    Project,
    TimeEntry,
    Task,
    Client,
    Invoice,
    InvoiceItem,
    Expense,
    ExpenseCategory,
    Mileage,
    PerDiem,
    Comment,
    FocusSession,
    RecurringBlock,
    Payment,
    CreditNote,
    SavedFilter,
    ProjectCost,
    WeeklyTimeGoal,
    Activity,
    CalendarEvent,
    BudgetAlert,
)


def export_user_data_gdpr(user_id, export_format="json"):
    """
    Export all user data for GDPR compliance

    Args:
        user_id: ID of the user whose data to export
        export_format: Format to export ('json', 'csv', 'zip')

    Returns:
        Dictionary with file path and metadata
    """
    user = User.query.get(user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")

    # Collect all user data
    data = {
        "export_info": {
            "user_id": user_id,
            "username": user.username,
            "export_date": datetime.utcnow().isoformat(),
            "export_type": "GDPR Full Data Export",
        },
        "user_profile": _export_user_profile(user),
        "time_entries": _export_time_entries(user),
        "projects": _export_user_projects(user),
        "tasks": _export_user_tasks(user),
        "expenses": _export_user_expenses(user),
        "mileage": _export_user_mileage(user),
        "per_diems": _export_user_per_diems(user),
        "invoices": _export_user_invoices(user),
        "comments": _export_user_comments(user),
        "focus_sessions": _export_user_focus_sessions(user),
        "saved_filters": _export_user_saved_filters(user),
        "project_costs": _export_user_project_costs(user),
        "weekly_goals": _export_user_weekly_goals(user),
        "activities": _export_user_activities(user),
        "calendar_events": _export_user_calendar_events(user),
    }

    # Generate export file
    export_dir = os.path.join(current_app.config.get("UPLOAD_FOLDER", "/data/uploads"), "exports")
    os.makedirs(export_dir, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"gdpr_export_{user.username}_{timestamp}"

    if export_format == "json":
        filepath = os.path.join(export_dir, f"{filename}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        file_size = os.path.getsize(filepath)

    elif export_format == "zip":
        # Create ZIP with separate CSV files for each data type
        filepath = os.path.join(export_dir, f"{filename}.zip")
        with ZipFile(filepath, "w") as zipf:
            # Add JSON version
            zipf.writestr(f"{filename}.json", json.dumps(data, indent=2, ensure_ascii=False, default=str))

            # Add CSV files for each data type
            for key, value in data.items():
                if key != "export_info" and isinstance(value, list) and len(value) > 0:
                    csv_content = _list_to_csv(value)
                    zipf.writestr(f"{key}.csv", csv_content)

        file_size = os.path.getsize(filepath)

    else:
        raise ValueError(f"Unsupported export format: {export_format}")

    record_count = sum(len(v) if isinstance(v, list) else 1 for v in data.values())

    return {
        "filepath": filepath,
        "file_size": file_size,
        "record_count": record_count,
        "filename": os.path.basename(filepath),
    }


def export_filtered_data(user_id, filters, export_format="json"):
    """
    Export filtered data based on user criteria

    Args:
        user_id: ID of the user requesting export
        filters: Dictionary with filter criteria
        export_format: Format to export ('json', 'csv', 'xlsx')

    Returns:
        Dictionary with file path and metadata
    """
    user = User.query.get(user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")

    data = {}

    # Export time entries with filters
    if filters.get("include_time_entries", True):
        query = TimeEntry.query

        if not user.is_admin:
            query = query.filter_by(user_id=user_id)

        if filters.get("start_date"):
            start_date = datetime.fromisoformat(filters["start_date"])
            query = query.filter(TimeEntry.start_time >= start_date)

        if filters.get("end_date"):
            end_date = datetime.fromisoformat(filters["end_date"])
            query = query.filter(TimeEntry.start_time <= end_date)

        if filters.get("project_id"):
            query = query.filter_by(project_id=filters["project_id"])

        if filters.get("billable_only"):
            query = query.filter_by(billable=True)

        time_entries = query.all()
        data["time_entries"] = [_time_entry_to_dict(te) for te in time_entries]

    # Export other data types based on filters
    if filters.get("include_projects"):
        projects = Project.query.all() if user.is_admin else []
        data["projects"] = [_project_to_dict(p) for p in projects]

    if filters.get("include_expenses"):
        query = Expense.query
        if not user.is_admin:
            query = query.filter_by(user_id=user_id)
        expenses = query.all()
        data["expenses"] = [_expense_to_dict(e) for e in expenses]

    # Generate export file
    export_dir = os.path.join(current_app.config.get("UPLOAD_FOLDER", "/data/uploads"), "exports")
    os.makedirs(export_dir, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"filtered_export_{user.username}_{timestamp}"

    if export_format == "json":
        filepath = os.path.join(export_dir, f"{filename}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        file_size = os.path.getsize(filepath)

    elif export_format == "csv":
        # Export as single CSV (time entries)
        filepath = os.path.join(export_dir, f"{filename}.csv")
        if "time_entries" in data:
            csv_content = _list_to_csv(data["time_entries"])
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(csv_content)
        file_size = os.path.getsize(filepath)

    else:
        raise ValueError(f"Unsupported export format: {export_format}")

    record_count = sum(len(v) if isinstance(v, list) else 1 for v in data.values())

    return {
        "filepath": filepath,
        "file_size": file_size,
        "record_count": record_count,
        "filename": os.path.basename(filepath),
    }


def create_backup(user_id):
    """
    Create a complete database backup for restore functionality

    Args:
        user_id: ID of the admin user creating the backup

    Returns:
        Dictionary with backup file path and metadata
    """
    user = User.query.get(user_id)
    if not user or not user.is_admin:
        raise ValueError("Only admin users can create backups")

    # Export all data from all tables
    backup_data = {
        "backup_info": {
            "created_by": user.username,
            "created_at": datetime.utcnow().isoformat(),
            "version": "1.0",
        },
        "users": [u.to_dict() for u in User.query.all()],
        "clients": [_client_to_dict(c) for c in Client.query.all()],
        "projects": [_project_to_dict(p) for p in Project.query.all()],
        "tasks": [_task_to_dict(t) for t in Task.query.all()],
        "time_entries": [_time_entry_to_dict(te) for te in TimeEntry.query.all()],
        "expenses": [_expense_to_dict(e) for e in Expense.query.all()],
        "expense_categories": [_expense_category_to_dict(ec) for ec in ExpenseCategory.query.all()],
        "mileage": [_mileage_to_dict(m) for m in Mileage.query.all()],
        "per_diems": [_per_diem_to_dict(pd) for pd in PerDiem.query.all()],
        "invoices": [_invoice_to_dict(i) for i in Invoice.query.all()],
        "comments": [_comment_to_dict(c) for c in Comment.query.all()],
        "focus_sessions": [_focus_session_to_dict(fs) for fs in FocusSession.query.all()],
        "recurring_blocks": [_recurring_block_to_dict(rb) for rb in RecurringBlock.query.all()],
        "saved_filters": [_saved_filter_to_dict(sf) for sf in SavedFilter.query.all()],
        "project_costs": [_project_cost_to_dict(pc) for pc in ProjectCost.query.all()],
        "weekly_goals": [_weekly_goal_to_dict(wg) for wg in WeeklyTimeGoal.query.all()],
        "calendar_events": [_calendar_event_to_dict(ce) for ce in CalendarEvent.query.all()],
    }

    # Create backup file
    backup_dir = os.path.join(current_app.config.get("UPLOAD_FOLDER", "/data/uploads"), "backups")
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"backup_{timestamp}.json"
    filepath = os.path.join(backup_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(backup_data, f, indent=2, ensure_ascii=False, default=str)

    file_size = os.path.getsize(filepath)
    record_count = sum(len(v) if isinstance(v, list) else 1 for v in backup_data.values())

    return {"filepath": filepath, "file_size": file_size, "record_count": record_count, "filename": filename}


# Helper functions to convert models to dictionaries


def _export_user_profile(user):
    """Export user profile data"""
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "theme_preference": user.theme_preference,
        "preferred_language": user.preferred_language,
        "timezone": user.timezone,
        "date_format": user.date_format,
        "time_format": user.time_format,
        "week_start_day": user.week_start_day,
    }


def _export_time_entries(user):
    """Export user time entries"""
    entries = TimeEntry.query.filter_by(user_id=user.id).all()
    return [_time_entry_to_dict(e) for e in entries]


def _export_user_projects(user):
    """Export projects user has worked on"""
    # Get unique projects from time entries
    project_ids = db.session.query(TimeEntry.project_id).filter_by(user_id=user.id).distinct().all()
    project_ids = [pid[0] for pid in project_ids]
    projects = Project.query.filter(Project.id.in_(project_ids)).all()
    return [_project_to_dict(p) for p in projects]


def _export_user_tasks(user):
    """Export tasks assigned to user"""
    tasks = Task.query.filter_by(assigned_to=user.id).all()
    return [_task_to_dict(t) for t in tasks]


def _export_user_expenses(user):
    """Export user expenses"""
    expenses = Expense.query.filter_by(user_id=user.id).all()
    return [_expense_to_dict(e) for e in expenses]


def _export_user_mileage(user):
    """Export user mileage records"""
    mileage = Mileage.query.filter_by(user_id=user.id).all()
    return [_mileage_to_dict(m) for m in mileage]


def _export_user_per_diems(user):
    """Export user per diem records"""
    per_diems = PerDiem.query.filter_by(user_id=user.id).all()
    return [_per_diem_to_dict(pd) for pd in per_diems]


def _export_user_invoices(user):
    """Export invoices created by user"""
    if not user.is_admin:
        return []
    invoices = Invoice.query.filter_by(created_by=user.id).all()
    return [_invoice_to_dict(i) for i in invoices]


def _export_user_comments(user):
    """Export comments by user"""
    comments = Comment.query.filter_by(user_id=user.id).all()
    return [_comment_to_dict(c) for c in comments]


def _export_user_focus_sessions(user):
    """Export user focus sessions"""
    sessions = FocusSession.query.filter_by(user_id=user.id).all()
    return [_focus_session_to_dict(fs) for fs in sessions]


def _export_user_saved_filters(user):
    """Export user saved filters"""
    filters = SavedFilter.query.filter_by(user_id=user.id).all()
    return [_saved_filter_to_dict(sf) for sf in filters]


def _export_user_project_costs(user):
    """Export project costs by user"""
    costs = ProjectCost.query.filter_by(user_id=user.id).all()
    return [_project_cost_to_dict(pc) for pc in costs]


def _export_user_weekly_goals(user):
    """Export user weekly goals"""
    goals = WeeklyTimeGoal.query.filter_by(user_id=user.id).all()
    return [_weekly_goal_to_dict(wg) for wg in goals]


def _export_user_activities(user):
    """Export user activities"""
    activities = Activity.query.filter_by(user_id=user.id).all()
    return [_activity_to_dict(a) for a in activities]


def _export_user_calendar_events(user):
    """Export user calendar events"""
    events = CalendarEvent.query.filter_by(user_id=user.id).all()
    return [_calendar_event_to_dict(ce) for ce in events]


# Model to dict converters


def _time_entry_to_dict(entry):
    """Convert time entry to dictionary"""
    return {
        "id": entry.id,
        "user_id": entry.user_id,
        "user": entry.user.username if entry.user else None,
        "project_id": entry.project_id,
        "project": entry.project.name if entry.project else None,
        "task_id": entry.task_id,
        "task": entry.task.name if entry.task else None,
        "start_time": entry.start_time.isoformat() if entry.start_time else None,
        "end_time": entry.end_time.isoformat() if entry.end_time else None,
        "duration_seconds": entry.duration_seconds,
        "duration_hours": entry.duration_hours,
        "notes": entry.notes,
        "tags": entry.tags,
        "source": entry.source,
        "billable": entry.billable,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
        "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
    }


def _project_to_dict(project):
    """Convert project to dictionary"""
    return {
        "id": project.id,
        "name": project.name,
        "client_id": project.client_id,
        "client": project.client,
        "description": project.description,
        "billable": project.billable,
        "hourly_rate": float(project.hourly_rate) if project.hourly_rate else None,
        "billing_ref": project.billing_ref,
        "code": project.code,
        "status": project.status,
        "estimated_hours": project.estimated_hours,
        "budget_amount": float(project.budget_amount) if project.budget_amount else None,
        "created_at": project.created_at.isoformat() if project.created_at else None,
    }


def _client_to_dict(client):
    """Convert client to dictionary"""
    return {
        "id": client.id,
        "name": client.name,
        "email": client.email,
        "phone": client.phone,
        "address": client.address,
        "created_at": client.created_at.isoformat() if client.created_at else None,
    }


def _task_to_dict(task):
    """Convert task to dictionary"""
    return {
        "id": task.id,
        "name": task.name,
        "description": task.description,
        "project_id": task.project_id,
        "project": task.project.name if task.project else None,
        "assigned_to": task.assigned_to,
        "status": task.status,
        "priority": task.priority,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


def _expense_to_dict(expense):
    """Convert expense to dictionary"""
    return {
        "id": expense.id,
        "user_id": expense.user_id,
        "project_id": expense.project_id,
        "category_id": expense.category_id,
        "amount": float(expense.amount) if expense.amount else None,
        "currency": expense.currency,
        "description": expense.description,
        "date": expense.date.isoformat() if expense.date else None,
        "billable": expense.billable,
        "created_at": expense.created_at.isoformat() if expense.created_at else None,
    }


def _expense_category_to_dict(category):
    """Convert expense category to dictionary"""
    return {
        "id": category.id,
        "name": category.name,
        "description": category.description,
    }


def _mileage_to_dict(mileage):
    """Convert mileage to dictionary"""
    return {
        "id": mileage.id,
        "user_id": mileage.user_id,
        "project_id": mileage.project_id,
        "distance": float(mileage.distance) if mileage.distance else None,
        "unit": mileage.unit,
        "purpose": mileage.purpose,
        "date": mileage.date.isoformat() if mileage.date else None,
        "created_at": mileage.created_at.isoformat() if mileage.created_at else None,
    }


def _per_diem_to_dict(per_diem):
    """Convert per diem to dictionary"""
    return {
        "id": per_diem.id,
        "user_id": per_diem.user_id,
        "project_id": per_diem.project_id,
        "date": per_diem.date.isoformat() if per_diem.date else None,
        "amount": float(per_diem.amount) if per_diem.amount else None,
        "description": per_diem.description,
        "created_at": per_diem.created_at.isoformat() if per_diem.created_at else None,
    }


def _invoice_to_dict(invoice):
    """Convert invoice to dictionary"""
    return {
        "id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "client_id": invoice.client_id,
        "project_id": invoice.project_id,
        "issue_date": invoice.issue_date.isoformat() if invoice.issue_date else None,
        "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
        "total_amount": float(invoice.total_amount) if invoice.total_amount else None,
        "status": invoice.status,
        "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
    }


def _comment_to_dict(comment):
    """Convert comment to dictionary"""
    return {
        "id": comment.id,
        "user_id": comment.user_id,
        "content": comment.content,
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
    }


def _focus_session_to_dict(session):
    """Convert focus session to dictionary"""
    return {
        "id": session.id,
        "user_id": session.user_id,
        "start_time": session.start_time.isoformat() if session.start_time else None,
        "end_time": session.end_time.isoformat() if session.end_time else None,
        "duration_minutes": session.duration_minutes,
        "created_at": session.created_at.isoformat() if session.created_at else None,
    }


def _recurring_block_to_dict(block):
    """Convert recurring block to dictionary"""
    return {
        "id": block.id,
        "user_id": block.user_id,
        "title": block.title,
        "description": block.description,
        "created_at": block.created_at.isoformat() if block.created_at else None,
    }


def _saved_filter_to_dict(filter_obj):
    """Convert saved filter to dictionary"""
    return {
        "id": filter_obj.id,
        "user_id": filter_obj.user_id,
        "name": filter_obj.name,
        "filter_data": filter_obj.filter_data,
        "created_at": filter_obj.created_at.isoformat() if filter_obj.created_at else None,
    }


def _project_cost_to_dict(cost):
    """Convert project cost to dictionary"""
    return {
        "id": cost.id,
        "project_id": cost.project_id,
        "user_id": cost.user_id,
        "amount": float(cost.amount) if cost.amount else None,
        "description": cost.description,
        "date": cost.date.isoformat() if cost.date else None,
        "billable": cost.billable,
        "created_at": cost.created_at.isoformat() if cost.created_at else None,
    }


def _weekly_goal_to_dict(goal):
    """Convert weekly goal to dictionary"""
    return {
        "id": goal.id,
        "user_id": goal.user_id,
        "week_start": goal.week_start.isoformat() if goal.week_start else None,
        "target_hours": float(goal.target_hours) if goal.target_hours else None,
        "created_at": goal.created_at.isoformat() if goal.created_at else None,
    }


def _activity_to_dict(activity):
    """Convert activity to dictionary"""
    return {
        "id": activity.id,
        "user_id": activity.user_id,
        "action": activity.action,
        "details": activity.details,
        "created_at": activity.created_at.isoformat() if activity.created_at else None,
    }


def _calendar_event_to_dict(event):
    """Convert calendar event to dictionary"""
    return {
        "id": event.id,
        "user_id": event.user_id,
        "title": event.title,
        "description": event.description,
        "start_time": event.start_time.isoformat() if event.start_time else None,
        "end_time": event.end_time.isoformat() if event.end_time else None,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


def _list_to_csv(data_list):
    """Convert list of dictionaries to CSV string"""
    if not data_list:
        return ""

    output = StringIO()
    if len(data_list) > 0:
        fieldnames = data_list[0].keys()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data_list)

    return output.getvalue()
