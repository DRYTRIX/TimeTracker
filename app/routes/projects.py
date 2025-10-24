from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify, make_response
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db, log_event, track_event
from app.models import Project, TimeEntry, Task, Client, ProjectCost, KanbanColumn, ExtraGood, Activity, UserFavoriteProject
from datetime import datetime
from decimal import Decimal
from app.utils.db import safe_commit
from app.utils.permissions import admin_or_permission_required, permission_required
from app.utils.posthog_funnels import (
    track_onboarding_first_project,
    track_project_setup_started,
    track_project_setup_basic_info,
    track_project_setup_billing_configured,
    track_project_setup_completed
)

projects_bp = Blueprint('projects', __name__)

@projects_bp.route('/projects')
@login_required
def list_projects():
    """List all projects"""
    # Track page view
    from app import track_page_view
    track_page_view("projects_list")
    
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'active')
    client_name = request.args.get('client', '').strip()
    search = request.args.get('search', '').strip()
    favorites_only = request.args.get('favorites', '').lower() == 'true'
    
    query = Project.query
    
    # Filter by favorites if requested
    if favorites_only:
        # Join with user_favorite_projects table
        query = query.join(
            UserFavoriteProject,
            db.and_(
                UserFavoriteProject.project_id == Project.id,
                UserFavoriteProject.user_id == current_user.id
            )
        )
    
    # Filter by status (use Project.status to be explicit)
    if status == 'active':
        query = query.filter(Project.status == 'active')
    elif status == 'archived':
        query = query.filter(Project.status == 'archived')
    elif status == 'inactive':
        query = query.filter(Project.status == 'inactive')
    
    if client_name:
        query = query.join(Client).filter(Client.name == client_name)
    
    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                Project.name.ilike(like),
                Project.description.ilike(like)
            )
        )
    
    # Get all projects for the current page
    projects_pagination = query.order_by(Project.name).paginate(
        page=page,
        per_page=20,
        error_out=False
    )
    
    # Get user's favorite project IDs for quick lookup in template
    favorite_project_ids = {p.id for p in current_user.favorite_projects.all()}
    
    # Get clients for filter dropdown
    clients = Client.get_active_clients()
    client_list = [c.name for c in clients]
    
    return render_template(
        'projects/list.html',
        projects=projects_pagination.items,
        status=status,
        clients=client_list,
        favorite_project_ids=favorite_project_ids,
        favorites_only=favorites_only
    )

