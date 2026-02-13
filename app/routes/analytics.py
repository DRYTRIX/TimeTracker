from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import User, Project, TimeEntry, Settings, Task, Payment, Invoice
from datetime import datetime, timedelta
from sqlalchemy import func, extract, case
import calendar
from app.utils.module_helpers import module_enabled

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/analytics")
@login_required
@module_enabled("analytics")
def analytics_dashboard():
    """Main analytics dashboard with charts"""
    # Check if user agent indicates mobile device
    user_agent = request.headers.get("User-Agent", "").lower()
    is_mobile = any(device in user_agent for device in ["mobile", "android", "iphone", "ipad"])

    # Check for legacy/simple dashboard query parameter
    use_legacy = request.args.get("legacy", "").lower() == "true"

    if is_mobile:
        return render_template("analytics/mobile_dashboard.html")
    elif use_legacy:
        return render_template("analytics/dashboard.html")
    else:
        return render_template("analytics/dashboard_improved.html")


@analytics_bp.route("/api/analytics/hours-by-day")
@login_required
@module_enabled("analytics")
def hours_by_day():
    """Get hours worked per day for the last 30 days"""
    try:
        days = int(request.args.get("days", 30))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid days parameter"}), 400

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    # Build query based on user permissions
    query = db.session.query(
        func.date(TimeEntry.start_time).label("date"), func.sum(TimeEntry.duration_seconds).label("total_seconds")
    ).filter(TimeEntry.end_time.isnot(None), TimeEntry.start_time >= start_date, TimeEntry.start_time <= end_date)

    if not current_user.is_admin:
        query = query.filter(TimeEntry.user_id == current_user.id)

    results = query.group_by(func.date(TimeEntry.start_time)).all()

    # Create date range and fill missing dates with 0
    date_data = {}
    current_date = start_date
    while current_date <= end_date:
        date_data[current_date.strftime("%Y-%m-%d")] = 0
        current_date += timedelta(days=1)

    # Fill in actual data
    for date_str, total_seconds in results:
        if date_str:
            # Handle both string and date object returns from different databases
            if isinstance(date_str, str):
                formatted_date = date_str
            elif hasattr(date_str, "strftime"):
                formatted_date = date_str.strftime("%Y-%m-%d")
            else:
                # Skip if we can't format the date
                continue
            if total_seconds is None:
                total_seconds = 0
            date_data[formatted_date] = round(total_seconds / 3600, 2)

    return jsonify(
        {
            "labels": list(date_data.keys()),
            "datasets": [
                {
                    "label": "Hours Worked",
                    "data": list(date_data.values()),
                    "borderColor": "#3b82f6",
                    "backgroundColor": "rgba(59, 130, 246, 0.1)",
                    "tension": 0.4,
                    "fill": True,
                }
            ],
        }
    )


@analytics_bp.route("/api/analytics/hours-by-project")
@login_required
@module_enabled("analytics")
def hours_by_project():
    """Get total hours per project"""
    days = int(request.args.get("days", 30))
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    query = (
        db.session.query(Project.name, func.sum(TimeEntry.duration_seconds).label("total_seconds"))
        .join(TimeEntry)
        .filter(
            TimeEntry.end_time.isnot(None),
            TimeEntry.start_time >= start_date,
            TimeEntry.start_time <= end_date,
            Project.status == "active",
        )
    )

    if not current_user.is_admin:
        query = query.filter(TimeEntry.user_id == current_user.id)

    results = query.group_by(Project.name).order_by(func.sum(TimeEntry.duration_seconds).desc()).limit(10).all()

    labels = [project for project, _ in results]
    data = [round(seconds / 3600, 2) for _, seconds in results]

    # Generate colors for each project
    colors = [
        "#3b82f6",
        "#10b981",
        "#f59e0b",
        "#ef4444",
        "#8b5cf6",
        "#06b6d4",
        "#84cc16",
        "#f97316",
        "#ec4899",
        "#6366f1",
    ]

    return jsonify(
        {
            "labels": labels,
            "datasets": [
                {
                    "label": "Hours",
                    "data": data,
                    "backgroundColor": colors[: len(labels)],
                    "borderColor": colors[: len(labels)],
                    "borderWidth": 1,
                }
            ],
        }
    )


@analytics_bp.route("/api/analytics/hours-by-user")
@login_required
@module_enabled("analytics")
def hours_by_user():
    """Get total hours per user (admin only)"""
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    days = int(request.args.get("days", 30))
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    results = (
        db.session.query(User.username, func.sum(TimeEntry.duration_seconds).label("total_seconds"))
        .join(TimeEntry)
        .filter(
            TimeEntry.end_time.isnot(None),
            TimeEntry.start_time >= start_date,
            TimeEntry.start_time <= end_date,
            User.is_active == True,
        )
        .group_by(User.username)
        .order_by(func.sum(TimeEntry.duration_seconds).desc())
        .all()
    )

    labels = [username for username, _ in results]
    data = [round(seconds / 3600, 2) for _, seconds in results]

    return jsonify(
        {
            "labels": labels,
            "datasets": [
                {
                    "label": "Hours",
                    "data": data,
                    "backgroundColor": "rgba(59, 130, 246, 0.8)",
                    "borderColor": "#3b82f6",
                    "borderWidth": 2,
                }
            ],
        }
    )


