from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db, socketio, log_event, track_event
from app.models import User, Project, TimeEntry, Task, Settings
from app.utils.timezone import parse_local_datetime, utc_to_local
from datetime import datetime
import json
from app.utils.db import safe_commit
from app.utils.posthog_funnels import (
    track_onboarding_first_timer,
    track_onboarding_first_time_entry
)

timer_bp = Blueprint('timer', __name__)

@timer_bp.route('/timer/start', methods=['POST'])
@login_required
def start_timer():
    """Start a new timer for the current user"""
    project_id = request.form.get('project_id', type=int)
    task_id = request.form.get('task_id', type=int)
    notes = request.form.get('notes', '').strip()
    current_app.logger.info("POST /timer/start user=%s project_id=%s task_id=%s", current_user.username, project_id, task_id)
    
    if not project_id:
        flash('Project is required', 'error')
        current_app.logger.warning("Start timer failed: missing project_id")
        return redirect(url_for('main.dashboard'))
    
    # Check if project exists and is active
    project = Project.query.filter_by(id=project_id, status='active').first()
    if not project:
        flash('Invalid project selected', 'error')
        current_app.logger.warning("Start timer failed: invalid or inactive project_id=%s", project_id)
        return redirect(url_for('main.dashboard'))
    
    # If a task is provided, validate it belongs to the project
    if task_id:
        task = Task.query.filter_by(id=task_id, project_id=project_id).first()
        if not task:
            flash('Selected task is invalid for the chosen project', 'error')
            current_app.logger.warning("Start timer failed: task_id=%s does not belong to project_id=%s", task_id, project_id)
            return redirect(url_for('main.dashboard'))
    else:
        task = None
    
    # Check if user already has an active timer
    active_timer = current_user.active_timer
    if active_timer:
        flash('You already have an active timer. Stop it before starting a new one.', 'error')
        current_app.logger.info("Start timer blocked: user already has an active timer")
        return redirect(url_for('main.dashboard'))
    
    # Create new timer
    from app.models.time_entry import local_now
    new_timer = TimeEntry(
        user_id=current_user.id,
        project_id=project_id,
        task_id=task.id if task else None,
        start_time=local_now(),
        notes=notes if notes else None,
        source='auto'
    )
    
    db.session.add(new_timer)
    if not safe_commit('start_timer', {'user_id': current_user.id, 'project_id': project_id, 'task_id': task_id}):
        flash('Could not start timer due to a database error. Please check server logs.', 'error')
        return redirect(url_for('main.dashboard'))
    current_app.logger.info("Started new timer id=%s for user=%s project_id=%s task_id=%s", new_timer.id, current_user.username, project_id, task_id)
    
    # Track timer started event
    log_event("timer.started", user_id=current_user.id, project_id=project_id, task_id=task_id, description=notes)
    track_event(current_user.id, "timer.started", {
        "project_id": project_id,
        "task_id": task_id,
        "has_description": bool(notes)
    })
    
    # Check if this is user's first timer (onboarding milestone)
    timer_count = TimeEntry.query.filter_by(
        user_id=current_user.id,
        source='auto'
    ).count()
    
    if timer_count == 1:  # First timer ever
        track_onboarding_first_timer(current_user.id, {
            "project_id": project_id,
            "has_task": bool(task_id),
            "has_notes": bool(notes)
        })
    
    # Emit WebSocket event for real-time updates
    try:
        payload = {
            'user_id': current_user.id,
            'timer_id': new_timer.id,
            'project_name': project.name,
            'start_time': new_timer.start_time.isoformat()
        }
        if task:
            payload['task_id'] = task.id
            payload['task_name'] = task.name
        socketio.emit('timer_started', payload)
    except Exception as e:
        current_app.logger.warning("Socket emit failed for timer_started: %s", e)
    
    if task:
        flash(f'Timer started for {project.name} - {task.name}', 'success')
    else:
        flash(f'Timer started for {project.name}', 'success')
    return redirect(url_for('main.dashboard'))

