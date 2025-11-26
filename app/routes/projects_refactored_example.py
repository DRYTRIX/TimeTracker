"""
Example refactored projects route using service layer and fixing N+1 queries.
This demonstrates the new architecture pattern.

To use: Replace the corresponding functions in app/routes/projects.py
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_babel import gettext as _
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from app import db
from app.services import ProjectService
from app.repositories import ProjectRepository, ClientRepository
from app.models import Project, Client, UserFavoriteProject
from app.utils.permissions import admin_or_permission_required

projects_bp = Blueprint('projects', __name__)


@projects_bp.route('/projects')
@login_required
def list_projects():
    """
    List all projects - REFACTORED VERSION
    
    This version fixes N+1 queries by using joinedload to eagerly load
    related data (clients) in a single query.
    """
    from app import track_page_view
    track_page_view("projects_list")
    
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'active')
    client_name = request.args.get('client', '').strip()
    search = request.args.get('search', '').strip()
    favorites_only = request.args.get('favorites', '').lower() == 'true'
    
    # Use repository with eager loading to fix N+1 queries
    project_repo = ProjectRepository()
    query = project_repo.query().options(
        joinedload(Project.client)  # Eagerly load client to avoid N+1
    )
    
    # Filter by favorites if requested
    if favorites_only:
        query = query.join(
            UserFavoriteProject,
            db.and_(
                UserFavoriteProject.project_id == Project.id,
                UserFavoriteProject.user_id == current_user.id
            )
        )
    
    # Filter by status
    if status == 'active':
        query = query.filter(Project.status == 'active')
    elif status == 'archived':
        query = query.filter(Project.status == 'archived')
    elif status == 'inactive':
        query = query.filter(Project.status == 'inactive')
    
    # Filter by client
    if client_name:
        query = query.join(Client).filter(Client.name == client_name)
    
    # Search filter
    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                Project.name.ilike(like),
                Project.description.ilike(like)
            )
        )
    
    # Paginate with eager loading
    projects_pagination = query.order_by(Project.name).paginate(
        page=page,
        per_page=20,
        error_out=False
    )
    
    # Get user's favorite project IDs (single query)
    favorite_project_ids = {
        fav.project_id 
        for fav in UserFavoriteProject.query.filter_by(user_id=current_user.id).all()
    }
    
    # Get clients for filter dropdown (single query)
    client_repo = ClientRepository()
    clients = client_repo.get_active_clients()
    client_list = [c.name for c in clients]
    
    return render_template(
        'projects/list.html',
        projects=projects_pagination.items,
        status=status,
        clients=client_list,
        favorite_project_ids=favorite_project_ids,
        favorites_only=favorites_only,
        pagination=projects_pagination
    )


@projects_bp.route('/projects/<int:project_id>')
@login_required
def view_project(project_id):
    """
    View project details - REFACTORED VERSION
    
    This version uses the service layer and fixes N+1 queries.
    """
    from app.repositories import TimeEntryRepository
    from app.models import Task, Comment, ProjectCost, KanbanColumn
    from sqlalchemy.orm import joinedload
    
    # Use repository to get project with relations
    project_repo = ProjectRepository()
    project = project_repo.get_with_stats(project_id)
    
    if not project:
        flash(_('Project not found'), 'error')
        return redirect(url_for('projects.list_projects'))
    
    # Get time entries with eager loading (fixes N+1)
    time_entry_repo = TimeEntryRepository()
    page = request.args.get('page', 1, type=int)
    
    entries_query = time_entry_repo.query().filter(
        TimeEntry.project_id == project_id,
        TimeEntry.end_time.isnot(None)
    ).options(
        joinedload(TimeEntry.user),  # Eagerly load user
        joinedload(TimeEntry.task)    # Eagerly load task
    ).order_by(TimeEntry.start_time.desc())
    
    entries_pagination = entries_query.paginate(
        page=page,
        per_page=50,
        error_out=False
    )
    
    # Get tasks with eager loading
    tasks = Task.query.filter_by(project_id=project_id).options(
        joinedload(Task.assignee)  # If Task has assignee relationship
    ).order_by(Task.priority.desc(), Task.due_date.asc(), Task.created_at.asc()).all()
    
    # Get user totals (this might need optimization too)
    user_totals = project.get_user_totals()
    
    # Get comments with eager loading
    comments = Comment.query.filter_by(project_id=project_id).options(
        joinedload(Comment.user)  # Eagerly load user
    ).order_by(Comment.created_at.desc()).all()
    
    # Get recent project costs
    recent_costs = ProjectCost.query.filter_by(project_id=project_id).order_by(
        ProjectCost.cost_date.desc()
    ).limit(5).all()
    
    # Get kanban columns
    kanban_columns = KanbanColumn.get_active_columns(project_id=project_id) if KanbanColumn else []
    
    return render_template(
        'projects/view.html',
        project=project,
        entries=entries_pagination.items,
        entries_pagination=entries_pagination,
        tasks=tasks,
        user_totals=user_totals,
        comments=comments,
        recent_costs=recent_costs,
        kanban_columns=kanban_columns
    )


@projects_bp.route('/projects/create', methods=['GET', 'POST'])
@login_required
@admin_or_permission_required('create_projects')
def create_project():
    """
    Create a new project - REFACTORED VERSION using service layer
    """
    if request.method == 'POST':
        # Use service layer for business logic
        project_service = ProjectService()
        
        result = project_service.create_project(
            name=request.form.get('name', '').strip(),
            client_id=request.form.get('client_id', type=int),
            description=request.form.get('description', '').strip() or None,
            billable=request.form.get('billable') == 'on',
            hourly_rate=request.form.get('hourly_rate', type=float),
            created_by=current_user.id
        )
        
        if result['success']:
            flash(_('Project created successfully'), 'success')
            return redirect(url_for('projects.view_project', project_id=result['project'].id))
        else:
            flash(_(result['message']), 'error')
    
    # GET request - show form
    client_repo = ClientRepository()
    clients = client_repo.get_active_clients()
    
    return render_template('projects/create.html', clients=clients)