@analytics_bp.route("/api/analytics/hours-by-hour")
@login_required
@module_enabled("analytics")
def hours_by_hour():
    """Get hours worked by hour of day (24-hour format)"""
    days = int(request.args.get("days", 30))
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    query = db.session.query(
        extract("hour", TimeEntry.start_time).label("hour"), func.sum(TimeEntry.duration_seconds).label("total_seconds")
    ).filter(TimeEntry.end_time.isnot(None), TimeEntry.start_time >= start_date, TimeEntry.start_time <= end_date)

    if not current_user.is_admin:
        query = query.filter(TimeEntry.user_id == current_user.id)

    results = (
        query.group_by(extract("hour", TimeEntry.start_time)).order_by(extract("hour", TimeEntry.start_time)).all()
    )

    # Create 24-hour array
    hours_data = [0] * 24
    for hour, total_seconds in results:
        if total_seconds is None:
            total_seconds = 0
        hours_data[int(hour)] = round(total_seconds / 3600, 2)

    labels = [f"{hour:02d}:00" for hour in range(24)]

    return jsonify(
        {
            "labels": labels,
            "datasets": [
                {
                    "label": "Hours Worked",
                    "data": hours_data,
                    "backgroundColor": "rgba(16, 185, 129, 0.8)",
                    "borderColor": "#10b981",
                    "borderWidth": 2,
                    "tension": 0.4,
                }
            ],
        }
    )


@analytics_bp.route("/api/analytics/billable-vs-nonbillable")
@login_required
@module_enabled("analytics")
def billable_vs_nonbillable():
    """Get billable vs non-billable hours breakdown"""
    days = int(request.args.get("days", 30))
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    query = db.session.query(TimeEntry.billable, func.sum(TimeEntry.duration_seconds).label("total_seconds")).filter(
        TimeEntry.end_time.isnot(None), TimeEntry.start_time >= start_date, TimeEntry.start_time <= end_date
    )

    if not current_user.is_admin:
        query = query.filter(TimeEntry.user_id == current_user.id)

    results = query.group_by(TimeEntry.billable).all()

    billable_hours = 0
    nonbillable_hours = 0

    for billable, total_seconds in results:
        if total_seconds is None:
            total_seconds = 0
        hours = round(total_seconds / 3600, 2)
        if billable:
            billable_hours = hours
        else:
            nonbillable_hours = hours

    return jsonify(
        {
            "labels": ["Billable", "Non-Billable"],
            "datasets": [
                {
                    "label": "Hours",
                    "data": [billable_hours, nonbillable_hours],
                    "backgroundColor": ["#10b981", "#6b7280"],
                    "borderColor": ["#059669", "#4b5563"],
                    "borderWidth": 2,
                }
            ],
        }
    )


@analytics_bp.route("/api/analytics/weekly-trends")
@login_required
@module_enabled("analytics")
def weekly_trends():
    """Get weekly trends over the last 12 weeks"""
    try:
        weeks = int(request.args.get("weeks", 12))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid weeks parameter"}), 400

    end_date = datetime.now().date()
    start_date = end_date - timedelta(weeks=weeks)

    # Get all time entries and group by week in Python (database-agnostic)
    query = db.session.query(TimeEntry.start_time, TimeEntry.duration_seconds).filter(
        TimeEntry.end_time.isnot(None), TimeEntry.start_time >= start_date, TimeEntry.start_time <= end_date
    )

    if not current_user.is_admin:
        query = query.filter(TimeEntry.user_id == current_user.id)

    results = query.all()

    # Group by week in Python
    from collections import defaultdict

    week_data = defaultdict(float)

    for start_time, duration_seconds in results:
        # Get the start of the week (Monday) for this entry
        if isinstance(start_time, str):
            try:
                entry_date = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S").date()
            except ValueError:
                # Try alternative format if the first one fails
                try:
                    entry_date = datetime.strptime(start_time, "%Y-%m-%d").date()
                except ValueError:
                    # Skip invalid date strings
                    continue
        elif isinstance(start_time, datetime):
            entry_date = start_time.date()
        elif isinstance(start_time, type(end_date)):  # date object
            entry_date = start_time
        else:
            # Skip if we can't determine the date
            continue

        # Ensure entry_date is a date object before calculating weekday
        if not isinstance(entry_date, type(end_date)):
            continue

        # Calculate Monday of that week
        week_start = entry_date - timedelta(days=entry_date.weekday())
        week_data[week_start] += duration_seconds or 0

    # Sort by week and format output
    labels = []
    data = []

    for week_start_key in sorted(week_data.keys()):
        # Ensure week_start is a date object before calling strftime
        if isinstance(week_start_key, str):
            # If it's a string, try to parse it
            try:
                week_start_date = datetime.strptime(week_start_key, "%Y-%m-%d").date()
            except (ValueError, AttributeError):
                continue
        elif isinstance(week_start_key, type(end_date)):
            week_start_date = week_start_key
        else:
            # Skip if it's not a date object or string
            continue

        labels.append(week_start_date.strftime("%b %d"))
        data.append(round(week_data[week_start_key] / 3600, 2))

    return jsonify(
        {
            "labels": labels,
            "datasets": [
                {
                    "label": "Weekly Hours",
                    "data": data,
                    "borderColor": "#8b5cf6",
                    "backgroundColor": "rgba(139, 92, 246, 0.1)",
                    "tension": 0.4,
                    "fill": True,
                    "pointBackgroundColor": "#8b5cf6",
                    "pointBorderColor": "#ffffff",
                    "pointBorderWidth": 2,
                }
            ],
        }
    )