@timer_bp.route('/timer/start/<int:project_id>')
@login_required
def start_timer_for_project(project_id):
    """Start a timer for a specific project (GET route for direct links)"""
    task_id = request.args.get('task_id', type=int)
    current_app.logger.info("GET /timer/start/%s user=%s task_id=%s", project_id, current_user.username, task_id)
    
    # Check if project exists and is active
    project = Project.query.filter_by(id=project_id, status='active').first()
    if not project:
        flash('Invalid project selected', 'error')
        current_app.logger.warning("Start timer (GET) failed: invalid or inactive project_id=%s", project_id)
        return redirect(url_for('main.dashboard'))
    
    # Check if user already has an active timer
    active_timer = current_user.active_timer
    if active_timer:
        flash('You already have an active timer. Stop it before starting a new one.', 'error')
        current_app.logger.info("Start timer (GET) blocked: user already has an active timer")
        return redirect(url_for('main.dashboard'))
    
    # Create new timer
    from app.models.time_entry import local_now
    new_timer = TimeEntry(
        user_id=current_user.id,
        project_id=project_id,
        task_id=task_id,
        start_time=local_now(),
        source='auto'
    )
    
    db.session.add(new_timer)
    if not safe_commit('start_timer_for_project', {'user_id': current_user.id, 'project_id': project_id, 'task_id': task_id}):
        flash('Could not start timer due to a database error. Please check server logs.', 'error')
        return redirect(url_for('main.dashboard'))
    current_app.logger.info("Started new timer id=%s for user=%s project_id=%s task_id=%s", new_timer.id, current_user.username, project_id, task_id)
    
    # Emit WebSocket event for real-time updates
    try:
        socketio.emit('timer_started', {
            'user_id': current_user.id,
            'timer_id': new_timer.id,
            'project_name': project.name,
            'task_id': task_id,
            'start_time': new_timer.start_time.isoformat()
        })
    except Exception as e:
        current_app.logger.warning("Socket emit failed for timer_started (GET): %s", e)
    
    if task_id:
        task = Task.query.get(task_id)
        task_name = task.name if task else "Unknown Task"
        flash(f'Timer started for {project.name} - {task_name}', 'success')
    else:
        flash(f'Timer started for {project.name}', 'success')
    
    return redirect(url_for('main.dashboard'))

