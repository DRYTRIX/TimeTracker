from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Task, Project, User, TimeEntry
from datetime import datetime, date
from decimal import Decimal
from app.utils.db import safe_commit
from app.utils.timezone import now_in_app_timezone

tasks_bp = Blueprint('tasks', __name__)

@tasks_bp.route('/tasks')
@login_required
def list_tasks():
    """List all tasks with filtering options"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    priority = request.args.get('priority', '')
    project_id = request.args.get('project_id', type=int)
    assigned_to = request.args.get('assigned_to', type=int)
    search = request.args.get('search', '').strip()
    overdue_param = request.args.get('overdue', '').strip().lower()
    overdue = overdue_param in ['1', 'true', 'on', 'yes']
    
    query = Task.query
    
    # Apply filters
    if status:
        query = query.filter_by(status=status)
    
    if priority:
        query = query.filter_by(priority=priority)
    
    if project_id:
        query = query.filter_by(project_id=project_id)
    
    if assigned_to:
        query = query.filter_by(assigned_to=assigned_to)
    
    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                Task.name.ilike(like),
                Task.description.ilike(like)
            )
        )
    
    # Overdue filter (uses application's local date)
    if overdue:
        today_local = now_in_app_timezone().date()
        query = query.filter(
            Task.due_date < today_local,
            Task.status.in_(['todo', 'in_progress', 'review'])
        )
    
    # Show user's tasks first, then others
    if not current_user.is_admin:
        query = query.filter(
            db.or_(
                Task.assigned_to == current_user.id,
                Task.created_by == current_user.id
            )
        )
    
    tasks = query.order_by(Task.priority.desc(), Task.due_date.asc(), Task.created_at.asc()).paginate(
        page=page,
        per_page=20,
        error_out=False
    )
    
    # Get filter options
    projects = Project.query.filter_by(status='active').order_by(Project.name).all()
    users = User.query.order_by(User.username).all()
    
    return render_template(
        'tasks/list.html',
        tasks=tasks.items,
        pagination=tasks,
        projects=projects,
        users=users,
        status=status,
        priority=priority,
        project_id=project_id,
        assigned_to=assigned_to,
        search=search,
        overdue=overdue
    )

@tasks_bp.route('/tasks/create', methods=['GET', 'POST'])
@login_required
def create_task():
    """Create a new task"""
    if request.method == 'POST':
        project_id = request.form.get('project_id', type=int)
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        priority = request.form.get('priority', 'medium')
        estimated_hours = request.form.get('estimated_hours', '').strip()
        due_date_str = request.form.get('due_date', '').strip()
        assigned_to = request.form.get('assigned_to', type=int)
        
        # Validate required fields
        if not project_id or not name:
            flash('Project and task name are required', 'error')
            return render_template('tasks/create.html')
        
        # Validate project exists
        project = Project.query.get(project_id)
        if not project:
            flash('Selected project does not exist', 'error')
            return render_template('tasks/create.html')
        
        # Parse estimated hours
        try:
            estimated_hours = float(estimated_hours) if estimated_hours else None
        except ValueError:
            flash('Invalid estimated hours format', 'error')
            return render_template('tasks/create.html')
        
        # Parse due date
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid due date format', 'error')
                return render_template('tasks/create.html')
        
        # Create task
        task = Task(
            project_id=project_id,
            name=name,
            description=description,
            priority=priority,
            estimated_hours=estimated_hours,
            due_date=due_date,
            assigned_to=assigned_to,
            created_by=current_user.id
        )
        
        db.session.add(task)
        if not safe_commit('create_task', {'project_id': project_id, 'name': name}):
            flash('Could not create task due to a database error. Please check server logs.', 'error')
            return render_template('tasks/create.html')
        
        flash(f'Task "{name}" created successfully', 'success')
        return redirect(url_for('tasks.view_task', task_id=task.id))
    
    # Get available projects and users for form
    projects = Project.query.filter_by(status='active').order_by(Project.name).all()
    users = User.query.order_by(User.username).all()
    
    return render_template('tasks/create.html', projects=projects, users=users)

@tasks_bp.route('/tasks/<int:task_id>')
@login_required
def view_task(task_id):
    """View task details"""
    task = Task.query.get_or_404(task_id)
    
    # Check if user has access to this task
    if not current_user.is_admin and task.assigned_to != current_user.id and task.created_by != current_user.id:
        flash('You do not have access to this task', 'error')
        return redirect(url_for('tasks.list_tasks'))
    
    # Get time entries for this task
    time_entries = task.time_entries.order_by(TimeEntry.start_time.desc()).all()
    
    return render_template('tasks/view.html', task=task, time_entries=time_entries)

@tasks_bp.route('/tasks/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    """Edit task details"""
    task = Task.query.get_or_404(task_id)
    
    # Check if user can edit this task
    if not current_user.is_admin and task.created_by != current_user.id:
        flash('You can only edit tasks you created', 'error')
        return redirect(url_for('tasks.view_task', task_id=task.id))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        priority = request.form.get('priority', 'medium')
        estimated_hours = request.form.get('estimated_hours', '').strip()
        due_date_str = request.form.get('due_date', '').strip()
        assigned_to = request.form.get('assigned_to', type=int)
        
        # Validate required fields
        if not name:
            flash('Task name is required', 'error')
            return render_template('tasks/edit.html', task=task)
        
        # Parse estimated hours
        try:
            estimated_hours = float(estimated_hours) if estimated_hours else None
        except ValueError:
            flash('Invalid estimated hours format', 'error')
            return render_template('tasks/edit.html', task=task)
        
        # Parse due date
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid due date format', 'error')
                return render_template('tasks/edit.html', task=task)
        
        # Update task
        task.name = name
        task.description = description
        task.priority = priority
        task.estimated_hours = estimated_hours
        task.due_date = due_date
        task.assigned_to = assigned_to
        # Handle status update (including reopening from done)
        selected_status = request.form.get('status', '').strip()
        valid_statuses = ['todo', 'in_progress', 'review', 'done', 'cancelled']
        if selected_status and selected_status in valid_statuses and selected_status != task.status:
            try:
                if selected_status == 'in_progress':
                    task.start_task()
                elif selected_status == 'done':
                    task.complete_task()
                elif selected_status == 'cancelled':
                    task.cancel_task()
                else:
                    # Reopen or move to non-special states
                    # Clear completed_at if reopening from done
                    if task.status == 'done' and selected_status in ['todo', 'in_progress', 'review']:
                        task.completed_at = None
                    task.status = selected_status
                    task.updated_at = now_in_app_timezone()
                    if not safe_commit('edit_task_status_change', {'task_id': task.id, 'status': selected_status}):
                        flash('Could not update status due to a database error. Please check server logs.', 'error')
                        return render_template('tasks/edit.html', task=task)
            except ValueError as e:
                flash(str(e), 'error')
                return render_template('tasks/edit.html', task=task)

        # Always update the updated_at timestamp to local time after edits
        task.updated_at = now_in_app_timezone()
        
        if not safe_commit('edit_task', {'task_id': task.id}):
            flash('Could not update task due to a database error. Please check server logs.', 'error')
            return render_template('tasks/edit.html', task=task)
        
        flash(f'Task "{name}" updated successfully', 'success')
        return redirect(url_for('tasks.view_task', task_id=task.id))
    
    # Get available projects and users for form
    projects = Project.query.filter_by(status='active').order_by(Project.name).all()
    users = User.query.order_by(User.username).all()
    
    return render_template('tasks/edit.html', task=task, projects=projects, users=users)

@tasks_bp.route('/tasks/<int:task_id>/status', methods=['POST'])
@login_required
def update_task_status(task_id):
    """Update task status"""
    task = Task.query.get_or_404(task_id)
    new_status = request.form.get('status', '').strip()
    
    # Check if user can update this task
    if not current_user.is_admin and task.assigned_to != current_user.id and task.created_by != current_user.id:
        flash('You do not have permission to update this task', 'error')
        return redirect(url_for('tasks.view_task', task_id=task.id))
    
    # Validate status
    valid_statuses = ['todo', 'in_progress', 'review', 'done', 'cancelled']
    if new_status not in valid_statuses:
        flash('Invalid status', 'error')
        return redirect(url_for('tasks.view_task', task_id=task.id))
    
    # Update status
    try:
        if new_status == 'in_progress':
            # If reopening from done, bypass start_task restriction
            if task.status == 'done':
                task.completed_at = None
                task.status = 'in_progress'
                # Preserve existing started_at if present, otherwise set now
                if not task.started_at:
                    task.started_at = now_in_app_timezone()
                task.updated_at = now_in_app_timezone()
                if not safe_commit('update_task_status_reopen_in_progress', {'task_id': task.id, 'status': new_status}):
                    flash('Could not update status due to a database error. Please check server logs.', 'error')
                    return redirect(url_for('tasks.view_task', task_id=task.id))
            else:
                task.start_task()
        elif new_status == 'done':
            task.complete_task()
        elif new_status == 'cancelled':
            task.cancel_task()
        else:
            # For other transitions, handle reopening from done and local timestamps
            if task.status == 'done' and new_status in ['todo', 'review']:
                task.completed_at = None
            task.status = new_status
            task.updated_at = now_in_app_timezone()
            if not safe_commit('update_task_status', {'task_id': task.id, 'status': new_status}):
                flash('Could not update status due to a database error. Please check server logs.', 'error')
                return redirect(url_for('tasks.view_task', task_id=task.id))
        
        flash(f'Task status updated to {task.status_display}', 'success')
    except ValueError as e:
        flash(str(e), 'error')
    
    return redirect(url_for('tasks.view_task', task_id=task.id))

@tasks_bp.route('/tasks/<int:task_id>/priority', methods=['POST'])
@login_required
def update_task_priority(task_id):
    """Update task priority"""
    task = Task.query.get_or_404(task_id)
    new_priority = request.form.get('priority', '').strip()
    
    # Check if user can update this task
    if not current_user.is_admin and task.created_by != current_user.id:
        flash('You can only update tasks you created', 'error')
        return redirect(url_for('tasks.view_task', task_id=task.id))
    
    try:
        task.update_priority(new_priority)
        flash(f'Task priority updated to {task.priority_display}', 'success')
    except ValueError as e:
        flash(str(e), 'error')
    
    return redirect(url_for('tasks.view_task', task_id=task.id))

@tasks_bp.route('/tasks/<int:task_id>/assign', methods=['POST'])
@login_required
def assign_task(task_id):
    """Assign task to a user"""
    task = Task.query.get_or_404(task_id)
    user_id = request.form.get('user_id', type=int)
    
    # Check if user can assign this task
    if not current_user.is_admin and task.created_by != current_user.id:
        flash('You can only assign tasks you created', 'error')
        return redirect(url_for('tasks.view_task', task_id=task.id))
    
    if user_id:
        user = User.query.get(user_id)
        if not user:
            flash('Selected user does not exist', 'error')
            return redirect(url_for('tasks.view_task', task_id=task.id))
    
    task.reassign(user_id)
    if user_id:
        flash(f'Task assigned to {user.username}', 'success')
    else:
        flash('Task unassigned', 'success')
    
    return redirect(url_for('tasks.view_task', task_id=task.id))

@tasks_bp.route('/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    """Delete a task"""
    task = Task.query.get_or_404(task_id)
    
    # Check if user can delete this task
    if not current_user.is_admin and task.created_by != current_user.id:
        flash('You can only delete tasks you created', 'error')
        return redirect(url_for('tasks.view_task', task_id=task.id))
    
    # Check if task has time entries
    if task.time_entries.count() > 0:
        flash('Cannot delete task with existing time entries', 'error')
        return redirect(url_for('tasks.view_task', task_id=task.id))
    
    task_name = task.name
    db.session.delete(task)
    if not safe_commit('delete_task', {'task_id': task.id}):
        flash('Could not delete task due to a database error. Please check server logs.', 'error')
        return redirect(url_for('tasks.view_task', task_id=task.id))
    
    flash(f'Task "{task_name}" deleted successfully', 'success')
    return redirect(url_for('tasks.list_tasks'))

@tasks_bp.route('/tasks/my-tasks')
@login_required
def my_tasks():
    """Show current user's tasks with filters and pagination"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    priority = request.args.get('priority', '')
    project_id = request.args.get('project_id', type=int)
    search = request.args.get('search', '').strip()
    task_type = request.args.get('task_type', '')  # '', 'assigned', 'created'
    overdue_param = request.args.get('overdue', '').strip().lower()
    overdue = overdue_param in ['1', 'true', 'on', 'yes']

    query = Task.query

    # Restrict to current user's tasks depending on task_type filter
    if task_type == 'assigned':
        query = query.filter(Task.assigned_to == current_user.id)
    elif task_type == 'created':
        query = query.filter(Task.created_by == current_user.id)
    else:
        query = query.filter(
            db.or_(
                Task.assigned_to == current_user.id,
                Task.created_by == current_user.id
            )
        )

    # Apply filters
    if status:
        query = query.filter_by(status=status)

    if priority:
        query = query.filter_by(priority=priority)

    if project_id:
        query = query.filter_by(project_id=project_id)

    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                Task.name.ilike(like),
                Task.description.ilike(like)
            )
        )

    # Overdue filter (uses application's local date)
    if overdue:
        today_local = now_in_app_timezone().date()
        query = query.filter(
            Task.due_date < today_local,
            Task.status.in_(['todo', 'in_progress', 'review'])
        )

    tasks = query.order_by(
        Task.priority.desc(),
        Task.due_date.asc(),
        Task.created_at.asc()
    ).paginate(page=page, per_page=20, error_out=False)

    # Provide projects for filter dropdown
    projects = Project.query.filter_by(status='active').order_by(Project.name).all()

    return render_template(
        'tasks/my_tasks.html',
        tasks=tasks.items,
        pagination=tasks,
        projects=projects,
        status=status,
        priority=priority,
        project_id=project_id,
        search=search,
        task_type=task_type,
        overdue=overdue
    )