@analytics_bp.route("/api/analytics/overtime")
@login_required
@module_enabled("analytics")
def overtime_analytics():
    """Get overtime statistics for the current user or all users (if admin)"""
    try:
        days = int(request.args.get("days", 30))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid days parameter"}), 400

    from app.utils.overtime import calculate_period_overtime, get_daily_breakdown

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    # If admin, show all users; otherwise show current user only
    if current_user.is_admin:
        users = User.query.filter_by(is_active=True).all()
    else:
        users = [current_user]

    # Calculate overtime for each user
    user_overtime_data = []
    total_overtime = 0
    total_regular = 0

    total_undertime = 0
    total_days_under = 0
    for user in users:
        overtime_info = calculate_period_overtime(user, start_date, end_date)
        if overtime_info["total_hours"] > 0:  # Only include users with tracked time
            user_overtime_data.append(
                {
                    "username": user.display_name,
                    "regular_hours": overtime_info["regular_hours"],
                    "overtime_hours": overtime_info["overtime_hours"],
                    "undertime_hours": overtime_info.get("undertime_hours", 0),
                    "days_under": overtime_info.get("days_under", 0),
                    "total_hours": overtime_info["total_hours"],
                    "days_with_overtime": overtime_info["days_with_overtime"],
                }
            )
            total_overtime += overtime_info["overtime_hours"]
            total_regular += overtime_info["regular_hours"]
            total_undertime += overtime_info.get("undertime_hours", 0)
            total_days_under += overtime_info.get("days_under", 0)

    # Get daily breakdown for chart
    if not current_user.is_admin:
        daily_data = get_daily_breakdown(current_user, start_date, end_date)
    else:
        # For admin, show aggregated daily data
        daily_data = []

    return jsonify(
        {
            "users": user_overtime_data,
            "summary": {
                "total_regular_hours": round(total_regular, 2),
                "total_overtime_hours": round(total_overtime, 2),
                "total_undertime_hours": round(total_undertime, 2),
                "days_under": total_days_under,
                "total_hours": round(total_regular + total_overtime, 2),
                "overtime_percentage": round(
                    (
                        (total_overtime / (total_regular + total_overtime) * 100)
                        if (total_regular + total_overtime) > 0
                        else 0
                    ),
                    1,
                ),
            },
            "daily_breakdown": [
                {
                    "date": day["date_str"],
                    "regular_hours": day["regular_hours"],
                    "overtime_hours": day["overtime_hours"],
                    "undertime_hours": day.get("undertime_hours", 0),
                    "is_undertime": day.get("is_undertime", False),
                    "total_hours": day["total_hours"],
                }
                for day in daily_data
            ],
        }
    )


@analytics_bp.route("/api/analytics/project-efficiency")
@login_required
@module_enabled("analytics")
def project_efficiency():
    """Get project efficiency metrics (hours vs billable amount)"""
    days = int(request.args.get("days", 30))
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    query = (
        db.session.query(Project.name, func.sum(TimeEntry.duration_seconds).label("total_seconds"), Project.hourly_rate)
        .join(TimeEntry)
        .filter(
            TimeEntry.end_time.isnot(None),
            TimeEntry.start_time >= start_date,
            TimeEntry.start_time <= end_date,
            Project.status == "active",
            Project.billable == True,
            Project.hourly_rate.isnot(None),
        )
    )

    if not current_user.is_admin:
        query = query.filter(TimeEntry.user_id == current_user.id)

    results = (
        query.group_by(Project.name, Project.hourly_rate)
        .order_by(func.sum(TimeEntry.duration_seconds).desc())
        .limit(8)
        .all()
    )

    labels = [project for project, _, _ in results]
    hours_data = [round(seconds / 3600, 2) for _, seconds, _ in results]
    revenue_data = [round((seconds / 3600) * float(rate), 2) for _, seconds, rate in results]

    return jsonify(
        {
            "labels": labels,
            "datasets": [
                {
                    "label": "Hours",
                    "data": hours_data,
                    "backgroundColor": "rgba(59, 130, 246, 0.8)",
                    "borderColor": "#3b82f6",
                    "borderWidth": 2,
                    "yAxisID": "y",
                },
                {
                    "label": "Revenue",
                    "data": revenue_data,
                    "backgroundColor": "rgba(16, 185, 129, 0.8)",
                    "borderColor": "#10b981",
                    "borderWidth": 2,
                    "yAxisID": "y1",
                },
            ],
        }
    )


