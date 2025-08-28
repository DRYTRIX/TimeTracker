from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from app import db
from app.models import User, Project, TimeEntry, Settings
from datetime import datetime, timedelta
import csv
import io
import pytz

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/reports')
@login_required
def reports():
    """Main reports page"""
    # Aggregate totals (scope by user unless admin)
    totals_query = db.session.query(db.func.sum(TimeEntry.duration_seconds)).filter(
        TimeEntry.end_time.isnot(None)
    )
    billable_query = db.session.query(db.func.sum(TimeEntry.duration_seconds)).filter(
        TimeEntry.end_time.isnot(None),
        TimeEntry.billable == True
    )

    entries_query = TimeEntry.query.filter(TimeEntry.end_time.isnot(None))

    if not current_user.is_admin:
        totals_query = totals_query.filter(TimeEntry.user_id == current_user.id)
        billable_query = billable_query.filter(TimeEntry.user_id == current_user.id)
        entries_query = entries_query.filter(TimeEntry.user_id == current_user.id)

    total_seconds = totals_query.scalar() or 0
    billable_seconds = billable_query.scalar() or 0

    summary = {
        'total_hours': round(total_seconds / 3600, 2),
        'billable_hours': round(billable_seconds / 3600, 2),
        'active_projects': Project.query.filter_by(status='active').count(),
        'total_users': User.query.filter_by(is_active=True).count(),
    }

    recent_entries = entries_query.order_by(TimeEntry.start_time.desc()).limit(10).all()

    return render_template('reports/index.html', summary=summary, recent_entries=recent_entries)

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
        flash('Invalid date format', 'error')
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
        username = entry.user.username if entry.user else 'Unknown'
        agg['user_totals'][username] = agg['user_totals'].get(username, 0.0) + hours

    # Finalize structures
    projects_data = []
    total_hours = 0.0
    billable_hours = 0.0
    total_billable_amount = 0.0
    for agg in projects_map.values():
        total_hours += agg['total_hours']
        billable_hours += agg['billable_hours']
        total_billable_amount += agg['billable_amount']
        agg['total_hours'] = round(agg['total_hours'], 1)
        agg['billable_hours'] = round(agg['billable_hours'], 1)
        agg['billable_amount'] = round(agg['billable_amount'], 2)
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
        flash('Invalid date format', 'error')
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
        username = entry.user.username if entry.user else 'Unknown'
        if username not in user_totals:
            user_totals[username] = {
                'hours': 0,
                'billable_hours': 0,
                'entries': []
            }
        user_totals[username]['hours'] += entry.duration_hours
        if entry.billable:
            user_totals[username]['billable_hours'] += entry.duration_hours
        user_totals[username]['entries'].append(entry)

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

@reports_bp.route('/reports/export/csv')
@login_required
def export_csv():
    """Export time entries as CSV"""
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
        flash('Invalid date format', 'error')
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
    
    # Write header
    writer.writerow([
        'ID', 'User', 'Project', 'Client', 'Start Time', 'End Time', 
        'Duration (hours)', 'Duration (formatted)', 'Notes', 'Tags', 
        'Source', 'Billable', 'Created At'
    ])
    
    # Write data
    for entry in entries:
        writer.writerow([
            entry.id,
            entry.user.username,
            entry.project.name,
            entry.project.client,
            entry.start_time.isoformat(),
            entry.end_time.isoformat() if entry.end_time else '',
            entry.duration_hours,
            entry.duration_formatted,
            entry.notes or '',
            entry.tags or '',
            entry.source,
            'Yes' if entry.billable else 'No',
            entry.created_at.isoformat()
        ])
    
    output.seek(0)
    
    # Create filename
    filename = f'timetracker_export_{start_date}_to_{end_date}.csv'
    
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
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
