from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify, make_response
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db, log_event, track_event
from app.models import Project, TimeEntry, Task, Client, ProjectCost, KanbanColumn, ExtraGood
from datetime import datetime
from decimal import Decimal
from app.utils.db import safe_commit

projects_bp = Blueprint('projects', __name__)

@projects_bp.route('/projects')
@login_required
def list_projects():
    """List all projects"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'active')
    client_name = request.args.get('client', '').strip()
    search = request.args.get('search', '').strip()
    
    query = Project.query
    if status == 'active':
        query = query.filter_by(status='active')
    elif status == 'archived':
        query = query.filter_by(status='archived')
    
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
    
    projects = query.order_by(Project.name).paginate(
        page=page,
        per_page=20,
        error_out=False
    )
    
    # Get clients for filter dropdown
    clients = Client.get_active_clients()
    client_list = [c.name for c in clients]
    
    return render_template(
        'projects/list.html',
        projects=projects.items,
        status=status,
        clients=client_list
    )

@projects_bp.route('/projects/create', methods=['GET', 'POST'])
@login_required
def create_project():
    """Create a new project"""
    if not current_user.is_admin:
        try:
            current_app.logger.warning("Non-admin user attempted to create project: user=%s", current_user.username)
        except Exception:
            pass
        flash('Only administrators can create projects', 'error')
        return redirect(url_for('projects.list_projects'))
    
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
        
        # Create project
        project = Project(
            name=name,
            client_id=client_id,
            description=description,
            billable=billable,
            hourly_rate=hourly_rate,
            billing_ref=billing_ref,
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
def edit_project(project_id):
    """Edit project details"""
    if not current_user.is_admin:
        flash('Only administrators can edit projects', 'error')
        return redirect(url_for('projects.view_project', project_id=project_id))
    
    project = Project.query.get_or_404(project_id)
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        client_id = request.form.get('client_id', '').strip()
        description = request.form.get('description', '').strip()
        billable = request.form.get('billable') == 'on'
        hourly_rate = request.form.get('hourly_rate', '').strip()
        billing_ref = request.form.get('billing_ref', '').strip()
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
        
        # Update project
        project.name = name
        project.client_id = client_id
        project.description = description
        project.billable = billable
        project.hourly_rate = hourly_rate
        project.billing_ref = billing_ref
        project.budget_amount = budget_amount if budget_amount_raw != '' else None
        project.budget_threshold_percent = budget_threshold_percent
        project.updated_at = datetime.utcnow()
        
        if not safe_commit('edit_project', {'project_id': project.id}):
            flash('Could not update project due to a database error. Please check server logs.', 'error')
            return render_template('projects/edit.html', project=project, clients=Client.get_active_clients())
        
        flash(f'Project "{name}" updated successfully', 'success')
        return redirect(url_for('projects.view_project', project_id=project.id))
    
    return render_template('projects/edit.html', project=project, clients=Client.get_active_clients())

@projects_bp.route('/projects/<int:project_id>/archive', methods=['POST'])
@login_required
def archive_project(project_id):
    """Archive a project"""
    if not current_user.is_admin:
        flash('Only administrators can archive projects', 'error')
        return redirect(url_for('projects.view_project', project_id=project_id))
    
    project = Project.query.get_or_404(project_id)
    
    if project.status == 'archived':
        flash('Project is already archived', 'info')
    else:
        project.archive()
        flash(f'Project "{project.name}" archived successfully', 'success')
    
    return redirect(url_for('projects.list_projects'))

@projects_bp.route('/projects/<int:project_id>/unarchive', methods=['POST'])
@login_required
def unarchive_project(project_id):
    """Unarchive a project"""
    if not current_user.is_admin:
        flash('Only administrators can unarchive projects', 'error')
        return redirect(url_for('projects.view_project', project_id=project_id))
    
    project = Project.query.get_or_404(project_id)
    
    if project.status == 'active':
        flash('Project is already active', 'info')
    else:
        project.unarchive()
        flash(f'Project "{project.name}" unarchived successfully', 'success')
    
    return redirect(url_for('projects.list_projects'))

@projects_bp.route('/projects/<int:project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    """Delete a project (only if no time entries exist)"""
    if not current_user.is_admin:
        flash('Only administrators can delete projects', 'error')
        return redirect(url_for('projects.view_project', project_id=project_id))
    
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