@analytics_bp.route("/api/analytics/today-by-task")
@login_required
@module_enabled("analytics")
def today_by_task():
    """Get today's total hours grouped by task (includes project-level entries without task).

    Optional query params:
    - date: YYYY-MM-DD (defaults to today)
    - user_id: admin-only override to view a specific user's data
    """
    # Parse target date
    date_str = request.args.get("date")
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Invalid date format, expected YYYY-MM-DD"}), 400
    else:
        target_date = datetime.now().date()

    # Base query
    query = (
        db.session.query(
            TimeEntry.task_id,
            Task.name.label("task_name"),
            TimeEntry.project_id,
            Project.name.label("project_name"),
            func.sum(TimeEntry.duration_seconds).label("total_seconds"),
        )
        .join(Project, Project.id == TimeEntry.project_id)
        .outerjoin(Task, Task.id == TimeEntry.task_id)
        .filter(TimeEntry.end_time.isnot(None), func.date(TimeEntry.start_time) == target_date)
    )

    # Scope to current user unless admin (with optional override)
    if not current_user.is_admin:
        query = query.filter(TimeEntry.user_id == current_user.id)
    else:
        user_id = request.args.get("user_id", type=int)
        if user_id:
            query = query.filter(TimeEntry.user_id == user_id)

    results = (
        query.group_by(TimeEntry.task_id, Task.name, TimeEntry.project_id, Project.name)
        .order_by(func.sum(TimeEntry.duration_seconds).desc())
        .all()
    )

    rows = []
    for task_id, task_name, project_id, project_name, total_seconds in results:
        total_seconds = int(total_seconds or 0)
        total_hours = round(total_seconds / 3600, 2)
        label = f"{project_name} • {task_name}" if task_name else f"{project_name} • No task"
        rows.append(
            {
                "task_id": task_id,
                "task_name": task_name,
                "project_id": project_id,
                "project_name": project_name,
                "total_seconds": total_seconds,
                "total_hours": total_hours,
                "label": label,
            }
        )

    return jsonify({"date": target_date.strftime("%Y-%m-%d"), "rows": rows})


@analytics_bp.route("/api/analytics/summary-with-comparison")
@login_required
@module_enabled("analytics")
def summary_with_comparison():
    """Get summary metrics with comparison to previous period"""
    days = int(request.args.get("days", 30))
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    # Previous period dates
    prev_end_date = start_date - timedelta(days=1)
    prev_start_date = prev_end_date - timedelta(days=days)

    # Current period query
    current_query = db.session.query(
        func.sum(TimeEntry.duration_seconds).label("total_seconds"),
        func.count(TimeEntry.id).label("total_entries"),
        func.sum(case((TimeEntry.billable == True, TimeEntry.duration_seconds), else_=0)).label("billable_seconds"),
    ).filter(TimeEntry.end_time.isnot(None), TimeEntry.start_time >= start_date, TimeEntry.start_time <= end_date)

    # Previous period query
    prev_query = db.session.query(
        func.sum(TimeEntry.duration_seconds).label("total_seconds"),
        func.count(TimeEntry.id).label("total_entries"),
        func.sum(case((TimeEntry.billable == True, TimeEntry.duration_seconds), else_=0)).label("billable_seconds"),
    ).filter(
        TimeEntry.end_time.isnot(None), TimeEntry.start_time >= prev_start_date, TimeEntry.start_time <= prev_end_date
    )

    if not current_user.is_admin:
        current_query = current_query.filter(TimeEntry.user_id == current_user.id)
        prev_query = prev_query.filter(TimeEntry.user_id == current_user.id)

    current_result = current_query.first()
    prev_result = prev_query.first()

    current_hours = round((current_result.total_seconds or 0) / 3600, 1)
    prev_hours = round((prev_result.total_seconds or 0) / 3600, 1)
    hours_change = ((current_hours - prev_hours) / prev_hours * 100) if prev_hours > 0 else 0

    current_billable = round((current_result.billable_seconds or 0) / 3600, 1)
    prev_billable = round((prev_result.billable_seconds or 0) / 3600, 1)
    billable_change = ((current_billable - prev_billable) / prev_billable * 100) if prev_billable > 0 else 0

    current_entries = current_result.total_entries or 0
    prev_entries = prev_result.total_entries or 0
    entries_change = ((current_entries - prev_entries) / prev_entries * 100) if prev_entries > 0 else 0

    # Get active projects count
    active_projects = Project.query.filter_by(status="active").count()

    # Calculate average daily hours
    avg_daily_hours = round(current_hours / days, 1) if days > 0 else 0

    # Calculate billable percentage
    billable_percentage = round((current_billable / current_hours * 100), 1) if current_hours > 0 else 0

    # Get payment data for the period
    payment_query = db.session.query(
        func.sum(Payment.amount).label("total_payments"), func.count(Payment.id).label("payment_count")
    ).filter(Payment.payment_date >= start_date, Payment.payment_date <= end_date, Payment.status == "completed")

    if not current_user.is_admin:
        payment_query = (
            payment_query.join(Invoice).join(Project).join(TimeEntry).filter(TimeEntry.user_id == current_user.id)
        )

    payment_result = payment_query.first()
    total_payments = float(payment_result.total_payments or 0)
    payment_count = payment_result.payment_count or 0

    return jsonify(
        {
            "total_hours": current_hours,
            "total_hours_change": round(hours_change, 1),
            "billable_hours": current_billable,
            "billable_hours_change": round(billable_change, 1),
            "total_entries": current_entries,
            "entries_change": round(entries_change, 1),
            "active_projects": active_projects,
            "avg_daily_hours": avg_daily_hours,
            "billable_percentage": billable_percentage,
            "total_payments": round(total_payments, 2),
            "payment_count": payment_count,
        }
    )


