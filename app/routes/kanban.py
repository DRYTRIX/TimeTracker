from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, make_response
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db, socketio
from app.models import KanbanColumn, Task
from app.utils.db import safe_commit
from app.routes.admin import admin_required

kanban_bp = Blueprint('kanban', __name__)
@kanban_bp.route('/kanban')
@login_required
def board():
    """Kanban board page with optional project filter"""
    project_id = request.args.get('project_id', type=int)
    query = Task.query
    if project_id:
        query = query.filter_by(project_id=project_id)
    # Order tasks for stable rendering
    tasks = query.order_by(Task.priority.desc(), Task.due_date.asc(), Task.created_at.asc()).all()
    # Fresh columns - use project-specific columns if project_id is provided
    db.session.expire_all()
    if KanbanColumn:
        # Try to get project-specific columns first
        columns = KanbanColumn.get_active_columns(project_id=project_id)
        # If no project-specific columns exist, fall back to global columns
        if not columns:
            columns = KanbanColumn.get_active_columns(project_id=None)
            # If still no global columns exist, initialize default global columns
            if not columns:
                KanbanColumn.initialize_default_columns(project_id=None)
                columns = KanbanColumn.get_active_columns(project_id=None)
    else:
        columns = []
    # Provide projects for filter dropdown
    from app.models import Project
    projects = Project.query.filter_by(status='active').order_by(Project.name).all()
    # No-cache
    response = render_template('kanban/board.html', tasks=tasks, kanban_columns=columns, projects=projects, project_id=project_id)
    resp = make_response(response)
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

@kanban_bp.route('/kanban/columns')
@login_required
@admin_required
def list_columns():
    """List kanban columns for management, optionally filtered by project"""
    project_id = request.args.get('project_id', type=int)
    # Force fresh data from database - clear all caches
    db.session.expire_all()
    columns = KanbanColumn.get_all_columns(project_id=project_id)
    
    # Get projects for filter dropdown
    from app.models import Project
    projects = Project.query.filter_by(status='active').order_by(Project.name).all()
    
    # Prevent browser caching
    response = render_template('kanban/columns.html', columns=columns, projects=projects, project_id=project_id)
    resp = make_response(response)
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

