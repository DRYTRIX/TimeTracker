from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import User, Project, TimeEntry, Settings, Task
from datetime import datetime, timedelta
from sqlalchemy import func, extract
import calendar

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/analytics')
@login_required
def analytics_dashboard():
    """Main analytics dashboard with charts"""
    # Check if user agent indicates mobile device
    user_agent = request.headers.get('User-Agent', '').lower()
    is_mobile = any(device in user_agent for device in ['mobile', 'android', 'iphone', 'ipad'])
    
    # Check for legacy/simple dashboard query parameter
    use_legacy = request.args.get('legacy', '').lower() == 'true'
    
    if is_mobile:
        return render_template('analytics/mobile_dashboard.html')
    elif use_legacy:
        return render_template('analytics/dashboard.html')
    else:
        return render_template('analytics/dashboard_improved.html')

@analytics_bp.route('/api/analytics/hours-by-day')
@login_required
def hours_by_day():
    """Get hours worked per day for the last 30 days"""
    days = int(request.args.get('days', 30))
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Build query based on user permissions
    query = db.session.query(
        func.date(TimeEntry.start_time).label('date'),
        func.sum(TimeEntry.duration_seconds).label('total_seconds')
    ).filter(
        TimeEntry.end_time.isnot(None),
        TimeEntry.start_time >= start_date,
        TimeEntry.start_time <= end_date
    )
    
    if not current_user.is_admin:
        query = query.filter(TimeEntry.user_id == current_user.id)
    
    results = query.group_by(func.date(TimeEntry.start_time)).all()
    
    # Create date range and fill missing dates with 0
    date_data = {}
    current_date = start_date
    while current_date <= end_date:
        date_data[current_date.strftime('%Y-%m-%d')] = 0
        current_date += timedelta(days=1)
    
    # Fill in actual data
    for date_str, total_seconds in results:
        if date_str:
            date_data[date_str.strftime('%Y-%m-%d')] = round(total_seconds / 3600, 2)
    
    return jsonify({
        'labels': list(date_data.keys()),
        'datasets': [{
            'label': 'Hours Worked',
            'data': list(date_data.values()),
            'borderColor': '#3b82f6',
            'backgroundColor': 'rgba(59, 130, 246, 0.1)',
            'tension': 0.4,
            'fill': True
        }]
    })

@analytics_bp.route('/api/analytics/hours-by-project')
@login_required
def hours_by_project():
    """Get total hours per project"""
    days = int(request.args.get('days', 30))
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    query = db.session.query(
        Project.name,
        func.sum(TimeEntry.duration_seconds).label('total_seconds')
    ).join(TimeEntry).filter(
        TimeEntry.end_time.isnot(None),
        TimeEntry.start_time >= start_date,
        TimeEntry.start_time <= end_date,
        Project.status == 'active'
    )
    
    if not current_user.is_admin:
        query = query.filter(TimeEntry.user_id == current_user.id)
    
    results = query.group_by(Project.name).order_by(func.sum(TimeEntry.duration_seconds).desc()).limit(10).all()
    
    labels = [project for project, _ in results]
    data = [round(seconds / 3600, 2) for _, seconds in results]
    
    # Generate colors for each project
    colors = [
        '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
        '#06b6d4', '#84cc16', '#f97316', '#ec4899', '#6366f1'
    ]
    
    return jsonify({
        'labels': labels,
        'datasets': [{
            'label': 'Hours',
            'data': data,
            'backgroundColor': colors[:len(labels)],
            'borderColor': colors[:len(labels)],
            'borderWidth': 1
        }]
    })