@analytics_bp.route("/api/analytics/task-completion")
@login_required
@module_enabled("analytics")
def task_completion():
    """Get task completion analytics"""
    days = int(request.args.get("days", 30))
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    # Get tasks completed in period
    completed_query = db.session.query(func.count(Task.id).label("count")).filter(
        Task.status == "done", Task.completed_at >= start_date, Task.completed_at <= end_date
    )

    if not current_user.is_admin:
        completed_query = completed_query.filter(Task.assigned_to == current_user.id)

    completed_count = completed_query.scalar() or 0

    # Get tasks by status
    status_query = db.session.query(Task.status, func.count(Task.id).label("count")).filter(
        Task.created_at >= start_date
    )

    if not current_user.is_admin:
        status_query = status_query.filter(Task.assigned_to == current_user.id)

    status_results = status_query.group_by(Task.status).all()

    status_data = {"todo": 0, "in_progress": 0, "review": 0, "done": 0, "cancelled": 0}

    for status, count in status_results:
        if status in status_data:
            status_data[status] = count

    # Get task completion rate by project
    project_query = (
        db.session.query(
            Project.name,
            func.count(Task.id).label("total_tasks"),
            func.sum(case((Task.status == "done", 1), else_=0)).label("completed_tasks"),
        )
        .join(Task)
        .filter(Task.created_at >= start_date, Project.status == "active")
    )

    if not current_user.is_admin:
        project_query = project_query.filter(Task.assigned_to == current_user.id)

    project_results = project_query.group_by(Project.name).order_by(func.count(Task.id).desc()).limit(10).all()

    project_labels = []
    project_completion_rates = []

    for project_name, total, completed in project_results:
        project_labels.append(project_name)
        rate = (completed / total * 100) if total > 0 else 0
        project_completion_rates.append(round(rate, 1))

    return jsonify(
        {
            "completed_count": completed_count,
            "status_breakdown": status_data,
            "project_labels": project_labels,
            "project_completion_rates": project_completion_rates,
        }
    )


@analytics_bp.route("/api/analytics/revenue-metrics")
@login_required
@module_enabled("analytics")
def revenue_metrics():
    """Get revenue and financial metrics"""
    days = int(request.args.get("days", 30))
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    settings = Settings.get_settings()
    currency = settings.currency

    # Get billable hours with rates
    query = (
        db.session.query(func.sum(TimeEntry.duration_seconds).label("total_seconds"), Project.hourly_rate)
        .join(Project)
        .filter(
            TimeEntry.end_time.isnot(None),
            TimeEntry.start_time >= start_date,
            TimeEntry.start_time <= end_date,
            TimeEntry.billable == True,
            Project.billable == True,
            Project.hourly_rate.isnot(None),
        )
    )

    if not current_user.is_admin:
        query = query.filter(TimeEntry.user_id == current_user.id)

    results = query.group_by(Project.hourly_rate).all()

    total_revenue = 0
    for seconds, rate in results:
        if seconds and rate:
            hours = seconds / 3600
            total_revenue += hours * float(rate)

    # Get billable hours
    billable_query = db.session.query(func.sum(TimeEntry.duration_seconds).label("total_seconds")).filter(
        TimeEntry.end_time.isnot(None),
        TimeEntry.start_time >= start_date,
        TimeEntry.start_time <= end_date,
        TimeEntry.billable == True,
    )

    if not current_user.is_admin:
        billable_query = billable_query.filter(TimeEntry.user_id == current_user.id)

    billable_seconds = billable_query.scalar() or 0
    billable_hours = round(billable_seconds / 3600, 1)

    # Calculate average hourly rate
    avg_hourly_rate = (total_revenue / billable_hours) if billable_hours > 0 else 0

    # Get revenue by project
    project_query = (
        db.session.query(Project.name, func.sum(TimeEntry.duration_seconds).label("total_seconds"), Project.hourly_rate)
        .join(TimeEntry)
        .filter(
            TimeEntry.end_time.isnot(None),
            TimeEntry.start_time >= start_date,
            TimeEntry.start_time <= end_date,
            TimeEntry.billable == True,
            Project.billable == True,
            Project.hourly_rate.isnot(None),
        )
    )

    if not current_user.is_admin:
        project_query = project_query.filter(TimeEntry.user_id == current_user.id)

    project_results = (
        project_query.group_by(Project.name, Project.hourly_rate)
        .order_by(func.sum(TimeEntry.duration_seconds).desc())
        .limit(8)
        .all()
    )

    project_labels = []
    project_revenue = []

    for project_name, seconds, rate in project_results:
        project_labels.append(project_name)
        if seconds and rate:
            revenue = (seconds / 3600) * float(rate)
            project_revenue.append(round(revenue, 2))
        else:
            project_revenue.append(0)

    return jsonify(
        {
            "total_revenue": round(total_revenue, 2),
            "billable_hours": billable_hours,
            "avg_hourly_rate": round(avg_hourly_rate, 2),
            "currency": currency,
            "project_labels": project_labels,
            "project_revenue": project_revenue,
        }
    )


@analytics_bp.route("/api/analytics/insights")
@login_required
@module_enabled("analytics")
def insights():
    """Generate insights and recommendations based on analytics data"""
    days = int(request.args.get("days", 30))
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    insights_list = []

    # Analyze time entries
    query = db.session.query(
        func.sum(TimeEntry.duration_seconds).label("total_seconds"),
        func.avg(TimeEntry.duration_seconds).label("avg_seconds"),
        func.count(TimeEntry.id).label("total_entries"),
        func.sum(case((TimeEntry.billable == True, TimeEntry.duration_seconds), else_=0)).label("billable_seconds"),
    ).filter(TimeEntry.end_time.isnot(None), TimeEntry.start_time >= start_date, TimeEntry.start_time <= end_date)

    if not current_user.is_admin:
        query = query.filter(TimeEntry.user_id == current_user.id)

    result = query.first()

    total_hours = (result.total_seconds or 0) / 3600
    billable_hours = (result.billable_seconds or 0) / 3600
    avg_entry_hours = (result.avg_seconds or 0) / 3600

    # Insight 1: Billable ratio
    if total_hours > 0:
        billable_ratio = (billable_hours / total_hours) * 100
        if billable_ratio < 60:
            insights_list.append(
                {
                    "type": "warning",
                    "icon": "fas fa-exclamation-triangle",
                    "title": "Low Billable Ratio",
                    "message": f"Only {billable_ratio:.1f}% of your time is billable. Consider focusing on billable projects.",
                }
            )
        elif billable_ratio > 85:
            insights_list.append(
                {
                    "type": "success",
                    "icon": "fas fa-trophy",
                    "title": "Excellent Billable Ratio",
                    "message": f"You have {billable_ratio:.1f}% billable time. Great work!",
                }
            )

    # Insight 2: Average daily hours
    avg_daily = total_hours / days if days > 0 else 0
    if avg_daily < 4:
        insights_list.append(
            {
                "type": "info",
                "icon": "fas fa-chart-line",
                "title": "Low Activity",
                "message": f"Average of {avg_daily:.1f}h per day. Consider tracking more consistently.",
            }
        )
    elif avg_daily > 10:
        insights_list.append(
            {
                "type": "warning",
                "icon": "fas fa-battery-empty",
                "title": "High Workload",
                "message": f"Averaging {avg_daily:.1f}h per day. Remember to take breaks!",
            }
        )

    # Insight 3: Project diversity
    project_count = db.session.query(func.count(func.distinct(TimeEntry.project_id))).filter(
        TimeEntry.end_time.isnot(None), TimeEntry.start_time >= start_date, TimeEntry.start_time <= end_date
    )

    if not current_user.is_admin:
        project_count = project_count.filter(TimeEntry.user_id == current_user.id)

    num_projects = project_count.scalar() or 0

    if num_projects > 8:
        insights_list.append(
            {
                "type": "info",
                "icon": "fas fa-tasks",
                "title": "Multiple Projects",
                "message": f"Working on {num_projects} projects. Consider consolidating focus.",
            }
        )

    # Insight 4: Weekend work (if any)
    weekend_query = db.session.query(func.sum(TimeEntry.duration_seconds).label("weekend_seconds")).filter(
        TimeEntry.end_time.isnot(None),
        TimeEntry.start_time >= start_date,
        TimeEntry.start_time <= end_date,
        extract("dow", TimeEntry.start_time).in_([0, 6]),  # Sunday=0, Saturday=6
    )

    if not current_user.is_admin:
        weekend_query = weekend_query.filter(TimeEntry.user_id == current_user.id)

    weekend_seconds = weekend_query.scalar() or 0
    weekend_hours = weekend_seconds / 3600

    if weekend_hours > 5:
        weekend_percent = (weekend_hours / total_hours * 100) if total_hours > 0 else 0
        insights_list.append(
            {
                "type": "warning",
                "icon": "fas fa-calendar-times",
                "title": "Weekend Work",
                "message": f"{weekend_percent:.0f}% of work done on weekends ({weekend_hours:.1f}h). Consider work-life balance.",
            }
        )

    return jsonify({"insights": insights_list})