@tasks_bp.route('/tasks/overdue')
@login_required
def overdue_tasks():
    """Show all overdue tasks"""
    if not current_user.is_admin:
        flash('Only administrators can view all overdue tasks', 'error')
        return redirect(url_for('tasks.list_tasks'))
    
    tasks = Task.get_overdue_tasks()
    
    return render_template('tasks/overdue.html', tasks=tasks)

@tasks_bp.route('/api/tasks/<int:task_id>')
@login_required
def api_task(task_id):
    """API endpoint to get task details"""
    task = Task.query.get_or_404(task_id)
    
    # Check if user has access to this task
    if not current_user.is_admin and task.assigned_to != current_user.id and task.created_by != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    return jsonify(task.to_dict())

@tasks_bp.route('/api/tasks/<int:task_id>/status', methods=['PUT'])
@login_required
def api_update_status(task_id):
    """API endpoint to update task status"""
    task = Task.query.get_or_404(task_id)
    data = request.get_json()
    new_status = data.get('status', '').strip()
    
    # Check if user can update this task
    if not current_user.is_admin and task.assigned_to != current_user.id and task.created_by != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    # Validate status
    valid_statuses = ['todo', 'in_progress', 'review', 'done', 'cancelled']
    if new_status not in valid_statuses:
        return jsonify({'error': 'Invalid status'}), 400
    
    # Update status
    try:
        if new_status == 'in_progress':
            if task.status == 'done':
                task.completed_at = None
                task.status = 'in_progress'
                if not task.started_at:
                    task.started_at = now_in_app_timezone()
                task.updated_at = now_in_app_timezone()
                if not safe_commit('api_update_task_status_reopen_in_progress', {'task_id': task.id, 'status': new_status}):
                    return jsonify({'error': 'Database error while updating status'}), 500
            else:
                task.start_task()
        elif new_status == 'done':
            task.complete_task()
        elif new_status == 'cancelled':
            task.cancel_task()
        else:
            if task.status == 'done' and new_status in ['todo', 'review']:
                task.completed_at = None
            task.status = new_status
            task.updated_at = now_in_app_timezone()
            if not safe_commit('api_update_task_status', {'task_id': task.id, 'status': new_status}):
                return jsonify({'error': 'Database error while updating status'}), 500
        
        return jsonify({'success': True, 'task': task.to_dict()})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