@timer_bp.route('/timer/stop', methods=['POST'])
@login_required
def stop_timer():
    """Stop the current user's active timer"""
    active_timer = current_user.active_timer
    current_app.logger.info("POST /timer/stop user=%s active_timer=%s", current_user.username, bool(active_timer))
    
    if not active_timer:
        flash('No active timer to stop', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Stop the timer
    try:
        active_timer.stop_timer()
        current_app.logger.info("Stopped timer id=%s for user=%s", active_timer.id, current_user.username)
        
        # Track timer stopped event
        duration_seconds = active_timer.duration if hasattr(active_timer, 'duration') else 0
        log_event("timer.stopped", 
                 user_id=current_user.id, 
                 time_entry_id=active_timer.id,
                 project_id=active_timer.project_id,
                 task_id=active_timer.task_id,
                 duration_seconds=duration_seconds)
        track_event(current_user.id, "timer.stopped", {
            "time_entry_id": active_timer.id,
            "project_id": active_timer.project_id,
            "task_id": active_timer.task_id,
            "duration_seconds": duration_seconds
        })
        
        # Check if this is user's first completed time entry (onboarding milestone)
        entry_count = TimeEntry.query.filter_by(
            user_id=current_user.id
        ).filter(
            TimeEntry.end_time.isnot(None)
        ).count()
        
        if entry_count == 1:  # First completed time entry ever
            track_onboarding_first_time_entry(current_user.id, {
                "source": "timer",
                "duration_seconds": duration_seconds,
                "has_task": bool(active_timer.task_id)
            })
    except Exception as e:
        current_app.logger.exception("Error stopping timer: %s", e)
    
    # Emit WebSocket event for real-time updates
    try:
        socketio.emit('timer_stopped', {
            'user_id': current_user.id,
            'timer_id': active_timer.id,
            'duration': active_timer.duration_formatted
        })
    except Exception as e:
        current_app.logger.warning("Socket emit failed for timer_stopped: %s", e)
    
    flash(f'Timer stopped. Duration: {active_timer.duration_formatted}', 'success')
    return redirect(url_for('main.dashboard'))

@timer_bp.route('/timer/status')
@login_required
def timer_status():
    """Get current timer status as JSON"""
    active_timer = current_user.active_timer
    
    if not active_timer:
        return jsonify({
            'active': False,
            'timer': None
        })
    
    return jsonify({
        'active': True,
        'timer': {
            'id': active_timer.id,
            'project_name': active_timer.project.name,
            'start_time': active_timer.start_time.isoformat(),
            'current_duration': active_timer.current_duration_seconds,
            'duration_formatted': active_timer.duration_formatted
        }
    })

@timer_bp.route('/timer/edit/<int:timer_id>', methods=['GET', 'POST'])
@login_required
def edit_timer(timer_id):
    """Edit a completed timer entry"""
    timer = TimeEntry.query.get_or_404(timer_id)
    
    # Check if user can edit this timer
    if timer.user_id != current_user.id and not current_user.is_admin:
        flash('You can only edit your own timers', 'error')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        # Update timer details
        timer.notes = request.form.get('notes', '').strip()
        timer.tags = request.form.get('tags', '').strip()
        timer.billable = request.form.get('billable') == 'on'
        
        # Admin users can edit additional fields
        if current_user.is_admin:
            # Update project if changed
            new_project_id = request.form.get('project_id', type=int)
            if new_project_id and new_project_id != timer.project_id:
                new_project = Project.query.filter_by(id=new_project_id, status='active').first()
                if new_project:
                    timer.project_id = new_project_id
                else:
                    flash('Invalid project selected', 'error')
                    return render_template('timer/edit_timer.html', timer=timer, 
                                        projects=Project.query.filter_by(status='active').order_by(Project.name).all(),
                                        tasks=[] if not new_project_id else Task.query.filter_by(project_id=new_project_id).order_by(Task.name).all())
            
            # Update task if changed
            new_task_id = request.form.get('task_id', type=int)
            if new_task_id != timer.task_id:
                if new_task_id:
                    new_task = Task.query.filter_by(id=new_task_id, project_id=timer.project_id).first()
                    if new_task:
                        timer.task_id = new_task_id
                    else:
                        flash('Invalid task selected for the chosen project', 'error')
                        return render_template('timer/edit_timer.html', timer=timer, 
                                            projects=Project.query.filter_by(status='active').order_by(Project.name).all(),
                                            tasks=Task.query.filter_by(project_id=timer.project_id).order_by(Task.name).all())
                else:
                    timer.task_id = None
            
            # Update start and end times if provided
            start_date = request.form.get('start_date')
            start_time = request.form.get('start_time')
            end_date = request.form.get('end_date')
            end_time = request.form.get('end_time')
            
            if start_date and start_time:
                try:
                    # Convert parsed UTC-aware to local naive to match model storage
                    parsed_start_utc = parse_local_datetime(start_date, start_time)
                    new_start_time = utc_to_local(parsed_start_utc).replace(tzinfo=None)
                    
                    # Validate that start time is not in the future
                    from app.models.time_entry import local_now
                    current_time = local_now()
                    if new_start_time > current_time:
                        flash('Start time cannot be in the future', 'error')
                        return render_template('timer/edit_timer.html', timer=timer, 
                                            projects=Project.query.filter_by(status='active').order_by(Project.name).all(),
                                            tasks=Task.query.filter_by(project_id=timer.project_id).order_by(Task.name).all())
                    
                    timer.start_time = new_start_time
                except ValueError:
                    flash('Invalid start date/time format', 'error')
                    return render_template('timer/edit_timer.html', timer=timer, 
                                        projects=Project.query.filter_by(status='active').order_by(Project.name).all(),
                                        tasks=Task.query.filter_by(project_id=timer.project_id).order_by(Task.name).all())
            
            if end_date and end_time:
                try:
                    # Convert parsed UTC-aware to local naive to match model storage
                    parsed_end_utc = parse_local_datetime(end_date, end_time)
                    new_end_time = utc_to_local(parsed_end_utc).replace(tzinfo=None)
                    
                    # Validate that end time is after start time
                    if new_end_time <= timer.start_time:
                        flash('End time must be after start time', 'error')
                        return render_template('timer/edit_timer.html', timer=timer, 
                                            projects=Project.query.filter_by(status='active').order_by(Project.name).all(),
                                            tasks=Task.query.filter_by(project_id=timer.project_id).order_by(Task.name).all())
                    
                    timer.end_time = new_end_time
                    # Recalculate duration
                    timer.calculate_duration()
                except ValueError:
                    flash('Invalid end date/time format', 'error')
                    return render_template('timer/edit_timer.html', timer=timer, 
                                        projects=Project.query.filter_by(status='active').order_by(Project.name).all(),
                                        tasks=Task.query.filter_by(project_id=timer.project_id).order_by(Task.name).all())
            
            # Update source if provided
            new_source = request.form.get('source')
            if new_source in ['manual', 'auto']:
                timer.source = new_source
        
        if not safe_commit('edit_timer', {'timer_id': timer.id}):
            flash('Could not update timer due to a database error. Please check server logs.', 'error')
            return redirect(url_for('main.dashboard'))
        
        flash('Timer updated successfully', 'success')
        return redirect(url_for('main.dashboard'))
    
    # Get projects and tasks for admin users
    projects = []
    tasks = []
    if current_user.is_admin:
        projects = Project.query.filter_by(status='active').order_by(Project.name).all()
        if timer.project_id:
            tasks = Task.query.filter_by(project_id=timer.project_id).order_by(Task.name).all()
    
    return render_template('timer/edit_timer.html', timer=timer, projects=projects, tasks=tasks)

@timer_bp.route('/timer/delete/<int:timer_id>', methods=['POST'])
@login_required
def delete_timer(timer_id):
    """Delete a timer entry"""
    timer = TimeEntry.query.get_or_404(timer_id)
    
    # Check if user can delete this timer
    if timer.user_id != current_user.id and not current_user.is_admin:
        flash('You can only delete your own timers', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Don't allow deletion of active timers
    if timer.is_active:
        flash('Cannot delete an active timer', 'error')
        return redirect(url_for('main.dashboard'))
    
    project_name = timer.project.name
    db.session.delete(timer)
    if not safe_commit('delete_timer', {'timer_id': timer.id}):
        flash('Could not delete timer due to a database error. Please check server logs.', 'error')
        return redirect(url_for('main.dashboard'))
    
    flash(f'Timer for {project_name} deleted successfully', 'success')
    return redirect(url_for('main.dashboard'))

@timer_bp.route('/timer/manual', methods=['GET', 'POST'])
@login_required
def manual_entry():
    """Create a manual time entry"""
    # Get active projects for dropdown (used for both GET and error re-renders on POST)
    active_projects = Project.query.filter_by(status='active').order_by(Project.name).all()
    
    # Get project_id and task_id from query parameters for pre-filling
    project_id = request.args.get('project_id', type=int)
    task_id = request.args.get('task_id', type=int)
    
    if request.method == 'POST':
        project_id = request.form.get('project_id', type=int)
        task_id = request.form.get('task_id', type=int)
        start_date = request.form.get('start_date')
        start_time = request.form.get('start_time')
        end_date = request.form.get('end_date')
        end_time = request.form.get('end_time')
        notes = request.form.get('notes', '').strip()
        tags = request.form.get('tags', '').strip()
        billable = request.form.get('billable') == 'on'
        
        # Validate required fields
        if not all([project_id, start_date, start_time, end_date, end_time]):
            flash('All fields are required', 'error')
            return render_template('timer/manual_entry.html', projects=active_projects, 
                                selected_project_id=project_id, selected_task_id=task_id)
        
        # Check if project exists and is active
        project = Project.query.filter_by(id=project_id, status='active').first()
        if not project:
            flash('Invalid project selected', 'error')
            return render_template('timer/manual_entry.html', projects=active_projects,
                                selected_project_id=project_id, selected_task_id=task_id)
        
        # Validate task if provided
        if task_id:
            task = Task.query.filter_by(id=task_id, project_id=project_id).first()
            if not task:
                flash('Invalid task selected', 'error')
                return render_template('timer/manual_entry.html', projects=active_projects,
                                    selected_project_id=project_id, selected_task_id=task_id)
        
        # Parse datetime with timezone awareness
        try:
            start_time_parsed = parse_local_datetime(start_date, start_time)
            end_time_parsed = parse_local_datetime(end_date, end_time)
        except ValueError:
            flash('Invalid date/time format', 'error')
            return render_template('timer/manual_entry.html', projects=active_projects,
                                selected_project_id=project_id, selected_task_id=task_id)
        
        # Validate time range
        if end_time_parsed <= start_time_parsed:
            flash('End time must be after start time', 'error')
            return render_template('timer/manual_entry.html', projects=active_projects,
                                selected_project_id=project_id, selected_task_id=task_id)
        
        # Create manual entry
        entry = TimeEntry(
            user_id=current_user.id,
            project_id=project_id,
            task_id=task_id,
            start_time=start_time_parsed,
            end_time=end_time_parsed,
            notes=notes,
            tags=tags,
            source='manual',
            billable=billable
        )
        
        db.session.add(entry)
        if not safe_commit('manual_entry', {'user_id': current_user.id, 'project_id': project_id, 'task_id': task_id}):
            flash('Could not create manual entry due to a database error. Please check server logs.', 'error')
            return render_template('timer/manual_entry.html', projects=active_projects, 
                                selected_project_id=project_id, selected_task_id=task_id)
        
        if task_id:
            task = Task.query.get(task_id)
            task_name = task.name if task else "Unknown Task"
            flash(f'Manual entry created for {project.name} - {task_name}', 'success')
        else:
            flash(f'Manual entry created for {project.name}', 'success')
        
        return redirect(url_for('main.dashboard'))
    
    return render_template('timer/manual_entry.html', projects=active_projects, 
                         selected_project_id=project_id, selected_task_id=task_id)

@timer_bp.route('/timer/manual/<int:project_id>')
@login_required
def manual_entry_for_project(project_id):
    """Create a manual time entry for a specific project"""
    task_id = request.args.get('task_id', type=int)
    
    # Check if project exists and is active
    project = Project.query.filter_by(id=project_id, status='active').first()
    if not project:
        flash('Invalid project selected', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get active projects for dropdown
    active_projects = Project.query.filter_by(status='active').order_by(Project.name).all()
    
    return render_template('timer/manual_entry.html', projects=active_projects, 
                         selected_project_id=project_id, selected_task_id=task_id)

@timer_bp.route('/timer/bulk', methods=['GET', 'POST'])
@login_required
def bulk_entry():
    """Create bulk time entries for multiple days"""
    # Get active projects for dropdown
    active_projects = Project.query.filter_by(status='active').order_by(Project.name).all()
    
    # Get project_id and task_id from query parameters for pre-filling
    project_id = request.args.get('project_id', type=int)
    task_id = request.args.get('task_id', type=int)
    
    if request.method == 'POST':
        project_id = request.form.get('project_id', type=int)
        task_id = request.form.get('task_id', type=int)
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        notes = request.form.get('notes', '').strip()
        tags = request.form.get('tags', '').strip()
        billable = request.form.get('billable') == 'on'
        skip_weekends = request.form.get('skip_weekends') == 'on'
        
        # Validate required fields
        if not all([project_id, start_date, end_date, start_time, end_time]):
            flash('All fields are required', 'error')
            return render_template('timer/bulk_entry.html', projects=active_projects, 
                                selected_project_id=project_id, selected_task_id=task_id)
        
        # Check if project exists and is active
        project = Project.query.filter_by(id=project_id, status='active').first()
        if not project:
            flash('Invalid project selected', 'error')
            return render_template('timer/bulk_entry.html', projects=active_projects,
                                selected_project_id=project_id, selected_task_id=task_id)
        
        # Validate task if provided
        if task_id:
            task = Task.query.filter_by(id=task_id, project_id=project_id).first()
            if not task:
                flash('Invalid task selected', 'error')
                return render_template('timer/bulk_entry.html', projects=active_projects,
                                    selected_project_id=project_id, selected_task_id=task_id)
        
        # Parse and validate dates
        try:
            from datetime import datetime, timedelta
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            if end_date_obj < start_date_obj:
                flash('End date must be after or equal to start date', 'error')
                return render_template('timer/bulk_entry.html', projects=active_projects,
                                    selected_project_id=project_id, selected_task_id=task_id)
            
            # Check for reasonable date range (max 31 days)
            if (end_date_obj - start_date_obj).days > 31:
                flash('Date range cannot exceed 31 days', 'error')
                return render_template('timer/bulk_entry.html', projects=active_projects,
                                    selected_project_id=project_id, selected_task_id=task_id)
        except ValueError:
            flash('Invalid date format', 'error')
            return render_template('timer/bulk_entry.html', projects=active_projects,
                                selected_project_id=project_id, selected_task_id=task_id)
        
        # Parse and validate times
        try:
            start_time_obj = datetime.strptime(start_time, '%H:%M').time()
            end_time_obj = datetime.strptime(end_time, '%H:%M').time()
            
            if end_time_obj <= start_time_obj:
                flash('End time must be after start time', 'error')
                return render_template('timer/bulk_entry.html', projects=active_projects,
                                    selected_project_id=project_id, selected_task_id=task_id)
        except ValueError:
            flash('Invalid time format', 'error')
            return render_template('timer/bulk_entry.html', projects=active_projects,
                                selected_project_id=project_id, selected_task_id=task_id)
        
        # Generate date range
        current_date = start_date_obj
        dates_to_create = []
        
        while current_date <= end_date_obj:
            # Skip weekends if requested
            if skip_weekends and current_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
                current_date += timedelta(days=1)
                continue
            
            dates_to_create.append(current_date)
            current_date += timedelta(days=1)
        
        if not dates_to_create:
            flash('No valid dates found in the selected range', 'error')
            return render_template('timer/bulk_entry.html', projects=active_projects,
                                selected_project_id=project_id, selected_task_id=task_id)
        
        # Check for existing entries on the same dates/times
        from app.models.time_entry import local_now
        existing_entries = []
        
        for date_obj in dates_to_create:
            start_datetime = datetime.combine(date_obj, start_time_obj)
            end_datetime = datetime.combine(date_obj, end_time_obj)
            
            # Check for overlapping entries
            overlapping = TimeEntry.query.filter(
                TimeEntry.user_id == current_user.id,
                TimeEntry.start_time <= end_datetime,
                TimeEntry.end_time >= start_datetime,
                TimeEntry.end_time.isnot(None)
            ).first()
            
            if overlapping:
                existing_entries.append(date_obj.strftime('%Y-%m-%d'))
        
        if existing_entries:
            flash(f'Time entries already exist for these dates: {", ".join(existing_entries[:5])}{"..." if len(existing_entries) > 5 else ""}', 'error')
            return render_template('timer/bulk_entry.html', projects=active_projects,
                                selected_project_id=project_id, selected_task_id=task_id)
        
        # Create bulk entries
        created_entries = []
        
        try:
            for date_obj in dates_to_create:
                start_datetime = datetime.combine(date_obj, start_time_obj)
                end_datetime = datetime.combine(date_obj, end_time_obj)
                
                entry = TimeEntry(
                    user_id=current_user.id,
                    project_id=project_id,
                    task_id=task_id,
                    start_time=start_datetime,
                    end_time=end_datetime,
                    notes=notes,
                    tags=tags,
                    source='manual',
                    billable=billable
                )
                
                db.session.add(entry)
                created_entries.append(entry)
            
            if not safe_commit('bulk_entry', {'user_id': current_user.id, 'project_id': project_id, 'count': len(created_entries)}):
                flash('Could not create bulk entries due to a database error. Please check server logs.', 'error')
                return render_template('timer/bulk_entry.html', projects=active_projects, 
                                    selected_project_id=project_id, selected_task_id=task_id)
            
            task_name = ""
            if task_id:
                task = Task.query.get(task_id)
                task_name = f" - {task.name}" if task else ""
            
            flash(f'Successfully created {len(created_entries)} time entries for {project.name}{task_name}', 'success')
            return redirect(url_for('main.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception("Error creating bulk entries: %s", e)
            flash('An error occurred while creating bulk entries. Please try again.', 'error')
            return render_template('timer/bulk_entry.html', projects=active_projects, 
                                selected_project_id=project_id, selected_task_id=task_id)
    
    return render_template('timer/bulk_entry.html', projects=active_projects, 
                         selected_project_id=project_id, selected_task_id=task_id)

@timer_bp.route('/timer/calendar')
@login_required
def calendar_view():
    """Calendar UI combining day/week/month with list toggle."""
    # Provide projects for quick assignment during drag-create
    active_projects = Project.query.filter_by(status='active').order_by(Project.name).all()
    return render_template('timer/calendar.html', projects=active_projects)

@timer_bp.route('/timer/bulk/<int:project_id>')
@login_required
def bulk_entry_for_project(project_id):
    """Create bulk time entries for a specific project"""
    task_id = request.args.get('task_id', type=int)
    
    # Check if project exists and is active
    project = Project.query.filter_by(id=project_id, status='active').first()
    if not project:
        flash('Invalid project selected', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get active projects for dropdown
    active_projects = Project.query.filter_by(status='active').order_by(Project.name).all()
    
    return render_template('timer/bulk_entry.html', projects=active_projects, 
                         selected_project_id=project_id, selected_task_id=task_id)

@timer_bp.route('/timer/duplicate/<int:timer_id>')
@login_required
def duplicate_timer(timer_id):
    """Duplicate an existing time entry - opens manual entry form with pre-filled data"""
    timer = TimeEntry.query.get_or_404(timer_id)
    
    # Check if user can duplicate this timer
    if timer.user_id != current_user.id and not current_user.is_admin:
        flash('You can only duplicate your own timers', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get active projects for dropdown
    active_projects = Project.query.filter_by(status='active').order_by(Project.name).all()
    
    # Track duplication event
    log_event("timer.duplicated", 
             user_id=current_user.id, 
             time_entry_id=timer.id,
             project_id=timer.project_id,
             task_id=timer.task_id)
    track_event(current_user.id, "timer.duplicated", {
        "time_entry_id": timer.id,
        "project_id": timer.project_id,
        "task_id": timer.task_id,
        "has_notes": bool(timer.notes),
        "has_tags": bool(timer.tags)
    })
    
    # Render the manual entry form with pre-filled data
    return render_template('timer/manual_entry.html', 
                         projects=active_projects,
                         selected_project_id=timer.project_id,
                         selected_task_id=timer.task_id,
                         prefill_notes=timer.notes,
                         prefill_tags=timer.tags,
                         prefill_billable=timer.billable,
                         is_duplicate=True,
                         original_entry=timer)