@kanban_bp.route('/kanban/columns/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_column():
    """Create a new kanban column"""
    project_id = request.args.get('project_id', type=int) or request.form.get('project_id', type=int)
    
    if request.method == 'POST':
        key = request.form.get('key', '').strip().lower().replace(' ', '_')
        label = request.form.get('label', '').strip()
        icon = request.form.get('icon', 'fas fa-circle').strip()
        color = request.form.get('color', 'secondary').strip()
        is_complete_state = request.form.get('is_complete_state') == 'on'
        project_id = request.form.get('project_id', type=int) or None
        
        # Validate required fields
        if not key or not label:
            flash('Key and label are required', 'error')
            from app.models import Project
            projects = Project.query.filter_by(status='active').order_by(Project.name).all()
            return render_template('kanban/create_column.html', projects=projects, project_id=project_id)
        
        # Check if key already exists for this project (or globally)
        existing = KanbanColumn.get_column_by_key(key, project_id=project_id)
        if existing:
            project_text = f" for this project" if project_id else " globally"
            flash(f'A column with key "{key}" already exists{project_text}', 'error')
            from app.models import Project
            projects = Project.query.filter_by(status='active').order_by(Project.name).all()
            return render_template('kanban/create_column.html', projects=projects, project_id=project_id)
        
        # Get max position for this project (or globally) and add 1
        query = db.session.query(db.func.max(KanbanColumn.position))
        if project_id is None:
            query = query.filter(KanbanColumn.project_id.is_(None))
        else:
            query = query.filter_by(project_id=project_id)
        max_position = query.scalar() or -1
        
        # Create column
        column = KanbanColumn(
            key=key,
            label=label,
            icon=icon,
            color=color,
            position=max_position + 1,
            is_complete_state=is_complete_state,
            is_system=False,
            is_active=True,
            project_id=project_id
        )
        
        db.session.add(column)
        
        # Explicitly flush to write to database immediately
        try:
            db.session.flush()
        except Exception as e:
            db.session.rollback()
            flash(f'Could not create column: {str(e)}', 'error')
            print(f"[KANBAN] Flush failed: {e}")
            from app.models import Project
            projects = Project.query.filter_by(status='active').order_by(Project.name).all()
            return render_template('kanban/create_column.html', projects=projects, project_id=project_id)
        
        # Now commit the transaction
        if not safe_commit('create_kanban_column', {'key': key, 'project_id': project_id}):
            flash('Could not create column due to a database error. Please check server logs.', 'error')
            from app.models import Project
            projects = Project.query.filter_by(status='active').order_by(Project.name).all()
            return render_template('kanban/create_column.html', projects=projects, project_id=project_id)
        
        print(f"[KANBAN] Column '{key}' committed to database successfully")
        
        flash(f'Column "{label}" created successfully', 'success')
        # Clear any SQLAlchemy cache to ensure fresh data on next load
        db.session.expire_all()
        # Notify all connected clients to refresh kanban boards
        try:
            print(f"[KANBAN] Emitting kanban_columns_updated event: created column '{key}'")
            socketio.emit('kanban_columns_updated', {'action': 'created', 'column_key': key, 'project_id': project_id}, broadcast=True)
            print(f"[KANBAN] Event emitted successfully")
        except Exception as e:
            print(f"[KANBAN] Failed to emit event: {e}")
        
        redirect_url = url_for('kanban.list_columns')
        if project_id:
            redirect_url = url_for('kanban.list_columns', project_id=project_id)
        return redirect(redirect_url)
    
    from app.models import Project
    projects = Project.query.filter_by(status='active').order_by(Project.name).all()
    return render_template('kanban/create_column.html', projects=projects, project_id=project_id)

@kanban_bp.route('/kanban/columns/<int:column_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_column(column_id):
    """Edit an existing kanban column"""
    column = KanbanColumn.query.get_or_404(column_id)
    
    if request.method == 'POST':
        label = request.form.get('label', '').strip()
        icon = request.form.get('icon', 'fas fa-circle').strip()
        color = request.form.get('color', 'secondary').strip()
        is_complete_state = request.form.get('is_complete_state') == 'on'
        is_active = request.form.get('is_active') == 'on'
        
        # Validate required fields
        if not label:
            flash('Label is required', 'error')
            return render_template('kanban/edit_column.html', column=column)
        
        # Update column
        column.label = label
        column.icon = icon
        column.color = color
        column.is_complete_state = is_complete_state
        column.is_active = is_active
        
        # Explicitly flush to write changes immediately
        try:
            db.session.flush()
        except Exception as e:
            db.session.rollback()
            flash(f'Could not update column: {str(e)}', 'error')
            print(f"[KANBAN] Flush failed: {e}")
            return render_template('kanban/edit_column.html', column=column)
        
        # Now commit the transaction
        if not safe_commit('edit_kanban_column', {'column_id': column_id}):
            flash('Could not update column due to a database error. Please check server logs.', 'error')
            return render_template('kanban/edit_column.html', column=column)
        
        print(f"[KANBAN] Column {column_id} updated and committed to database successfully")
        
        flash(f'Column "{label}" updated successfully', 'success')
        # Clear any SQLAlchemy cache to ensure fresh data on next load
        db.session.expire_all()
        # Notify all connected clients to refresh kanban boards
        try:
            print(f"[KANBAN] Emitting kanban_columns_updated event: updated column ID {column_id}")
            socketio.emit('kanban_columns_updated', {'action': 'updated', 'column_id': column_id, 'project_id': column.project_id}, broadcast=True)
            print(f"[KANBAN] Event emitted successfully")
        except Exception as e:
            print(f"[KANBAN] Failed to emit event: {e}")
        
        redirect_url = url_for('kanban.list_columns')
        if column.project_id:
            redirect_url = url_for('kanban.list_columns', project_id=column.project_id)
        return redirect(redirect_url)
    
    return render_template('kanban/edit_column.html', column=column)

@kanban_bp.route('/kanban/columns/<int:column_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_column(column_id):
    """Delete a kanban column (only if not system and has no tasks)"""
    column = KanbanColumn.query.get_or_404(column_id)
    
    # Check if system column
    if column.is_system:
        flash('System columns cannot be deleted', 'error')
        redirect_url = url_for('kanban.list_columns')
        if column.project_id:
            redirect_url = url_for('kanban.list_columns', project_id=column.project_id)
        return redirect(redirect_url)
    
    # Check if column has tasks (filter by project if column is project-specific)
    task_query = Task.query.filter_by(status=column.key)
    if column.project_id:
        task_query = task_query.filter_by(project_id=column.project_id)
    task_count = task_query.count()
    if task_count > 0:
        flash(f'Cannot delete column with {task_count} task(s). Move or delete tasks first.', 'error')
        redirect_url = url_for('kanban.list_columns')
        if column.project_id:
            redirect_url = url_for('kanban.list_columns', project_id=column.project_id)
        return redirect(redirect_url)
    
    column_name = column.label
    project_id = column.project_id
    db.session.delete(column)
    
    # Explicitly flush to execute delete immediately
    try:
        db.session.flush()
    except Exception as e:
        db.session.rollback()
        flash(f'Could not delete column: {str(e)}', 'error')
        print(f"[KANBAN] Flush failed: {e}")
        redirect_url = url_for('kanban.list_columns')
        if project_id:
            redirect_url = url_for('kanban.list_columns', project_id=project_id)
        return redirect(redirect_url)
    
    # Now commit the transaction
    if not safe_commit('delete_kanban_column', {'column_id': column_id}):
        flash('Could not delete column due to a database error. Please check server logs.', 'error')
        redirect_url = url_for('kanban.list_columns')
        if project_id:
            redirect_url = url_for('kanban.list_columns', project_id=project_id)
        return redirect(redirect_url)
    
    print(f"[KANBAN] Column {column_id} deleted and committed to database successfully")
    
    flash(f'Column "{column_name}" deleted successfully', 'success')
    # Clear any SQLAlchemy cache to ensure fresh data on next load
    db.session.expire_all()
    # Notify all connected clients to refresh kanban boards
    try:
        print(f"[KANBAN] Emitting kanban_columns_updated event: deleted column ID {column_id}")
        socketio.emit('kanban_columns_updated', {'action': 'deleted', 'column_id': column_id, 'project_id': project_id}, broadcast=True)
        print(f"[KANBAN] Event emitted successfully")
    except Exception as e:
        print(f"[KANBAN] Failed to emit event: {e}")
    
    redirect_url = url_for('kanban.list_columns')
    if project_id:
        redirect_url = url_for('kanban.list_columns', project_id=project_id)
    return redirect(redirect_url)

@kanban_bp.route('/kanban/columns/<int:column_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_column(column_id):
    """Toggle column active status"""
    column = KanbanColumn.query.get_or_404(column_id)
    
    column.is_active = not column.is_active
    
    # Explicitly flush to write changes immediately
    try:
        db.session.flush()
    except Exception as e:
        db.session.rollback()
        flash(f'Could not toggle column: {str(e)}', 'error')
        print(f"[KANBAN] Flush failed: {e}")
        return redirect(url_for('kanban.list_columns'))
    
    # Now commit the transaction
    if not safe_commit('toggle_kanban_column', {'column_id': column_id}):
        flash('Could not toggle column due to a database error. Please check server logs.', 'error')
        return redirect(url_for('kanban.list_columns'))
    
    print(f"[KANBAN] Column {column_id} toggled and committed to database successfully")
    
    status = 'activated' if column.is_active else 'deactivated'
    flash(f'Column "{column.label}" {status} successfully', 'success')
    # Clear any SQLAlchemy cache to ensure fresh data on next load
    db.session.expire_all()
    # Notify all connected clients to refresh kanban boards
    try:
        print(f"[KANBAN] Emitting kanban_columns_updated event: toggled column ID {column_id}")
        socketio.emit('kanban_columns_updated', {'action': 'toggled', 'column_id': column_id, 'project_id': column.project_id}, broadcast=True)
        print(f"[KANBAN] Event emitted successfully")
    except Exception as e:
        print(f"[KANBAN] Failed to emit event: {e}")
    
    redirect_url = url_for('kanban.list_columns')
    if column.project_id:
        redirect_url = url_for('kanban.list_columns', project_id=column.project_id)
    return redirect(redirect_url)

@kanban_bp.route('/api/kanban/columns/reorder', methods=['POST'])
@login_required
@admin_required
def reorder_columns():
    """Reorder kanban columns via API"""
    data = request.get_json()
    column_ids = data.get('column_ids', [])
    project_id = data.get('project_id', None)
    
    if not column_ids:
        return jsonify({'error': 'No column IDs provided'}), 400
    
    try:
        # Reorder columns for the specified project (or globally if project_id is None)
        KanbanColumn.reorder_columns(column_ids, project_id=project_id)
        
        # Explicitly flush to write changes immediately
        db.session.flush()
        
        # Force database commit
        db.session.commit()
        
        print(f"[KANBAN] Columns reordered and committed to database successfully")
        
        # Clear all caches to force fresh reads
        db.session.expire_all()
        
        # Notify all connected clients to refresh kanban boards
        try:
            print(f"[KANBAN] Emitting kanban_columns_updated event: reordered columns")
            socketio.emit('kanban_columns_updated', {'action': 'reordered', 'project_id': project_id}, broadcast=True)
            print(f"[KANBAN] Event emitted successfully")
        except Exception as e:
            print(f"[KANBAN] Failed to emit event: {e}")
        
        return jsonify({'success': True, 'message': 'Columns reordered successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@kanban_bp.route('/api/kanban/columns')
@login_required
def api_list_columns():
    """API endpoint to get active kanban columns, optionally filtered by project"""
    project_id = request.args.get('project_id', type=int)
    # Force fresh data - no caching
    db.session.expire_all()
    if KanbanColumn:
        # Try to get project-specific columns first
        columns = KanbanColumn.get_active_columns(project_id=project_id)
        # If no project-specific columns exist, fall back to global columns
        if not columns:
            columns = KanbanColumn.get_active_columns(project_id=None)
            # If still no global columns exist, initialize default global columns
            if not columns:
                KanbanColumn.initialize_default_columns(project_id=None)
                columns = KanbanColumn.get_active_columns(project_id=None)
    else:
        columns = []
    response = jsonify({'columns': [col.to_dict() for col in columns]})
    # Add no-cache headers to avoid SW/browser caching
    try:
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    except Exception:
        pass
    return response