@analytics_bp.route("/api/analytics/payments-over-time")
@login_required
@module_enabled("analytics")
def payments_over_time():
    """Get payments over time"""
    days = int(request.args.get("days", 30))
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    # Build query
    query = db.session.query(
        func.date(Payment.payment_date).label("date"),
        func.sum(Payment.amount).label("total_amount"),
        func.count(Payment.id).label("payment_count"),
    ).filter(Payment.payment_date >= start_date, Payment.payment_date <= end_date)

    if not current_user.is_admin:
        query = (
            query.join(Invoice).join(Project).join(TimeEntry).filter(TimeEntry.user_id == current_user.id).distinct()
        )

    results = query.group_by(func.date(Payment.payment_date)).all()

    # Create date range and fill missing dates with 0
    date_data = {}
    current_date = start_date
    while current_date <= end_date:
        date_data[current_date.strftime("%Y-%m-%d")] = 0
        current_date += timedelta(days=1)

    # Fill in actual data
    for date_obj, total_amount, _ in results:
        if date_obj:
            if isinstance(date_obj, str):
                formatted_date = date_obj
            elif hasattr(date_obj, "strftime"):
                formatted_date = date_obj.strftime("%Y-%m-%d")
            else:
                # Skip if we can't format the date
                continue
            date_data[formatted_date] = float(total_amount or 0)

    return jsonify(
        {
            "labels": list(date_data.keys()),
            "datasets": [
                {
                    "label": "Payments Received",
                    "data": list(date_data.values()),
                    "borderColor": "#10b981",
                    "backgroundColor": "rgba(16, 185, 129, 0.1)",
                    "tension": 0.4,
                    "fill": True,
                }
            ],
        }
    )


@analytics_bp.route("/api/analytics/payments-by-status")
@login_required
@module_enabled("analytics")
def payments_by_status():
    """Get payment breakdown by status"""
    days = int(request.args.get("days", 30))
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    query = db.session.query(
        Payment.status, func.count(Payment.id).label("count"), func.sum(Payment.amount).label("total_amount")
    ).filter(Payment.payment_date >= start_date, Payment.payment_date <= end_date)

    if not current_user.is_admin:
        query = (
            query.join(Invoice).join(Project).join(TimeEntry).filter(TimeEntry.user_id == current_user.id).distinct()
        )

    results = query.group_by(Payment.status).all()

    labels = []
    counts = []
    amounts = []
    colors = {"completed": "#10b981", "pending": "#f59e0b", "failed": "#ef4444", "refunded": "#6b7280"}
    background_colors = []

    for status, count, amount in results:
        labels.append(status.title() if status else "Unknown")
        counts.append(count)
        amounts.append(float(amount or 0))
        background_colors.append(colors.get(status, "#3b82f6"))

    return jsonify(
        {
            "labels": labels,
            "count_dataset": {"label": "Payment Count", "data": counts, "backgroundColor": background_colors},
            "amount_dataset": {"label": "Total Amount", "data": amounts, "backgroundColor": background_colors},
        }
    )


@analytics_bp.route("/api/analytics/payments-by-method")
@login_required
@module_enabled("analytics")
def payments_by_method():
    """Get payment breakdown by payment method"""
    days = int(request.args.get("days", 30))
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    query = db.session.query(
        Payment.method, func.count(Payment.id).label("count"), func.sum(Payment.amount).label("total_amount")
    ).filter(Payment.payment_date >= start_date, Payment.payment_date <= end_date, Payment.method.isnot(None))

    if not current_user.is_admin:
        query = (
            query.join(Invoice).join(Project).join(TimeEntry).filter(TimeEntry.user_id == current_user.id).distinct()
        )

    results = query.group_by(Payment.method).order_by(func.sum(Payment.amount).desc()).all()

    labels = []
    amounts = []
    colors = [
        "#3b82f6",
        "#10b981",
        "#f59e0b",
        "#ef4444",
        "#8b5cf6",
        "#06b6d4",
        "#84cc16",
        "#f97316",
        "#ec4899",
        "#6366f1",
    ]

    for idx, (method, _, amount) in enumerate(results):
        labels.append(method.replace("_", " ").title() if method else "Other")
        amounts.append(float(amount or 0))

    return jsonify(
        {
            "labels": labels,
            "datasets": [
                {"label": "Amount", "data": amounts, "backgroundColor": colors[: len(labels)], "borderWidth": 2}
            ],
        }
    )


@analytics_bp.route("/api/analytics/payment-summary")
@login_required
@module_enabled("analytics")
def payment_summary():
    """Get payment summary statistics"""
    days = int(request.args.get("days", 30))
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    # Previous period
    prev_end_date = start_date - timedelta(days=1)
    prev_start_date = prev_end_date - timedelta(days=days)

    # Current period query
    current_query = db.session.query(
        func.sum(Payment.amount).label("total_amount"),
        func.count(Payment.id).label("payment_count"),
        func.sum(Payment.gateway_fee).label("total_fees"),
        func.sum(Payment.net_amount).label("total_net"),
    ).filter(Payment.payment_date >= start_date, Payment.payment_date <= end_date)

    # Previous period query
    prev_query = db.session.query(
        func.sum(Payment.amount).label("total_amount"), func.count(Payment.id).label("payment_count")
    ).filter(Payment.payment_date >= prev_start_date, Payment.payment_date <= prev_end_date)

    if not current_user.is_admin:
        current_query = (
            current_query.join(Invoice).join(Project).join(TimeEntry).filter(TimeEntry.user_id == current_user.id)
        )
        prev_query = prev_query.join(Invoice).join(Project).join(TimeEntry).filter(TimeEntry.user_id == current_user.id)

    current_result = current_query.first()
    prev_result = prev_query.first()

    current_amount = float(current_result.total_amount or 0)
    prev_amount = float(prev_result.total_amount or 0)
    amount_change = ((current_amount - prev_amount) / prev_amount * 100) if prev_amount > 0 else 0

    current_count = current_result.payment_count or 0
    prev_count = prev_result.payment_count or 0
    count_change = ((current_count - prev_count) / prev_count * 100) if prev_count > 0 else 0

    total_fees = float(current_result.total_fees or 0)
    total_net = float(current_result.total_net or 0)

    # Get completed vs pending
    status_query = db.session.query(Payment.status, func.sum(Payment.amount).label("amount")).filter(
        Payment.payment_date >= start_date, Payment.payment_date <= end_date
    )

    if not current_user.is_admin:
        status_query = (
            status_query.join(Invoice).join(Project).join(TimeEntry).filter(TimeEntry.user_id == current_user.id)
        )

    status_results = status_query.group_by(Payment.status).all()

    completed_amount = 0
    pending_amount = 0

    for status, amount in status_results:
        if status == "completed":
            completed_amount = float(amount or 0)
        elif status == "pending":
            pending_amount = float(amount or 0)

    return jsonify(
        {
            "total_amount": round(current_amount, 2),
            "amount_change": round(amount_change, 1),
            "payment_count": current_count,
            "count_change": round(count_change, 1),
            "total_fees": round(total_fees, 2),
            "total_net": round(total_net, 2),
            "completed_amount": round(completed_amount, 2),
            "pending_amount": round(pending_amount, 2),
            "avg_payment": round(current_amount / current_count, 2) if current_count > 0 else 0,
        }
    )


@analytics_bp.route("/api/analytics/revenue-vs-payments")
@login_required
@module_enabled("analytics")
def revenue_vs_payments():
    """Compare potential revenue (from time tracking) with actual payments"""
    days = int(request.args.get("days", 30))
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    settings = Settings.get_settings()
    currency = settings.currency

    # Get billable revenue (potential)
    revenue_query = (
        db.session.query(func.sum(TimeEntry.duration_seconds).label("total_seconds"), Project.hourly_rate)
        .join(Project)
        .filter(
            TimeEntry.end_time.isnot(None),
            TimeEntry.start_time >= start_date,
            TimeEntry.start_time <= end_date,
            TimeEntry.billable == True,
            Project.billable == True,
            Project.hourly_rate.isnot(None),
        )
    )

    if not current_user.is_admin:
        revenue_query = revenue_query.filter(TimeEntry.user_id == current_user.id)

    revenue_results = revenue_query.group_by(Project.hourly_rate).all()

    potential_revenue = 0
    for seconds, rate in revenue_results:
        if seconds and rate:
            hours = seconds / 3600
            potential_revenue += hours * float(rate)

    # Get actual payments
    payment_query = db.session.query(func.sum(Payment.amount).label("total_amount")).filter(
        Payment.payment_date >= start_date, Payment.payment_date <= end_date, Payment.status == "completed"
    )

    if not current_user.is_admin:
        payment_query = (
            payment_query.join(Invoice).join(Project).join(TimeEntry).filter(TimeEntry.user_id == current_user.id)
        )

    actual_payments = payment_query.scalar() or 0
    actual_payments = float(actual_payments)

    collection_rate = (actual_payments / potential_revenue * 100) if potential_revenue > 0 else 0
    outstanding = potential_revenue - actual_payments

    return jsonify(
        {
            "potential_revenue": round(potential_revenue, 2),
            "actual_payments": round(actual_payments, 2),
            "outstanding": round(outstanding, 2),
            "collection_rate": round(collection_rate, 1),
            "currency": currency,
            "labels": ["Collected", "Outstanding"],
            "data": [round(actual_payments, 2), round(outstanding, 2) if outstanding > 0 else 0],
        }
    )