@projects_bp.route('/projects/create', methods=['GET', 'POST'])
@login_required
@admin_or_permission_required('create_projects')
def create_project():
    """Create a new project"""
    
    # Track project setup started when user opens the form
    if request.method == 'GET':
        track_project_setup_started(current_user.id)
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        client_id = request.form.get('client_id', '').strip()
        description = request.form.get('description', '').strip()
        billable = request.form.get('billable') == 'on'
        hourly_rate = request.form.get('hourly_rate', '').strip()
        billing_ref = request.form.get('billing_ref', '').strip()
        # Budgets
        budget_amount_raw = request.form.get('budget_amount', '').strip()
        budget_threshold_raw = request.form.get('budget_threshold_percent', '').strip()
        code = request.form.get('code', '').strip()
        try:
            current_app.logger.info(
                "POST /projects/create user=%s name=%s client_id=%s billable=%s",
                current_user.username,
                name or '<empty>',
                client_id or '<empty>',
                billable,
            )
        except Exception:
            pass
        
        # Validate required fields
        if not name or not client_id:
            flash('Project name and client are required', 'error')
            try:
                current_app.logger.warning("Validation failed: missing required fields for project creation")
            except Exception:
                pass
            return render_template('projects/create.html', clients=Client.get_active_clients())
        
        # Get client and validate
        client = Client.query.get(client_id)
        if not client:
            flash('Selected client not found', 'error')
            try:
                current_app.logger.warning("Validation failed: client not found (id=%s)", client_id)
            except Exception:
                pass
            return render_template('projects/create.html', clients=Client.get_active_clients())
        
        # Validate hourly rate
        try:
            hourly_rate = Decimal(hourly_rate) if hourly_rate else None
        except ValueError:
            flash('Invalid hourly rate format', 'error')
        # Validate budgets
        budget_amount = None
        budget_threshold_percent = None
        if budget_amount_raw:
            try:
                budget_amount = Decimal(budget_amount_raw)
                if budget_amount < 0:
                    raise ValueError('Budget cannot be negative')
            except Exception:
                flash('Invalid budget amount', 'error')
                return render_template('projects/create.html', clients=Client.get_active_clients())
        if budget_threshold_raw:
            try:
                budget_threshold_percent = int(budget_threshold_raw)
                if budget_threshold_percent < 0 or budget_threshold_percent > 100:
                    raise ValueError('Invalid threshold')
            except Exception:
                flash('Invalid budget threshold percent (0-100)', 'error')
                return render_template('projects/create.html', clients=Client.get_active_clients())
        
        # Check if project name already exists
        if Project.query.filter_by(name=name).first():
            flash('A project with this name already exists', 'error')
            try:
                current_app.logger.warning("Validation failed: duplicate project name '%s'", name)
            except Exception:
                pass
            return render_template('projects/create.html', clients=Client.get_active_clients())
        
        # Normalize code
        normalized_code = code.upper() if code else None

        # Validate code uniqueness if provided
        if normalized_code:
            existing_code = Project.query.filter(Project.code == normalized_code).first()
            if existing_code:
                flash(_('Project code already in use'), 'error')
                return render_template('projects/create.html', clients=Client.get_active_clients())

        # Create project
        project = Project(
            name=name,
            client_id=client_id,
            description=description,
            billable=billable,
            hourly_rate=hourly_rate,
            billing_ref=billing_ref,
            code=normalized_code,
            budget_amount=budget_amount,
            budget_threshold_percent=budget_threshold_percent or 80
        )
        
        db.session.add(project)
        if not safe_commit('create_project', {'name': name, 'client_id': client_id}):
            flash('Could not create project due to a database error. Please check server logs.', 'error')
            return render_template('projects/create.html', clients=Client.get_active_clients())
        
        # Track project created event
        log_event("project.created", 
                 user_id=current_user.id, 
                 project_id=project.id, 
                 project_name=name,
                 has_client=bool(client_id))
        track_event(current_user.id, "project.created", {
            "project_id": project.id,
            "project_name": name,
            "has_client": bool(client_id),
            "billable": billable
        })
        
        # Track project setup funnel steps
        track_project_setup_basic_info(current_user.id, {
            "has_description": bool(description),
            "has_code": bool(code),
            "billable": billable
        })
        
        if hourly_rate or billing_ref or budget_amount:
            track_project_setup_billing_configured(current_user.id, {
                "has_hourly_rate": bool(hourly_rate),
                "has_billing_ref": bool(billing_ref),
                "has_budget": bool(budget_amount)
            })
        
        track_project_setup_completed(current_user.id, {
            "project_id": project.id,
            "billable": billable,
            "has_budget": bool(budget_amount)
        })
        
        # Check if this is user's first project (onboarding milestone)
        # Count projects this user has created or has time entries for
        from sqlalchemy import func, or_
        project_count = db.session.query(func.count(Project.id.distinct())).join(
            TimeEntry, 
            TimeEntry.project_id == Project.id,
            isouter=True
        ).filter(
            or_(
                TimeEntry.user_id == current_user.id,
                Project.id == project.id  # Include the just-created project
            )
        ).scalar() or 0
        
        if project_count == 1:
            track_onboarding_first_project(current_user.id, {
                "project_name_length": len(name),
                "has_description": bool(description),
                "billable": billable,
                "has_budget": bool(budget_amount)
            })
        
        # Log activity
        Activity.log(
            user_id=current_user.id,
            action='created',
            entity_type='project',
            entity_id=project.id,
            entity_name=project.name,
            description=f'Created project "{project.name}" for {client.name}',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        flash(f'Project "{name}" created successfully', 'success')
        return redirect(url_for('projects.view_project', project_id=project.id))
    
    return render_template('projects/create.html', clients=Client.get_active_clients())

@projects_bp.route('/projects/<int:project_id>')
@login_required
def view_project(project_id):
    """View project details and time entries"""
    project = Project.query.get_or_404(project_id)
    
    # Get time entries for this project
    page = request.args.get('page', 1, type=int)
    entries_pagination = project.time_entries.filter(
        TimeEntry.end_time.isnot(None)
    ).order_by(
        TimeEntry.start_time.desc()
    ).paginate(
        page=page,
        per_page=50,
        error_out=False
    )
    
    # Get tasks for this project
    tasks = project.tasks.order_by(Task.priority.desc(), Task.due_date.asc(), Task.created_at.asc()).all()
    
    # Get user totals
    user_totals = project.get_user_totals()
    
    # Get comments for this project
    from app.models import Comment
    comments = Comment.get_project_comments(project_id, include_replies=True)
    
    # Get recent project costs (latest 5)
    recent_costs = ProjectCost.query.filter_by(project_id=project_id).order_by(
        ProjectCost.cost_date.desc()
    ).limit(5).all()
    
    # Get total cost count
    total_costs_count = ProjectCost.query.filter_by(project_id=project_id).count()
    
    # Get kanban columns - force fresh data
    db.session.expire_all()
    kanban_columns = KanbanColumn.get_active_columns() if KanbanColumn else []
    
    # Prevent browser caching of kanban board
    response = render_template('projects/view.html', 
                         project=project, 
                         entries=entries_pagination.items,
                         pagination=entries_pagination,
                         tasks=tasks,
                         user_totals=user_totals,
                         comments=comments,
                         recent_costs=recent_costs,
                         total_costs_count=total_costs_count,
                         kanban_columns=kanban_columns)
    resp = make_response(response)
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

@projects_bp.route('/projects/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_or_permission_required('edit_projects')
def edit_project(project_id):
    """Edit project details"""
    project = Project.query.get_or_404(project_id)
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        client_id = request.form.get('client_id', '').strip()
        description = request.form.get('description', '').strip()
        billable = request.form.get('billable') == 'on'
        hourly_rate = request.form.get('hourly_rate', '').strip()
        billing_ref = request.form.get('billing_ref', '').strip()
        code = request.form.get('code', '').strip()
        budget_amount_raw = request.form.get('budget_amount', '').strip()
        budget_threshold_raw = request.form.get('budget_threshold_percent', '').strip()
        
        # Validate required fields
        if not name or not client_id:
            flash('Project name and client are required', 'error')
            return render_template('projects/edit.html', project=project, clients=Client.get_active_clients())
        
        # Get client and validate
        client = Client.query.get(client_id)
        if not client:
            flash('Selected client not found', 'error')
            return render_template('projects/edit.html', project=project, clients=Client.get_active_clients())
        
        # Validate hourly rate
        try:
            hourly_rate = Decimal(hourly_rate) if hourly_rate else None
        except ValueError:
            flash('Invalid hourly rate format', 'error')
            return render_template('projects/edit.html', project=project, clients=Client.get_active_clients())

        # Validate budgets
        budget_amount = None
        if budget_amount_raw:
            try:
                budget_amount = Decimal(budget_amount_raw)
                if budget_amount < 0:
                    raise ValueError('Budget cannot be negative')
            except Exception:
                flash('Invalid budget amount', 'error')
                return render_template('projects/edit.html', project=project, clients=Client.get_active_clients())
        budget_threshold_percent = project.budget_threshold_percent or 80
        if budget_threshold_raw:
            try:
                budget_threshold_percent = int(budget_threshold_raw)
                if budget_threshold_percent < 0 or budget_threshold_percent > 100:
                    raise ValueError('Invalid threshold')
            except Exception:
                flash('Invalid budget threshold percent (0-100)', 'error')
                return render_template('projects/edit.html', project=project, clients=Client.get_active_clients())
        
        # Check if project name already exists (excluding current project)
        existing = Project.query.filter_by(name=name).first()
        if existing and existing.id != project.id:
            flash('A project with this name already exists', 'error')
            return render_template('projects/edit.html', project=project, clients=Client.get_active_clients())

        # Validate code uniqueness if provided
        normalized_code = code.upper() if code else None
        if normalized_code:
            existing_code = Project.query.filter(Project.code == normalized_code).first()
            if existing_code and existing_code.id != project.id:
                flash(_('Project code already in use'), 'error')
                return render_template('projects/edit.html', project=project, clients=Client.get_active_clients())
        
        # Update project
        project.name = name
        project.client_id = client_id
        project.description = description
        project.billable = billable
        project.hourly_rate = hourly_rate
        project.billing_ref = billing_ref
        project.code = normalized_code
        project.budget_amount = budget_amount if budget_amount_raw != '' else None
        project.budget_threshold_percent = budget_threshold_percent
        project.updated_at = datetime.utcnow()
        
        if not safe_commit('edit_project', {'project_id': project.id}):
            flash('Could not update project due to a database error. Please check server logs.', 'error')
            return render_template('projects/edit.html', project=project, clients=Client.get_active_clients())
        
        flash(f'Project "{name}" updated successfully', 'success')
        return redirect(url_for('projects.view_project', project_id=project.id))
    
    return render_template('projects/edit.html', project=project, clients=Client.get_active_clients())

@projects_bp.route('/projects/<int:project_id>/archive', methods=['GET', 'POST'])
@login_required
def archive_project(project_id):
    """Archive a project with optional reason"""
    project = Project.query.get_or_404(project_id)
    
    # Check permissions
    if not current_user.is_admin and not current_user.has_permission('archive_projects'):
        flash('You do not have permission to archive projects', 'error')
        return redirect(url_for('projects.view_project', project_id=project_id))
    
    if request.method == 'GET':
        # Show archive form
        return render_template('projects/archive.html', project=project)
    
    if project.status == 'archived':
        flash('Project is already archived', 'info')
    else:
        reason = request.form.get('reason', '').strip()
        project.archive(user_id=current_user.id, reason=reason if reason else None)
        
        # Log the archiving
        log_event("project.archived", 
                 user_id=current_user.id, 
                 project_id=project.id,
                 reason=reason if reason else None)
        track_event(current_user.id, "project.archived", {
            "project_id": project.id,
            "has_reason": bool(reason)
        })
        
        # Log activity
        Activity.log(
            user_id=current_user.id,
            action='archived',
            entity_type='project',
            entity_id=project.id,
            entity_name=project.name,
            description=f'Archived project "{project.name}"' + (f': {reason}' if reason else ''),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        flash(f'Project "{project.name}" archived successfully', 'success')
    
    return redirect(url_for('projects.list_projects', status='archived'))

@projects_bp.route('/projects/<int:project_id>/unarchive', methods=['POST'])
@login_required
def unarchive_project(project_id):
    """Unarchive a project"""
    project = Project.query.get_or_404(project_id)
    
    # Check permissions
    if not current_user.is_admin and not current_user.has_permission('archive_projects'):
        flash('You do not have permission to unarchive projects', 'error')
        return redirect(url_for('projects.view_project', project_id=project_id))
    
    if project.status == 'active':
        flash('Project is already active', 'info')
    else:
        project.unarchive()
        
        # Log the unarchiving
        log_event("project.unarchived", user_id=current_user.id, project_id=project.id)
        track_event(current_user.id, "project.unarchived", {"project_id": project.id})
        
        # Log activity
        Activity.log(
            user_id=current_user.id,
            action='unarchived',
            entity_type='project',
            entity_id=project.id,
            entity_name=project.name,
            description=f'Unarchived project "{project.name}"',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        flash(f'Project "{project.name}" unarchived successfully', 'success')
    
    return redirect(url_for('projects.list_projects'))

@projects_bp.route('/projects/<int:project_id>/deactivate', methods=['POST'])
@login_required
def deactivate_project(project_id):
    """Mark a project as inactive"""
    project = Project.query.get_or_404(project_id)
    
    # Check permissions
    if not current_user.is_admin and not current_user.has_permission('edit_projects'):
        flash('You do not have permission to deactivate projects', 'error')
        return redirect(url_for('projects.view_project', project_id=project_id))
    
    if project.status == 'inactive':
        flash('Project is already inactive', 'info')
    else:
        project.deactivate()
        # Log project deactivation
        log_event("project.deactivated", user_id=current_user.id, project_id=project.id)
        track_event(current_user.id, "project.deactivated", {"project_id": project.id})
        flash(f'Project "{project.name}" marked as inactive', 'success')
    
    return redirect(url_for('projects.list_projects'))

@projects_bp.route('/projects/<int:project_id>/activate', methods=['POST'])
@login_required
def activate_project(project_id):
    """Activate a project"""
    project = Project.query.get_or_404(project_id)
    
    # Check permissions
    if not current_user.is_admin and not current_user.has_permission('edit_projects'):
        flash('You do not have permission to activate projects', 'error')
        return redirect(url_for('projects.view_project', project_id=project_id))
    
    if project.status == 'active':
        flash('Project is already active', 'info')
    else:
        project.activate()
        # Log project activation
        log_event("project.activated", user_id=current_user.id, project_id=project.id)
        track_event(current_user.id, "project.activated", {"project_id": project.id})
        flash(f'Project "{project.name}" activated successfully', 'success')
    
    return redirect(url_for('projects.list_projects'))

@projects_bp.route('/projects/<int:project_id>/delete', methods=['POST'])
@login_required
@admin_or_permission_required('delete_projects')
def delete_project(project_id):
    """Delete a project (only if no time entries exist)"""
    project = Project.query.get_or_404(project_id)
    
    # Check if project has time entries
    if project.time_entries.count() > 0:
        flash('Cannot delete project with existing time entries', 'error')
        return redirect(url_for('projects.view_project', project_id=project_id))
    
    project_name = project.name
    db.session.delete(project)
    if not safe_commit('delete_project', {'project_id': project.id}):
        flash('Could not delete project due to a database error. Please check server logs.', 'error')
        return redirect(url_for('projects.view_project', project_id=project.id))
    
    flash(f'Project "{project_name}" deleted successfully', 'success')
    return redirect(url_for('projects.list_projects'))

@projects_bp.route('/projects/bulk-delete', methods=['POST'])
@login_required
def bulk_delete_projects():
    """Delete multiple projects at once"""
    # Check permissions
    if not current_user.is_admin and not current_user.has_permission('delete_projects'):
        flash('You do not have permission to delete projects', 'error')
        return redirect(url_for('projects.list_projects'))
    
    project_ids = request.form.getlist('project_ids[]')
    
    if not project_ids:
        flash('No projects selected for deletion', 'warning')
        return redirect(url_for('projects.list_projects'))
    
    deleted_count = 0
    skipped_count = 0
    errors = []
    
    for project_id_str in project_ids:
        try:
            project_id = int(project_id_str)
            project = Project.query.get(project_id)
            
            if not project:
                continue
            
            # Check for time entries
            if project.time_entries.count() > 0:
                skipped_count += 1
                errors.append(f"'{project.name}': Has time entries")
                continue
            
            # Delete the project
            project_id_for_log = project.id
            project_name = project.name
            
            db.session.delete(project)
            deleted_count += 1
            
            # Log the deletion
            log_event("project.deleted", user_id=current_user.id, project_id=project_id_for_log)
            track_event(current_user.id, "project.deleted", {"project_id": project_id_for_log})
            
        except Exception as e:
            skipped_count += 1
            errors.append(f"ID {project_id_str}: {str(e)}")
    
    # Commit all deletions
    if deleted_count > 0:
        if not safe_commit('bulk_delete_projects', {'count': deleted_count}):
            flash('Could not delete projects due to a database error. Please check server logs.', 'error')
            return redirect(url_for('projects.list_projects'))
    
    # Show appropriate messages
    if deleted_count > 0:
        flash(f'Successfully deleted {deleted_count} project{"s" if deleted_count != 1 else ""}', 'success')
    
    if skipped_count > 0:
        flash(f'Skipped {skipped_count} project{"s" if skipped_count != 1 else ""}: {", ".join(errors[:3])}{"..." if len(errors) > 3 else ""}', 'warning')
    
    if deleted_count == 0 and skipped_count == 0:
        flash('No projects were deleted', 'info')
    
    return redirect(url_for('projects.list_projects'))

@projects_bp.route('/projects/bulk-status-change', methods=['POST'])
@login_required
def bulk_status_change():
    """Change status for multiple projects at once"""
    # Check permissions
    if not current_user.is_admin and not current_user.has_permission('edit_projects'):
        flash('You do not have permission to change project status', 'error')
        return redirect(url_for('projects.list_projects'))
    
    project_ids = request.form.getlist('project_ids[]')
    new_status = request.form.get('new_status', '').strip()
    archive_reason = request.form.get('archive_reason', '').strip() if new_status == 'archived' else None
    
    if not project_ids:
        flash('No projects selected', 'warning')
        return redirect(url_for('projects.list_projects'))
    
    if new_status not in ['active', 'inactive', 'archived']:
        flash('Invalid status', 'error')
        return redirect(url_for('projects.list_projects'))
    
    updated_count = 0
    errors = []
    
    for project_id_str in project_ids:
        try:
            project_id = int(project_id_str)
            project = Project.query.get(project_id)
            
            if not project:
                continue
            
            # Update status based on type
            if new_status == 'archived':
                # Use the enhanced archive method
                project.status = 'archived'
                project.archived_at = datetime.utcnow()
                project.archived_by = current_user.id
                project.archived_reason = archive_reason if archive_reason else None
                project.updated_at = datetime.utcnow()
            elif new_status == 'active':
                # Clear archiving metadata when activating
                project.status = 'active'
                project.archived_at = None
                project.archived_by = None
                project.archived_reason = None
                project.updated_at = datetime.utcnow()
            else:
                # Just update status for inactive
                project.status = new_status
                project.updated_at = datetime.utcnow()
            
            updated_count += 1
            
            # Log the status change
            log_event(f"project.status_changed_{new_status}", user_id=current_user.id, project_id=project.id)
            track_event(current_user.id, "project.status_changed", {"project_id": project.id, "new_status": new_status})
            
            # Log activity
            Activity.log(
                user_id=current_user.id,
                action=f'status_changed_{new_status}',
                entity_type='project',
                entity_id=project.id,
                entity_name=project.name,
                description=f'Changed project "{project.name}" status to {new_status}' + (f': {archive_reason}' if new_status == 'archived' and archive_reason else ''),
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            
        except Exception as e:
            errors.append(f"ID {project_id_str}: {str(e)}")
    
    # Commit all changes
    if updated_count > 0:
        if not safe_commit('bulk_status_change_projects', {'count': updated_count, 'status': new_status}):
            flash('Could not update project status due to a database error. Please check server logs.', 'error')
            return redirect(url_for('projects.list_projects'))
    
    # Show appropriate messages
    status_labels = {'active': 'active', 'inactive': 'inactive', 'archived': 'archived'}
    if updated_count > 0:
        flash(f'Successfully marked {updated_count} project{"s" if updated_count != 1 else ""} as {status_labels.get(new_status, new_status)}', 'success')
    
    if errors:
        flash(f'Some projects could not be updated: {", ".join(errors[:3])}{"..." if len(errors) > 3 else ""}', 'warning')
    
    if updated_count == 0:
        flash('No projects were updated', 'info')
    
    return redirect(url_for('projects.list_projects'))


# ===== FAVORITE PROJECTS ROUTES =====

@projects_bp.route('/projects/<int:project_id>/favorite', methods=['POST'])
@login_required
def favorite_project(project_id):
    """Add a project to user's favorites"""
    project = Project.query.get_or_404(project_id)
    
    try:
        # Check if already favorited
        if current_user.is_project_favorite(project):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': _('Project is already in favorites')}), 200
            flash(_('Project is already in favorites'), 'info')
        else:
            # Add to favorites
            current_user.add_favorite_project(project)
            
            # Log activity
            Activity.log(
                user_id=current_user.id,
                action='favorited',
                entity_type='project',
                entity_id=project.id,
                entity_name=project.name,
                description=f'Added project "{project.name}" to favorites',
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            
            # Track event
            log_event("project.favorited", user_id=current_user.id, project_id=project.id)
            track_event(current_user.id, "project.favorited", {"project_id": project.id})
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True, 'message': _('Project added to favorites')}), 200
            flash(_('Project added to favorites'), 'success')
    except Exception as e:
        current_app.logger.error(f"Error favoriting project: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': _('Failed to add project to favorites')}), 500
        flash(_('Failed to add project to favorites'), 'error')
    
    # Redirect back to referrer or project list
    return redirect(request.referrer or url_for('projects.list_projects'))


@projects_bp.route('/projects/<int:project_id>/unfavorite', methods=['POST'])
@login_required
def unfavorite_project(project_id):
    """Remove a project from user's favorites"""
    project = Project.query.get_or_404(project_id)
    
    try:
        # Check if not favorited
        if not current_user.is_project_favorite(project):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': _('Project is not in favorites')}), 200
            flash(_('Project is not in favorites'), 'info')
        else:
            # Remove from favorites
            current_user.remove_favorite_project(project)
            
            # Log activity
            Activity.log(
                user_id=current_user.id,
                action='unfavorited',
                entity_type='project',
                entity_id=project.id,
                entity_name=project.name,
                description=f'Removed project "{project.name}" from favorites',
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            
            # Track event
            log_event("project.unfavorited", user_id=current_user.id, project_id=project.id)
            track_event(current_user.id, "project.unfavorited", {"project_id": project.id})
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True, 'message': _('Project removed from favorites')}), 200
            flash(_('Project removed from favorites'), 'success')
    except Exception as e:
        current_app.logger.error(f"Error unfavoriting project: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': _('Failed to remove project from favorites')}), 500
        flash(_('Failed to remove project from favorites'), 'error')
    
    # Redirect back to referrer or project list
    return redirect(request.referrer or url_for('projects.list_projects'))


# ===== PROJECT COSTS ROUTES =====

@projects_bp.route('/projects/<int:project_id>/costs')
@login_required
def list_costs(project_id):
    """List all costs for a project"""
    project = Project.query.get_or_404(project_id)
    
    # Get filters from query params
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    category = request.args.get('category', '')
    
    start_date = None
    end_date = None
    
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    # Get costs
    query = project.costs
    
    if start_date:
        query = query.filter(ProjectCost.cost_date >= start_date)
    
    if end_date:
        query = query.filter(ProjectCost.cost_date <= end_date)
    
    if category:
        query = query.filter(ProjectCost.category == category)
    
    costs = query.order_by(ProjectCost.cost_date.desc()).all()
    
    # Get category breakdown
    category_breakdown = ProjectCost.get_costs_by_category(
        project_id, start_date, end_date
    )
    
    return render_template(
        'projects/costs.html',
        project=project,
        costs=costs,
        category_breakdown=category_breakdown,
        start_date=start_date_str,
        end_date=end_date_str,
        selected_category=category
    )


@projects_bp.route('/projects/<int:project_id>/costs/add', methods=['GET', 'POST'])
@login_required
def add_cost(project_id):
    """Add a new cost to a project"""
    project = Project.query.get_or_404(project_id)
    
    if request.method == 'POST':
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        amount = request.form.get('amount', '').strip()
        cost_date_str = request.form.get('cost_date', '').strip()
        billable = request.form.get('billable') == 'on'
        notes = request.form.get('notes', '').strip()
        currency_code = request.form.get('currency_code', 'EUR').strip()
        
        # Validate required fields
        if not description or not category or not amount or not cost_date_str:
            flash(_('Description, category, amount, and date are required'), 'error')
            return render_template('projects/add_cost.html', project=project)
        
        # Validate amount
        try:
            amount = Decimal(amount)
            if amount <= 0:
                raise ValueError('Amount must be positive')
        except (ValueError, Exception):
            flash(_('Invalid amount format'), 'error')
            return render_template('projects/add_cost.html', project=project)
        
        # Validate date
        try:
            cost_date = datetime.strptime(cost_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash(_('Invalid date format'), 'error')
            return render_template('projects/add_cost.html', project=project)
        
        # Create cost
        cost = ProjectCost(
            project_id=project_id,
            user_id=current_user.id,
            description=description,
            category=category,
            amount=amount,
            cost_date=cost_date,
            billable=billable,
            notes=notes,
            currency_code=currency_code
        )
        
        db.session.add(cost)
        if not safe_commit('add_project_cost', {'project_id': project_id}):
            flash(_('Could not add cost due to a database error. Please check server logs.'), 'error')
            return render_template('projects/add_cost.html', project=project)
        
        flash(_('Cost added successfully'), 'success')
        return redirect(url_for('projects.view_project', project_id=project.id))
    
    return render_template('projects/add_cost.html', project=project)


@projects_bp.route('/projects/<int:project_id>/costs/<int:cost_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_cost(project_id, cost_id):
    """Edit a project cost"""
    project = Project.query.get_or_404(project_id)
    cost = ProjectCost.query.get_or_404(cost_id)
    
    # Verify cost belongs to project
    if cost.project_id != project_id:
        flash(_('Cost not found'), 'error')
        return redirect(url_for('projects.view_project', project_id=project_id))
    
    # Only admin or the user who created the cost can edit
    if not current_user.is_admin and cost.user_id != current_user.id:
        flash(_('You do not have permission to edit this cost'), 'error')
        return redirect(url_for('projects.view_project', project_id=project_id))
    
    if request.method == 'POST':
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        amount = request.form.get('amount', '').strip()
        cost_date_str = request.form.get('cost_date', '').strip()
        billable = request.form.get('billable') == 'on'
        notes = request.form.get('notes', '').strip()
        currency_code = request.form.get('currency_code', 'EUR').strip()
        
        # Validate required fields
        if not description or not category or not amount or not cost_date_str:
            flash(_('Description, category, amount, and date are required'), 'error')
            return render_template('projects/edit_cost.html', project=project, cost=cost)
        
        # Validate amount
        try:
            amount = Decimal(amount)
            if amount <= 0:
                raise ValueError('Amount must be positive')
        except (ValueError, Exception):
            flash(_('Invalid amount format'), 'error')
            return render_template('projects/edit_cost.html', project=project, cost=cost)
        
        # Validate date
        try:
            cost_date = datetime.strptime(cost_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash(_('Invalid date format'), 'error')
            return render_template('projects/edit_cost.html', project=project, cost=cost)
        
        # Update cost
        cost.description = description
        cost.category = category
        cost.amount = amount
        cost.cost_date = cost_date
        cost.billable = billable
        cost.notes = notes
        cost.currency_code = currency_code
        cost.updated_at = datetime.utcnow()
        
        if not safe_commit('edit_project_cost', {'cost_id': cost_id}):
            flash(_('Could not update cost due to a database error. Please check server logs.'), 'error')
            return render_template('projects/edit_cost.html', project=project, cost=cost)
        
        flash(_('Cost updated successfully'), 'success')
        return redirect(url_for('projects.view_project', project_id=project.id))
    
    return render_template('projects/edit_cost.html', project=project, cost=cost)


@projects_bp.route('/projects/<int:project_id>/costs/<int:cost_id>/delete', methods=['POST'])
@login_required
def delete_cost(project_id, cost_id):
    """Delete a project cost"""
    project = Project.query.get_or_404(project_id)
    cost = ProjectCost.query.get_or_404(cost_id)
    
    # Verify cost belongs to project
    if cost.project_id != project_id:
        flash(_('Cost not found'), 'error')
        return redirect(url_for('projects.view_project', project_id=project_id))
    
    # Only admin or the user who created the cost can delete
    if not current_user.is_admin and cost.user_id != current_user.id:
        flash(_('You do not have permission to delete this cost'), 'error')
        return redirect(url_for('projects.view_project', project_id=project_id))
    
    # Check if cost has been invoiced
    if cost.is_invoiced:
        flash(_('Cannot delete cost that has been invoiced'), 'error')
        return redirect(url_for('projects.view_project', project_id=project_id))
    
    cost_description = cost.description
    db.session.delete(cost)
    if not safe_commit('delete_project_cost', {'cost_id': cost_id}):
        flash(_('Could not delete cost due to a database error. Please check server logs.'), 'error')
        return redirect(url_for('projects.view_project', project_id=project_id))
    
    flash(_(f'Cost "{cost_description}" deleted successfully'), 'success')
    return redirect(url_for('projects.view_project', project_id=project.id))


# API endpoint for getting project costs as JSON
@projects_bp.route('/api/projects/<int:project_id>/costs')
@login_required
def api_project_costs(project_id):
    """API endpoint to get project costs"""
    project = Project.query.get_or_404(project_id)
    
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    start_date = None
    end_date = None
    
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    costs = ProjectCost.get_project_costs(project_id, start_date, end_date)
    total_costs = ProjectCost.get_total_costs(project_id, start_date, end_date)
    billable_costs = ProjectCost.get_total_costs(project_id, start_date, end_date, billable_only=True)
    
    return jsonify({
        'costs': [cost.to_dict() for cost in costs],
        'total_costs': total_costs,
        'billable_costs': billable_costs,
        'count': len(costs)
    })


# ===== PROJECT EXTRA GOODS ROUTES =====

@projects_bp.route('/projects/<int:project_id>/goods')
@login_required
def list_goods(project_id):
    """List all extra goods for a project"""
    project = Project.query.get_or_404(project_id)
    
    # Get goods
    goods = project.extra_goods.order_by(ExtraGood.created_at.desc()).all()
    
    # Get category breakdown
    category_breakdown = ExtraGood.get_goods_by_category(project_id=project_id)
    
    # Calculate totals
    total_amount = ExtraGood.get_total_amount(project_id=project_id)
    billable_amount = ExtraGood.get_total_amount(project_id=project_id, billable_only=True)
    
    return render_template(
        'projects/goods.html',
        project=project,
        goods=goods,
        category_breakdown=category_breakdown,
        total_amount=total_amount,
        billable_amount=billable_amount
    )


@projects_bp.route('/projects/<int:project_id>/goods/add', methods=['GET', 'POST'])
@login_required
def add_good(project_id):
    """Add a new extra good to a project"""
    project = Project.query.get_or_404(project_id)
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', 'product').strip()
        quantity = request.form.get('quantity', '1').strip()
        unit_price = request.form.get('unit_price', '').strip()
        sku = request.form.get('sku', '').strip()
        billable = request.form.get('billable') == 'on'
        currency_code = request.form.get('currency_code', 'EUR').strip()
        
        # Validate required fields
        if not name or not unit_price:
            flash(_('Name and unit price are required'), 'error')
            return render_template('projects/add_good.html', project=project)
        
        # Validate quantity
        try:
            quantity = Decimal(quantity)
            if quantity <= 0:
                raise ValueError('Quantity must be positive')
        except (ValueError, Exception):
            flash(_('Invalid quantity format'), 'error')
            return render_template('projects/add_good.html', project=project)
        
        # Validate unit price
        try:
            unit_price = Decimal(unit_price)
            if unit_price < 0:
                raise ValueError('Unit price cannot be negative')
        except (ValueError, Exception):
            flash(_('Invalid unit price format'), 'error')
            return render_template('projects/add_good.html', project=project)
        
        # Create extra good
        good = ExtraGood(
            name=name,
            description=description if description else None,
            category=category,
            quantity=quantity,
            unit_price=unit_price,
            sku=sku if sku else None,
            billable=billable,
            currency_code=currency_code,
            project_id=project_id,
            created_by=current_user.id
        )
        
        db.session.add(good)
        if not safe_commit('add_project_good', {'project_id': project_id}):
            flash(_('Could not add extra good due to a database error. Please check server logs.'), 'error')
            return render_template('projects/add_good.html', project=project)
        
        flash(_('Extra good added successfully'), 'success')
        return redirect(url_for('projects.view_project', project_id=project.id))
    
    return render_template('projects/add_good.html', project=project)


@projects_bp.route('/projects/<int:project_id>/goods/<int:good_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_good(project_id, good_id):
    """Edit a project extra good"""
    project = Project.query.get_or_404(project_id)
    good = ExtraGood.query.get_or_404(good_id)
    
    # Verify good belongs to project
    if good.project_id != project_id:
        flash(_('Extra good not found'), 'error')
        return redirect(url_for('projects.view_project', project_id=project_id))
    
    # Only admin or the user who created the good can edit
    if not current_user.is_admin and good.created_by != current_user.id:
        flash(_('You do not have permission to edit this extra good'), 'error')
        return redirect(url_for('projects.view_project', project_id=project_id))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', 'product').strip()
        quantity = request.form.get('quantity', '1').strip()
        unit_price = request.form.get('unit_price', '').strip()
        sku = request.form.get('sku', '').strip()
        billable = request.form.get('billable') == 'on'
        currency_code = request.form.get('currency_code', 'EUR').strip()
        
        # Validate required fields
        if not name or not unit_price:
            flash(_('Name and unit price are required'), 'error')
            return render_template('projects/edit_good.html', project=project, good=good)
        
        # Validate quantity
        try:
            quantity = Decimal(quantity)
            if quantity <= 0:
                raise ValueError('Quantity must be positive')
        except (ValueError, Exception):
            flash(_('Invalid quantity format'), 'error')
            return render_template('projects/edit_good.html', project=project, good=good)
        
        # Validate unit price
        try:
            unit_price = Decimal(unit_price)
            if unit_price < 0:
                raise ValueError('Unit price cannot be negative')
        except (ValueError, Exception):
            flash(_('Invalid unit price format'), 'error')
            return render_template('projects/edit_good.html', project=project, good=good)
        
        # Update good
        good.name = name
        good.description = description if description else None
        good.category = category
        good.quantity = quantity
        good.unit_price = unit_price
        good.sku = sku if sku else None
        good.billable = billable
        good.currency_code = currency_code
        good.update_total()
        
        if not safe_commit('edit_project_good', {'good_id': good_id}):
            flash(_('Could not update extra good due to a database error. Please check server logs.'), 'error')
            return render_template('projects/edit_good.html', project=project, good=good)
        
        flash(_('Extra good updated successfully'), 'success')
        return redirect(url_for('projects.view_project', project_id=project.id))
    
    return render_template('projects/edit_good.html', project=project, good=good)


@projects_bp.route('/projects/<int:project_id>/goods/<int:good_id>/delete', methods=['POST'])
@login_required
def delete_good(project_id, good_id):
    """Delete a project extra good"""
    project = Project.query.get_or_404(project_id)
    good = ExtraGood.query.get_or_404(good_id)
    
    # Verify good belongs to project
    if good.project_id != project_id:
        flash(_('Extra good not found'), 'error')
        return redirect(url_for('projects.view_project', project_id=project_id))
    
    # Only admin or the user who created the good can delete
    if not current_user.is_admin and good.created_by != current_user.id:
        flash(_('You do not have permission to delete this extra good'), 'error')
        return redirect(url_for('projects.view_project', project_id=project_id))
    
    # Check if good has been added to an invoice
    if good.invoice_id:
        flash(_('Cannot delete extra good that has been added to an invoice'), 'error')
        return redirect(url_for('projects.view_project', project_id=project_id))
    
    good_name = good.name
    db.session.delete(good)
    if not safe_commit('delete_project_good', {'good_id': good_id}):
        flash(_('Could not delete extra good due to a database error. Please check server logs.'), 'error')
        return redirect(url_for('projects.view_project', project_id=project_id))
    
    flash(_(f'Extra good "{good_name}" deleted successfully'), 'success')
    return redirect(url_for('projects.view_project', project_id=project.id))


# API endpoint for getting project extra goods as JSON
@projects_bp.route('/api/projects/<int:project_id>/goods')
@login_required
def api_project_goods(project_id):
    """API endpoint to get project extra goods"""
    project = Project.query.get_or_404(project_id)
    
    goods = ExtraGood.get_project_goods(project_id)
    total_amount = ExtraGood.get_total_amount(project_id=project_id)
    billable_amount = ExtraGood.get_total_amount(project_id=project_id, billable_only=True)
    
    return jsonify({
        'goods': [good.to_dict() for good in goods],
        'total_amount': total_amount,
        'billable_amount': billable_amount,
        'count': len(goods)
    })


