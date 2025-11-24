from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_login import login_required, current_user
from flask_babel import _
from app import db, log_event, track_event
from app.models import User, Project, TimeEntry, Settings, Task, ProjectCost, Client, Payment, Invoice
from datetime import datetime, timedelta
from sqlalchemy import or_, func
import csv
import io
import pytz
import time
from app.utils.excel_export import create_time_entries_excel, create_project_report_excel
from app.utils.posthog_monitoring import (
    track_error,
    track_export_performance,
    track_validation_error
)

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/reports')
@login_required
def reports():
    """Main reports page - REFACTORED to use service layer with optimized queries"""
    from app.services import ReportingService
    
    # Use service layer to get reports summary (optimized queries)
    reporting_service = ReportingService()
    result = reporting_service.get_reports_summary(
        user_id=current_user.id,
        is_admin=current_user.is_admin
    )
    
    # Track report access
    log_event("report.viewed", user_id=current_user.id, report_type="summary")
    track_event(current_user.id, "report.viewed", {"report_type": "summary"})
    
    return render_template(
        'reports/index.html',
        summary=result['summary'],
        recent_entries=result['recent_entries'],
        comparison=result['comparison']
    )

@reports_bp.route('/reports/comparison')
@login_required
def comparison_view():
    """Get comparison data for reports"""
    period = request.args.get('period', 'month')
    now = datetime.utcnow()
    
    if period == 'month':
        # This month vs last month
        this_period_start = datetime(now.year, now.month, 1)
        last_period_start = (this_period_start - timedelta(days=1)).replace(day=1)
        last_period_end = this_period_start - timedelta(seconds=1)
    else:  # year
        # This year vs last year
        this_period_start = datetime(now.year, 1, 1)
        last_period_start = datetime(now.year - 1, 1, 1)
        last_period_end = datetime(now.year, 1, 1) - timedelta(seconds=1)
    
    # Get hours for current period
    current_query = db.session.query(db.func.sum(TimeEntry.duration_seconds)).filter(
        TimeEntry.end_time.isnot(None),
        TimeEntry.start_time >= this_period_start,
        TimeEntry.start_time <= now
    )
    if not current_user.is_admin:
        current_query = current_query.filter(TimeEntry.user_id == current_user.id)
    current_seconds = current_query.scalar() or 0
    
    # Get hours for previous period
    previous_query = db.session.query(db.func.sum(TimeEntry.duration_seconds)).filter(
        TimeEntry.end_time.isnot(None),
        TimeEntry.start_time >= last_period_start,
        TimeEntry.start_time <= last_period_end
    )
    if not current_user.is_admin:
        previous_query = previous_query.filter(TimeEntry.user_id == current_user.id)
    previous_seconds = previous_query.scalar() or 0
    
    current_hours = round(current_seconds / 3600, 2)
    previous_hours = round(previous_seconds / 3600, 2)
    change = ((current_hours - previous_hours) / previous_hours * 100) if previous_hours > 0 else 0
    
    return jsonify({
        'current': {'hours': current_hours},
        'previous': {'hours': previous_hours},
        'change': round(change, 1)
    })