@analytics_bp.route('/api/analytics/hours-by-user')
@login_required
def hours_by_user():
    """Get total hours per user (admin only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    days = int(request.args.get('days', 30))
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    results = db.session.query(
        User.username,
        func.sum(TimeEntry.duration_seconds).label('total_seconds')
    ).join(TimeEntry).filter(
        TimeEntry.end_time.isnot(None),
        TimeEntry.start_time >= start_date,
        TimeEntry.start_time <= end_date,
        User.is_active == True
    ).group_by(User.username).order_by(func.sum(TimeEntry.duration_seconds).desc()).all()
    
    labels = [username for username, _ in results]
    data = [round(seconds / 3600, 2) for _, seconds in results]
    
    return jsonify({
        'labels': labels,
        'datasets': [{
            'label': 'Hours',
            'data': data,
            'backgroundColor': 'rgba(59, 130, 246, 0.8)',
            'borderColor': '#3b82f6',
            'borderWidth': 2
        }]
    })

@analytics_bp.route('/api/analytics/hours-by-hour')
@login_required
def hours_by_hour():
    """Get hours worked by hour of day (24-hour format)"""
    days = int(request.args.get('days', 30))
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    query = db.session.query(
        extract('hour', TimeEntry.start_time).label('hour'),
        func.sum(TimeEntry.duration_seconds).label('total_seconds')
    ).filter(
        TimeEntry.end_time.isnot(None),
        TimeEntry.start_time >= start_date,
        TimeEntry.start_time <= end_date
    )
    
    if not current_user.is_admin:
        query = query.filter(TimeEntry.user_id == current_user.id)
    
    results = query.group_by(extract('hour', TimeEntry.start_time)).order_by(extract('hour', TimeEntry.start_time)).all()
    
    # Create 24-hour array
    hours_data = [0] * 24
    for hour, total_seconds in results:
        hours_data[int(hour)] = round(total_seconds / 3600, 2)
    
    labels = [f"{hour:02d}:00" for hour in range(24)]
    
    return jsonify({
        'labels': labels,
        'datasets': [{
            'label': 'Hours Worked',
            'data': hours_data,
            'backgroundColor': 'rgba(16, 185, 129, 0.8)',
            'borderColor': '#10b981',
            'borderWidth': 2,
            'tension': 0.4
        }]
    })

@analytics_bp.route('/api/analytics/billable-vs-nonbillable')
@login_required
def billable_vs_nonbillable():
    """Get billable vs non-billable hours breakdown"""
    days = int(request.args.get('days', 30))
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    query = db.session.query(
        TimeEntry.billable,
        func.sum(TimeEntry.duration_seconds).label('total_seconds')
    ).filter(
        TimeEntry.end_time.isnot(None),
        TimeEntry.start_time >= start_date,
        TimeEntry.start_time <= end_date
    )
    
    if not current_user.is_admin:
        query = query.filter(TimeEntry.user_id == current_user.id)
    
    results = query.group_by(TimeEntry.billable).all()
    
    billable_hours = 0
    nonbillable_hours = 0
    
    for billable, total_seconds in results:
        hours = round(total_seconds / 3600, 2)
        if billable:
            billable_hours = hours
        else:
            nonbillable_hours = hours
    
    return jsonify({
        'labels': ['Billable', 'Non-Billable'],
        'datasets': [{
            'label': 'Hours',
            'data': [billable_hours, nonbillable_hours],
            'backgroundColor': ['#10b981', '#6b7280'],
            'borderColor': ['#059669', '#4b5563'],
            'borderWidth': 2
        }]
    })

@analytics_bp.route('/api/analytics/weekly-trends')
@login_required
def weekly_trends():
    """Get weekly trends over the last 12 weeks"""
    weeks = int(request.args.get('weeks', 12))
    end_date = datetime.now().date()
    start_date = end_date - timedelta(weeks=weeks)
    
    query = db.session.query(
        func.date_trunc('week', TimeEntry.start_time).label('week'),
        func.sum(TimeEntry.duration_seconds).label('total_seconds')
    ).filter(
        TimeEntry.end_time.isnot(None),
        TimeEntry.start_time >= start_date,
        TimeEntry.start_time <= end_date
    )
    
    if not current_user.is_admin:
        query = query.filter(TimeEntry.user_id == current_user.id)
    
    results = query.group_by(func.date_trunc('week', TimeEntry.start_time)).order_by(func.date_trunc('week', TimeEntry.start_time)).all()
    
    labels = []
    data = []
    
    for week, total_seconds in results:
        if week:
            # Format week as "MMM DD" (e.g., "Jan 01")
            week_date = week.date()
            labels.append(week_date.strftime('%b %d'))
            data.append(round(total_seconds / 3600, 2))
    
    return jsonify({
        'labels': labels,
        'datasets': [{
            'label': 'Weekly Hours',
            'data': data,
            'borderColor': '#8b5cf6',
            'backgroundColor': 'rgba(139, 92, 246, 0.1)',
            'tension': 0.4,
            'fill': True,
            'pointBackgroundColor': '#8b5cf6',
            'pointBorderColor': '#ffffff',
            'pointBorderWidth': 2
        }]
    })

@analytics_bp.route('/api/analytics/project-efficiency')
@login_required
def project_efficiency():
    """Get project efficiency metrics (hours vs billable amount)"""
    days = int(request.args.get('days', 30))
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    query = db.session.query(
        Project.name,
        func.sum(TimeEntry.duration_seconds).label('total_seconds'),
        Project.hourly_rate
    ).join(TimeEntry).filter(
        TimeEntry.end_time.isnot(None),
        TimeEntry.start_time >= start_date,
        TimeEntry.start_time <= end_date,
        Project.status == 'active',
        Project.billable == True,
        Project.hourly_rate.isnot(None)
    )
    
    if not current_user.is_admin:
        query = query.filter(TimeEntry.user_id == current_user.id)
    
    results = query.group_by(Project.name, Project.hourly_rate).order_by(func.sum(TimeEntry.duration_seconds).desc()).limit(8).all()
    
    labels = [project for project, _, _ in results]
    hours_data = [round(seconds / 3600, 2) for _, seconds, _ in results]
    revenue_data = [round((seconds / 3600) * float(rate), 2) for _, seconds, rate in results]
    
    return jsonify({
        'labels': labels,
        'datasets': [
            {
                'label': 'Hours',
                'data': hours_data,
                'backgroundColor': 'rgba(59, 130, 246, 0.8)',
                'borderColor': '#3b82f6',
                'borderWidth': 2,
                'yAxisID': 'y'
            },
            {
                'label': 'Revenue',
                'data': revenue_data,
                'backgroundColor': 'rgba(16, 185, 129, 0.8)',
                'borderColor': '#10b981',
                'borderWidth': 2,
                'yAxisID': 'y1'
            }
        ]
    })


@analytics_bp.route('/api/analytics/today-by-task')
@login_required
def today_by_task():
    """Get today's total hours grouped by task (includes project-level entries without task).

    Optional query params:
    - date: YYYY-MM-DD (defaults to today)
    - user_id: admin-only override to view a specific user's data
    """
    # Parse target date
    date_str = request.args.get('date')
    if date_str:
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format, expected YYYY-MM-DD'}), 400
    else:
        target_date = datetime.now().date()

    # Base query
    query = db.session.query(
        TimeEntry.task_id,
        Task.name.label('task_name'),
        TimeEntry.project_id,
        Project.name.label('project_name'),
        func.sum(TimeEntry.duration_seconds).label('total_seconds')
    ).join(
        Project, Project.id == TimeEntry.project_id
    ).outerjoin(
        Task, Task.id == TimeEntry.task_id
    ).filter(
        TimeEntry.end_time.isnot(None),
        func.date(TimeEntry.start_time) == target_date
    )

    # Scope to current user unless admin (with optional override)
    if not current_user.is_admin:
        query = query.filter(TimeEntry.user_id == current_user.id)
    else:
        user_id = request.args.get('user_id', type=int)
        if user_id:
            query = query.filter(TimeEntry.user_id == user_id)

    results = query.group_by(
        TimeEntry.task_id,
        Task.name,
        TimeEntry.project_id,
        Project.name
    ).order_by(func.sum(TimeEntry.duration_seconds).desc()).all()

    rows = []
    for task_id, task_name, project_id, project_name, total_seconds in results:
        total_seconds = int(total_seconds or 0)
        total_hours = round(total_seconds / 3600, 2)
        label = f"{project_name} • {task_name}" if task_name else f"{project_name} • No task"
        rows.append({
            'task_id': task_id,
            'task_name': task_name,
            'project_id': project_id,
            'project_name': project_name,
            'total_seconds': total_seconds,
            'total_hours': total_hours,
            'label': label
        })

    return jsonify({
        'date': target_date.strftime('%Y-%m-%d'),
        'rows': rows
    })


@analytics_bp.route('/api/analytics/summary-with-comparison')
@login_required
def summary_with_comparison():
    """Get summary metrics with comparison to previous period"""
    days = int(request.args.get('days', 30))
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Previous period dates
    prev_end_date = start_date - timedelta(days=1)
    prev_start_date = prev_end_date - timedelta(days=days)
    
    # Current period query
    current_query = db.session.query(
        func.sum(TimeEntry.duration_seconds).label('total_seconds'),
        func.count(TimeEntry.id).label('total_entries'),
        func.sum(func.case((TimeEntry.billable == True, TimeEntry.duration_seconds), else_=0)).label('billable_seconds')
    ).filter(
        TimeEntry.end_time.isnot(None),
        TimeEntry.start_time >= start_date,
        TimeEntry.start_time <= end_date
    )
    
    # Previous period query
    prev_query = db.session.query(
        func.sum(TimeEntry.duration_seconds).label('total_seconds'),
        func.count(TimeEntry.id).label('total_entries'),
        func.sum(func.case((TimeEntry.billable == True, TimeEntry.duration_seconds), else_=0)).label('billable_seconds')
    ).filter(
        TimeEntry.end_time.isnot(None),
        TimeEntry.start_time >= prev_start_date,
        TimeEntry.start_time <= prev_end_date
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
    active_projects = Project.query.filter_by(status='active').count()
    
    # Calculate average daily hours
    avg_daily_hours = round(current_hours / days, 1) if days > 0 else 0
    
    # Calculate billable percentage
    billable_percentage = round((current_billable / current_hours * 100), 1) if current_hours > 0 else 0
    
    return jsonify({
        'total_hours': current_hours,
        'total_hours_change': round(hours_change, 1),
        'billable_hours': current_billable,
        'billable_hours_change': round(billable_change, 1),
        'total_entries': current_entries,
        'entries_change': round(entries_change, 1),
        'active_projects': active_projects,
        'avg_daily_hours': avg_daily_hours,
        'billable_percentage': billable_percentage
    })


@analytics_bp.route('/api/analytics/task-completion')
@login_required
def task_completion():
    """Get task completion analytics"""
    days = int(request.args.get('days', 30))
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Get tasks completed in period
    completed_query = db.session.query(
        func.count(Task.id).label('count')
    ).filter(
        Task.status == 'done',
        Task.completed_at >= start_date,
        Task.completed_at <= end_date
    )
    
    if not current_user.is_admin:
        completed_query = completed_query.filter(Task.assigned_to == current_user.id)
    
    completed_count = completed_query.scalar() or 0
    
    # Get tasks by status
    status_query = db.session.query(
        Task.status,
        func.count(Task.id).label('count')
    ).filter(
        Task.created_at >= start_date
    )
    
    if not current_user.is_admin:
        status_query = status_query.filter(Task.assigned_to == current_user.id)
    
    status_results = status_query.group_by(Task.status).all()
    
    status_data = {
        'todo': 0,
        'in_progress': 0,
        'review': 0,
        'done': 0,
        'cancelled': 0
    }
    
    for status, count in status_results:
        if status in status_data:
            status_data[status] = count
    
    # Get task completion rate by project
    project_query = db.session.query(
        Project.name,
        func.count(Task.id).label('total_tasks'),
        func.sum(func.case((Task.status == 'done', 1), else_=0)).label('completed_tasks')
    ).join(Task).filter(
        Task.created_at >= start_date,
        Project.status == 'active'
    )
    
    if not current_user.is_admin:
        project_query = project_query.filter(Task.assigned_to == current_user.id)
    
    project_results = project_query.group_by(Project.name).order_by(
        func.count(Task.id).desc()
    ).limit(10).all()
    
    project_labels = []
    project_completion_rates = []
    
    for project_name, total, completed in project_results:
        project_labels.append(project_name)
        rate = (completed / total * 100) if total > 0 else 0
        project_completion_rates.append(round(rate, 1))
    
    return jsonify({
        'completed_count': completed_count,
        'status_breakdown': status_data,
        'project_labels': project_labels,
        'project_completion_rates': project_completion_rates
    })


@analytics_bp.route('/api/analytics/revenue-metrics')
@login_required
def revenue_metrics():
    """Get revenue and financial metrics"""
    days = int(request.args.get('days', 30))
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    settings = Settings.get_settings()
    currency = settings.currency
    
    # Get billable hours with rates
    query = db.session.query(
        func.sum(TimeEntry.duration_seconds).label('total_seconds'),
        Project.hourly_rate
    ).join(Project).filter(
        TimeEntry.end_time.isnot(None),
        TimeEntry.start_time >= start_date,
        TimeEntry.start_time <= end_date,
        TimeEntry.billable == True,
        Project.billable == True,
        Project.hourly_rate.isnot(None)
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
    billable_query = db.session.query(
        func.sum(TimeEntry.duration_seconds).label('total_seconds')
    ).filter(
        TimeEntry.end_time.isnot(None),
        TimeEntry.start_time >= start_date,
        TimeEntry.start_time <= end_date,
        TimeEntry.billable == True
    )
    
    if not current_user.is_admin:
        billable_query = billable_query.filter(TimeEntry.user_id == current_user.id)
    
    billable_seconds = billable_query.scalar() or 0
    billable_hours = round(billable_seconds / 3600, 1)
    
    # Calculate average hourly rate
    avg_hourly_rate = (total_revenue / billable_hours) if billable_hours > 0 else 0
    
    # Get revenue by project
    project_query = db.session.query(
        Project.name,
        func.sum(TimeEntry.duration_seconds).label('total_seconds'),
        Project.hourly_rate
    ).join(TimeEntry).filter(
        TimeEntry.end_time.isnot(None),
        TimeEntry.start_time >= start_date,
        TimeEntry.start_time <= end_date,
        TimeEntry.billable == True,
        Project.billable == True,
        Project.hourly_rate.isnot(None)
    )
    
    if not current_user.is_admin:
        project_query = project_query.filter(TimeEntry.user_id == current_user.id)
    
    project_results = project_query.group_by(
        Project.name, Project.hourly_rate
    ).order_by(func.sum(TimeEntry.duration_seconds).desc()).limit(8).all()
    
    project_labels = []
    project_revenue = []
    
    for project_name, seconds, rate in project_results:
        project_labels.append(project_name)
        if seconds and rate:
            revenue = (seconds / 3600) * float(rate)
            project_revenue.append(round(revenue, 2))
        else:
            project_revenue.append(0)
    
    return jsonify({
        'total_revenue': round(total_revenue, 2),
        'billable_hours': billable_hours,
        'avg_hourly_rate': round(avg_hourly_rate, 2),
        'currency': currency,
        'project_labels': project_labels,
        'project_revenue': project_revenue
    })


@analytics_bp.route('/api/analytics/insights')
@login_required
def insights():
    """Generate insights and recommendations based on analytics data"""
    days = int(request.args.get('days', 30))
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    insights_list = []
    
    # Analyze time entries
    query = db.session.query(
        func.sum(TimeEntry.duration_seconds).label('total_seconds'),
        func.avg(TimeEntry.duration_seconds).label('avg_seconds'),
        func.count(TimeEntry.id).label('total_entries'),
        func.sum(func.case((TimeEntry.billable == True, TimeEntry.duration_seconds), else_=0)).label('billable_seconds')
    ).filter(
        TimeEntry.end_time.isnot(None),
        TimeEntry.start_time >= start_date,
        TimeEntry.start_time <= end_date
    )
    
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
            insights_list.append({
                'type': 'warning',
                'icon': 'fas fa-exclamation-triangle',
                'title': 'Low Billable Ratio',
                'message': f'Only {billable_ratio:.1f}% of your time is billable. Consider focusing on billable projects.'
            })
        elif billable_ratio > 85:
            insights_list.append({
                'type': 'success',
                'icon': 'fas fa-trophy',
                'title': 'Excellent Billable Ratio',
                'message': f'You have {billable_ratio:.1f}% billable time. Great work!'
            })
    
    # Insight 2: Average daily hours
    avg_daily = total_hours / days if days > 0 else 0
    if avg_daily < 4:
        insights_list.append({
            'type': 'info',
            'icon': 'fas fa-chart-line',
            'title': 'Low Activity',
            'message': f'Average of {avg_daily:.1f}h per day. Consider tracking more consistently.'
        })
    elif avg_daily > 10:
        insights_list.append({
            'type': 'warning',
            'icon': 'fas fa-battery-empty',
            'title': 'High Workload',
            'message': f'Averaging {avg_daily:.1f}h per day. Remember to take breaks!'
        })
    
    # Insight 3: Project diversity
    project_count = db.session.query(func.count(func.distinct(TimeEntry.project_id))).filter(
        TimeEntry.end_time.isnot(None),
        TimeEntry.start_time >= start_date,
        TimeEntry.start_time <= end_date
    )
    
    if not current_user.is_admin:
        project_count = project_count.filter(TimeEntry.user_id == current_user.id)
    
    num_projects = project_count.scalar() or 0
    
    if num_projects > 8:
        insights_list.append({
            'type': 'info',
            'icon': 'fas fa-tasks',
            'title': 'Multiple Projects',
            'message': f'Working on {num_projects} projects. Consider consolidating focus.'
        })
    
    # Insight 4: Weekend work (if any)
    weekend_query = db.session.query(
        func.sum(TimeEntry.duration_seconds).label('weekend_seconds')
    ).filter(
        TimeEntry.end_time.isnot(None),
        TimeEntry.start_time >= start_date,
        TimeEntry.start_time <= end_date,
        extract('dow', TimeEntry.start_time).in_([0, 6])  # Sunday=0, Saturday=6
    )
    
    if not current_user.is_admin:
        weekend_query = weekend_query.filter(TimeEntry.user_id == current_user.id)
    
    weekend_seconds = weekend_query.scalar() or 0
    weekend_hours = weekend_seconds / 3600
    
    if weekend_hours > 5:
        weekend_percent = (weekend_hours / total_hours * 100) if total_hours > 0 else 0
        insights_list.append({
            'type': 'warning',
            'icon': 'fas fa-calendar-times',
            'title': 'Weekend Work',
            'message': f'{weekend_percent:.0f}% of work done on weekends ({weekend_hours:.1f}h). Consider work-life balance.'
        })
    
    return jsonify({
        'insights': insights_list
    })