@reports_bp.route('/reports/project')
@login_required
def project_report():
    """Project-based time report"""
    project_id = request.args.get('project_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    user_id = request.args.get('user_id', type=int)
    
    # Get projects for filter
    projects = Project.query.filter_by(status='active').order_by(Project.name).all()
    users = User.query.filter_by(is_active=True).order_by(User.username).all()
    
    # Parse dates
    if not start_date:
        start_date = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.utcnow().strftime('%Y-%m-%d')
    
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
    except ValueError:
        flash(_('Invalid date format'), 'error')
        return render_template('reports/project_report.html', projects=projects, users=users)
    
    # Get time entries
    query = TimeEntry.query.filter(
        TimeEntry.end_time.isnot(None),
        TimeEntry.start_time >= start_dt,
        TimeEntry.start_time <= end_dt
    )
    
    if project_id:
        query = query.filter(TimeEntry.project_id == project_id)
    
    if user_id:
        query = query.filter(TimeEntry.user_id == user_id)
    
    entries = query.order_by(TimeEntry.start_time.desc()).all()

    # Aggregate by project for template expectations
    projects_map = {}
    for entry in entries:
        project = entry.project
        if not project:
            continue
        if project.id not in projects_map:
            projects_map[project.id] = {
                'id': project.id,
                'name': project.name,
                'client': project.client,
                'description': project.description,
                'billable': project.billable,
                'hourly_rate': float(project.hourly_rate) if project.hourly_rate else None,
                'total_hours': 0.0,
                'billable_hours': 0.0,
                'billable_amount': 0.0,
                'total_costs': 0.0,
                'billable_costs': 0.0,
                'total_value': 0.0,
                'user_totals': {}
            }
        agg = projects_map[project.id]
        hours = entry.duration_hours
        agg['total_hours'] += hours
        if entry.billable and project.billable:
            agg['billable_hours'] += hours
            if project.hourly_rate:
                agg['billable_amount'] += hours * float(project.hourly_rate)
        # per-user totals
        username = entry.user.display_name if entry.user else 'Unknown'
        agg['user_totals'][username] = agg['user_totals'].get(username, 0.0) + hours
    
    # Add project costs to the aggregated data
    for project_id, agg in projects_map.items():
        # Get costs for this project within the date range
        costs_query = ProjectCost.query.filter(
            ProjectCost.project_id == project_id,
            ProjectCost.cost_date >= start_dt.date(),
            ProjectCost.cost_date <= end_dt.date()
        )
        
        if user_id:
            costs_query = costs_query.filter(ProjectCost.user_id == user_id)
        
        costs = costs_query.all()
        
        for cost in costs:
            agg['total_costs'] += float(cost.amount)
            if cost.billable:
                agg['billable_costs'] += float(cost.amount)
        
        # Calculate total project value (billable hours + billable costs)
        agg['total_value'] = agg['billable_amount'] + agg['billable_costs']

    # Finalize structures
    projects_data = []
    total_hours = 0.0
    billable_hours = 0.0
    total_billable_amount = 0.0
    total_costs = 0.0
    total_billable_costs = 0.0
    total_project_value = 0.0
    for agg in projects_map.values():
        total_hours += agg['total_hours']
        billable_hours += agg['billable_hours']
        total_billable_amount += agg['billable_amount']
        total_costs += agg['total_costs']
        total_billable_costs += agg['billable_costs']
        total_project_value += agg['total_value']
        agg['total_hours'] = round(agg['total_hours'], 1)
        agg['billable_hours'] = round(agg['billable_hours'], 1)
        agg['billable_amount'] = round(agg['billable_amount'], 2)
        agg['total_costs'] = round(agg['total_costs'], 2)
        agg['billable_costs'] = round(agg['billable_costs'], 2)
        agg['total_value'] = round(agg['total_value'], 2)
        agg['user_totals'] = [
            {'username': username, 'hours': round(hours, 1)}
            for username, hours in agg['user_totals'].items()
        ]
        projects_data.append(agg)

    # Summary section expected by template
    summary = {
        'total_hours': round(total_hours, 1),
        'billable_hours': round(billable_hours, 1),
        'total_billable_amount': round(total_billable_amount, 2),
        'total_costs': round(total_costs, 2),
        'total_billable_costs': round(total_billable_costs, 2),
        'total_project_value': round(total_project_value, 2),
        'projects_count': len(projects_data),
    }

    return render_template('reports/project_report.html',
                          projects=projects,
                          users=users,
                          entries=entries,
                          projects_data=projects_data,
                          summary=summary,
                          start_date=start_date,
                          end_date=end_date,
                          selected_project=project_id,
                          selected_user=user_id)

@reports_bp.route('/reports/user')
@login_required
def user_report():
    """User-based time report"""
    user_id = request.args.get('user_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    project_id = request.args.get('project_id', type=int)
    
    # Get users for filter
    users = User.query.filter_by(is_active=True).order_by(User.username).all()
    projects = Project.query.filter_by(status='active').order_by(Project.name).all()
    
    # Parse dates
    if not start_date:
        start_date = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.utcnow().strftime('%Y-%m-%d')
    
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
    except ValueError:
        flash(_('Invalid date format'), 'error')
        return render_template('reports/user_report.html', users=users, projects=projects)
    
    # Get time entries
    query = TimeEntry.query.filter(
        TimeEntry.end_time.isnot(None),
        TimeEntry.start_time >= start_dt,
        TimeEntry.start_time <= end_dt
    )
    
    if user_id:
        query = query.filter(TimeEntry.user_id == user_id)
    
    if project_id:
        query = query.filter(TimeEntry.project_id == project_id)
    
    entries = query.order_by(TimeEntry.start_time.desc()).all()

    # Calculate totals
    total_hours = sum(entry.duration_hours for entry in entries)
    billable_hours = sum(entry.duration_hours for entry in entries if entry.billable)

    # Group by user
    user_totals = {}
    projects_set = set()
    users_set = set()
    for entry in entries:
        if entry.project:
            projects_set.add(entry.project.id)
        if entry.user:
            users_set.add(entry.user.id)
        username = entry.user.display_name if entry.user else 'Unknown'
        if username not in user_totals:
            user_totals[username] = {
                'hours': 0,
                'billable_hours': 0,
                'entries': [],
                'user_obj': entry.user  # Store user object for overtime calculation
            }
        user_totals[username]['hours'] += entry.duration_hours
        if entry.billable:
            user_totals[username]['billable_hours'] += entry.duration_hours
        user_totals[username]['entries'].append(entry)

    # Calculate overtime for each user
    from app.utils.overtime import calculate_period_overtime
    for username, data in user_totals.items():
        if data['user_obj']:
            overtime_data = calculate_period_overtime(
                data['user_obj'],
                start_dt.date(),
                end_dt.date()
            )
            data['regular_hours'] = overtime_data['regular_hours']
            data['overtime_hours'] = overtime_data['overtime_hours']
            data['days_with_overtime'] = overtime_data['days_with_overtime']

    summary = {
        'total_hours': round(total_hours, 1),
        'billable_hours': round(billable_hours, 1),
        'users_count': len(users_set),
        'projects_count': len(projects_set),
    }

    return render_template('reports/user_report.html',
                         users=users,
                         projects=projects,
                         entries=entries,
                         user_totals=user_totals,
                         summary=summary,
                         start_date=start_date,
                         end_date=end_date,
                         selected_user=user_id,
                         selected_project=project_id)

@reports_bp.route('/reports/export/form')
@login_required
def export_form():
    """Display CSV export form with filter options"""
    # Get all users (for admin)
    users = []
    if current_user.is_admin:
        users = User.query.filter_by(is_active=True).order_by(User.username).all()
    
    # Get all active projects
    projects = Project.query.filter_by(status='active').order_by(Project.name).all()
    
    # Get all active clients
    clients = Client.query.filter_by(status='active').order_by(Client.name).all()
    
    # Set default date range (last 30 days)
    default_end_date = datetime.utcnow().strftime('%Y-%m-%d')
    default_start_date = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    return render_template('reports/export_form.html',
                         users=users,
                         projects=projects,
                         clients=clients,
                         default_start_date=default_start_date,
                         default_end_date=default_end_date)

@reports_bp.route('/reports/export/csv')
@login_required
def export_csv():
    """Export time entries as CSV with enhanced filters"""
    start_time = time.time()  # Start performance tracking
    
    # Get all filter parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    user_id = request.args.get('user_id', type=int)
    project_id = request.args.get('project_id', type=int)
    task_id = request.args.get('task_id', type=int)
    client_id = request.args.get('client_id', type=int)
    billable = request.args.get('billable')  # 'yes', 'no', or 'all'
    source = request.args.get('source')  # 'manual', 'auto', or 'all'
    tags = request.args.get('tags', '').strip()
    
    # Parse dates
    if not start_date:
        start_date = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.utcnow().strftime('%Y-%m-%d')
    
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
    except ValueError:
        track_validation_error(
            current_user.id,
            "date_range",
            "Invalid date format for CSV export",
            {"start_date": start_date, "end_date": end_date}
        )
        flash(_('Invalid date format'), 'error')
        return redirect(url_for('reports.reports'))
    
    # Get time entries
    query = TimeEntry.query.filter(
        TimeEntry.end_time.isnot(None),
        TimeEntry.start_time >= start_dt,
        TimeEntry.start_time <= end_dt
    )
    
    if user_id:
        query = query.filter(TimeEntry.user_id == user_id)
    
    if project_id:
        query = query.filter(TimeEntry.project_id == project_id)
    
    entries = query.order_by(TimeEntry.start_time.desc()).all()
    
    # Get settings for delimiter
    settings = Settings.get_settings()
    delimiter = settings.export_delimiter
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output, delimiter=delimiter)
    
    # Write header with task column
    writer.writerow([
        'ID', 'User', 'Project', 'Client', 'Task', 'Start Time', 'End Time', 
        'Duration (hours)', 'Duration (formatted)', 'Notes', 'Tags', 
        'Source', 'Billable', 'Created At', 'Updated At'
    ])
    
    # Write data
    for entry in entries:
        writer.writerow([
            entry.id,
            entry.user.display_name,
            entry.project.name,
            entry.project.client,
            entry.task.name if entry.task else '',
            entry.start_time.isoformat(),
            entry.end_time.isoformat() if entry.end_time else '',
            entry.duration_hours,
            entry.duration_formatted,
            entry.notes or '',
            entry.tags or '',
            entry.source,
            'Yes' if entry.billable else 'No',
            entry.created_at.isoformat(),
            entry.updated_at.isoformat() if entry.updated_at else ''
        ])
    
    output.seek(0)
    
    # Create filename with filters indication
    filename_parts = [f'timetracker_export_{start_date}_to_{end_date}']
    if project_id:
        filename_parts.append('project')
    if client_id:
        filename_parts.append('client')
    if task_id:
        filename_parts.append('task')
    filename = '_'.join(filename_parts) + '.csv'
    
    # Track CSV export event with enhanced metadata
    log_event("export.csv", 
             user_id=current_user.id, 
             export_type="time_entries",
             num_rows=len(entries),
             date_range_days=(end_dt - start_dt).days,
             filters_applied={
                 'user_id': user_id,
                 'project_id': project_id,
                 'task_id': task_id,
                 'client_id': client_id,
                 'billable': billable,
                 'source': source,
                 'tags': tags
             })
    track_event(current_user.id, "export.csv", {
        "export_type": "time_entries",
        "num_rows": len(entries),
        "date_range_days": (end_dt - start_dt).days,
        "has_project_filter": project_id is not None,
        "has_client_filter": client_id is not None,
        "has_task_filter": task_id is not None,
        "has_billable_filter": billable is not None and billable != 'all',
        "has_source_filter": source is not None and source != 'all',
        "has_tags_filter": bool(tags)
    })
    
    # Track performance
    try:
        duration_ms = (time.time() - start_time) * 1000
        csv_content = output.getvalue().encode('utf-8')
        track_export_performance(
            current_user.id,
            "csv",
            row_count=len(entries),
            duration_ms=duration_ms,
            file_size_bytes=len(csv_content)
        )
    except Exception as e:
        # Don't let tracking errors break the export
        pass
    
    return send_file(
        io.BytesIO(csv_content),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )

@reports_bp.route('/reports/summary')
@login_required
def summary_report():
    """Summary report with key metrics"""
    # Get date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    
    # Get total hours for different periods
    today_hours = TimeEntry.get_total_hours_for_period(
        start_date=end_date.date(),
        user_id=current_user.id if not current_user.is_admin else None
    )
    
    week_hours = TimeEntry.get_total_hours_for_period(
        start_date=end_date.date() - timedelta(days=7),
        user_id=current_user.id if not current_user.is_admin else None
    )
    
    month_hours = TimeEntry.get_total_hours_for_period(
        start_date=start_date.date(),
        user_id=current_user.id if not current_user.is_admin else None
    )
    
    # Get top projects
    if current_user.is_admin:
        # For admins, show all projects
        projects = Project.query.filter_by(status='active').all()
    else:
        # For users, show only their projects
        project_ids = db.session.query(TimeEntry.project_id).filter(
            TimeEntry.user_id == current_user.id
        ).distinct().all()
        project_ids = [pid[0] for pid in project_ids]
        projects = Project.query.filter(Project.id.in_(project_ids)).all()
    
    # Sort projects by total hours
    project_stats = []
    for project in projects:
        hours = TimeEntry.get_total_hours_for_period(
            start_date=start_date.date(),
            project_id=project.id,
            user_id=current_user.id if not current_user.is_admin else None
        )
        if hours > 0:
            project_stats.append({
                'project': project,
                'hours': hours
            })
    
    project_stats.sort(key=lambda x: x['hours'], reverse=True)
    
    return render_template('reports/summary.html',
                         today_hours=today_hours,
                         week_hours=week_hours,
                         month_hours=month_hours,
                         project_stats=project_stats[:10])  # Top 10 projects


@reports_bp.route('/reports/tasks')
@login_required
def task_report():
    """Report of finished tasks within a project, including hours spent per task"""
    project_id = request.args.get('project_id', type=int)
    user_id = request.args.get('user_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # Filters data
    projects = Project.query.order_by(Project.name).all()
    users = User.query.filter_by(is_active=True).order_by(User.username).all()

    # Default date range: last 30 days
    if not start_date:
        start_date = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.utcnow().strftime('%Y-%m-%d')

    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
    except ValueError:
        flash(_('Invalid date format'), 'error')
        return render_template('reports/task_report.html', projects=projects, users=users)

    # Base tasks query: finished tasks
    tasks_query = Task.query.filter(Task.status == 'done')

    if project_id:
        tasks_query = tasks_query.filter(Task.project_id == project_id)

    # Filter by completion window intersects [start_dt, end_dt]
    tasks_query = tasks_query.filter(Task.completed_at.isnot(None))
    tasks_query = tasks_query.filter(Task.completed_at >= start_dt, Task.completed_at <= end_dt)

    # Optional: only tasks that have time entries by a specific user
    if user_id:
        tasks_query = tasks_query.join(TimeEntry, TimeEntry.task_id == Task.id).filter(TimeEntry.user_id == user_id)

    tasks = tasks_query.order_by(Task.completed_at.desc()).all()

    # Compute hours per task (sum of entry durations; respect user/project filters and date range)
    task_rows = []
    total_hours = 0.0
    for task in tasks:
        te_query = TimeEntry.query.filter(
            TimeEntry.task_id == task.id,
            TimeEntry.end_time.isnot(None),
            TimeEntry.start_time >= start_dt,
            TimeEntry.start_time <= end_dt
        )
        if project_id:
            te_query = te_query.filter(TimeEntry.project_id == project_id)
        if user_id:
            te_query = te_query.filter(TimeEntry.user_id == user_id)

        entries = te_query.all()
        hours = sum(e.duration_hours for e in entries)
        total_hours += hours

        task_rows.append({
            'task': task,
            'project': task.project,
            'assignee': task.assigned_user,
            'completed_at': task.completed_at,
            'hours': round(hours, 2),
            'entries_count': len(entries),
        })

    summary = {
        'tasks_count': len(task_rows),
        'total_hours': round(total_hours, 2),
    }

    return render_template(
        'reports/task_report.html',
        projects=projects,
        users=users,
        tasks=task_rows,
        summary=summary,
        start_date=start_date,
        end_date=end_date,
        selected_project=project_id,
        selected_user=user_id,
    )


@reports_bp.route('/reports/export/excel')
@login_required
def export_excel():
    """Export time entries as Excel file"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    user_id = request.args.get('user_id', type=int)
    project_id = request.args.get('project_id', type=int)
    
    # Parse dates
    if not start_date:
        start_date = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.utcnow().strftime('%Y-%m-%d')
    
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
    except ValueError:
        flash(_('Invalid date format'), 'error')
        return redirect(url_for('reports.reports'))
    
    # Get time entries
    query = TimeEntry.query.filter(
        TimeEntry.end_time.isnot(None),
        TimeEntry.start_time >= start_dt,
        TimeEntry.start_time <= end_dt
    )
    
    if user_id:
        query = query.filter(TimeEntry.user_id == user_id)
    
    if project_id:
        query = query.filter(TimeEntry.project_id == project_id)
    
    entries = query.order_by(TimeEntry.start_time.desc()).all()
    
    # Create Excel file
    output, filename = create_time_entries_excel(entries, filename_prefix='timetracker_export')
    
    # Track Excel export event
    log_event("export.excel", 
             user_id=current_user.id, 
             export_type="time_entries",
             num_rows=len(entries),
             date_range_days=(end_dt - start_dt).days)
    track_event(current_user.id, "export.excel", {
        "export_type": "time_entries",
        "num_rows": len(entries),
        "date_range_days": (end_dt - start_dt).days
    })
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


@reports_bp.route('/reports/project/export/excel')
@login_required
def export_project_excel():
    """Export project report as Excel file"""
    project_id = request.args.get('project_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    user_id = request.args.get('user_id', type=int)
    
    # Parse dates
    if not start_date:
        start_date = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.utcnow().strftime('%Y-%m-%d')
    
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
    except ValueError:
        flash(_('Invalid date format'), 'error')
        return redirect(url_for('reports.project_report'))
    
    # Get time entries
    query = TimeEntry.query.filter(
        TimeEntry.end_time.isnot(None),
        TimeEntry.start_time >= start_dt,
        TimeEntry.start_time <= end_dt
    )
    
    if project_id:
        query = query.filter(TimeEntry.project_id == project_id)
    
    if user_id:
        query = query.filter(TimeEntry.user_id == user_id)
    
    entries = query.all()
    
    # Aggregate by project
    projects_map = {}
    for entry in entries:
        project = entry.project
        if not project:
            continue
        if project.id not in projects_map:
            projects_map[project.id] = {
                'name': project.name,
                'client': project.client if project.client else '',
                'total_hours': 0,
                'billable_hours': 0,
                'hourly_rate': float(project.hourly_rate) if project.hourly_rate else 0,
                'billable_amount': 0,
                'total_costs': 0,
                'total_value': 0,
            }
        agg = projects_map[project.id]
        hours = entry.duration_hours
        agg['total_hours'] += hours
        if entry.billable and project.billable:
            agg['billable_hours'] += hours
            if project.hourly_rate:
                agg['billable_amount'] += hours * float(project.hourly_rate)
    
    projects_data = list(projects_map.values())
    
    # Create Excel file
    output, filename = create_project_report_excel(projects_data, start_date, end_date)
    
    # Track event
    log_event("export.excel", 
             user_id=current_user.id, 
             export_type="project_report",
             num_projects=len(projects_data))
    track_event(current_user.id, "export.excel", {
        "export_type": "project_report",
        "num_projects": len(projects_data)
    })
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )
