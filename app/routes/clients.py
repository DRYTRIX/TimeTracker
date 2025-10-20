from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db, log_event, track_event
from app.models import Client, Project
from datetime import datetime
from decimal import Decimal
from app.utils.db import safe_commit

clients_bp = Blueprint('clients', __name__)

@clients_bp.route('/clients')
@login_required
def list_clients():
    """List all clients"""
    status = request.args.get('status', 'active')
    search = request.args.get('search', '').strip()
    
    query = Client.query
    if status == 'active':
        query = query.filter_by(status='active')
    elif status == 'inactive':
        query = query.filter_by(status='inactive')
    
    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                Client.name.ilike(like),
                Client.description.ilike(like),
                Client.contact_person.ilike(like),
                Client.email.ilike(like)
            )
        )
    
    clients = query.order_by(Client.name).all()
    
    return render_template('clients/list.html', clients=clients, status=status, search=search)

@clients_bp.route('/clients/create', methods=['GET', 'POST'])
@login_required
def create_client():
    """Create a new client"""
    if not current_user.is_admin:
        flash(_('Only administrators can create clients'), 'error')
        return redirect(url_for('clients.list_clients'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        contact_person = request.form.get('contact_person', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        default_hourly_rate = request.form.get('default_hourly_rate', '').strip()
        try:
            current_app.logger.info(
                "POST /clients/create user=%s name=%s email=%s",
                current_user.username,
                name or '<empty>',
                email or '<empty>'
            )
        except Exception:
            pass
        
        # Validate required fields
        if not name:
            flash('Client name is required', 'error')
            try:
                current_app.logger.warning("Validation failed: missing client name")
            except Exception:
                pass
            return render_template('clients/create.html')
        
        # Check if client name already exists
        if Client.query.filter_by(name=name).first():
            flash('A client with this name already exists', 'error')
            try:
                current_app.logger.warning("Validation failed: duplicate client name '%s'", name)
            except Exception:
                pass
            return render_template('clients/create.html')
        
        # Validate hourly rate
        try:
            default_hourly_rate = Decimal(default_hourly_rate) if default_hourly_rate else None
        except ValueError:
            flash('Invalid hourly rate format', 'error')
            try:
                current_app.logger.warning("Validation failed: invalid hourly rate '%s'", default_hourly_rate)
            except Exception:
                pass
            return render_template('clients/create.html')
        
        # Create client
        client = Client(
            name=name,
            description=description,
            contact_person=contact_person,
            email=email,
            phone=phone,
            address=address,
            default_hourly_rate=default_hourly_rate
        )
        
        db.session.add(client)
        if not safe_commit('create_client', {'name': name}):
            flash('Could not create client due to a database error. Please check server logs.', 'error')
            return render_template('clients/create.html')
        
        # Log client creation
        log_event("client.created", user_id=current_user.id, client_id=client.id)
        track_event(current_user.id, "client.created", {"client_id": client.id})
        
        flash(f'Client "{name}" created successfully', 'success')
        return redirect(url_for('clients.view_client', client_id=client.id))
    
    return render_template('clients/create.html')

@clients_bp.route('/clients/<int:client_id>')
@login_required
def view_client(client_id):
    """View client details and projects"""
    client = Client.query.get_or_404(client_id)
    
    # Get projects for this client
    projects = Project.query.filter_by(client_id=client.id).order_by(Project.name).all()
    
    return render_template('clients/view.html', client=client, projects=projects)

@clients_bp.route('/clients/<int:client_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_client(client_id):
    """Edit client details"""
    if not current_user.is_admin:
        flash('Only administrators can edit clients', 'error')
        return redirect(url_for('clients.view_client', client_id=client_id))
    
    client = Client.query.get_or_404(client_id)
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        contact_person = request.form.get('contact_person', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        default_hourly_rate = request.form.get('default_hourly_rate', '').strip()
        
        # Validate required fields
        if not name:
            flash('Client name is required', 'error')
            return render_template('clients/edit.html', client=client)
        
        # Check if client name already exists (excluding current client)
        existing = Client.query.filter_by(name=name).first()
        if existing and existing.id != client.id:
            flash('A client with this name already exists', 'error')
            return render_template('clients/edit.html', client=client)
        
        # Validate hourly rate
        try:
            default_hourly_rate = Decimal(default_hourly_rate) if default_hourly_rate else None
        except ValueError:
            flash('Invalid hourly rate format', 'error')
            return render_template('clients/edit.html', client=client)
        
        # Update client
        client.name = name
        client.description = description
        client.contact_person = contact_person
        client.email = email
        client.phone = phone
        client.address = address
        client.default_hourly_rate = default_hourly_rate
        client.updated_at = datetime.utcnow()
        
        if not safe_commit('edit_client', {'client_id': client.id}):
            flash('Could not update client due to a database error. Please check server logs.', 'error')
            return render_template('clients/edit.html', client=client)
        
        # Log client update
        log_event("client.updated", user_id=current_user.id, client_id=client.id)
        track_event(current_user.id, "client.updated", {"client_id": client.id})
        
        flash(f'Client "{name}" updated successfully', 'success')
        return redirect(url_for('clients.view_client', client_id=client.id))
    
    return render_template('clients/edit.html', client=client)

@clients_bp.route('/clients/<int:client_id>/archive', methods=['POST'])
@login_required
def archive_client(client_id):
    """Archive a client"""
    if not current_user.is_admin:
        flash('Only administrators can archive clients', 'error')
        return redirect(url_for('clients.view_client', client_id=client_id))
    
    client = Client.query.get_or_404(client_id)
    
    if client.status == 'inactive':
        flash('Client is already inactive', 'info')
    else:
        client.archive()
        log_event("client.archived", user_id=current_user.id, client_id=client.id)
        track_event(current_user.id, "client.archived", {"client_id": client.id})
        flash(f'Client "{client.name}" archived successfully', 'success')
    
    return redirect(url_for('clients.list_clients'))

@clients_bp.route('/clients/<int:client_id>/activate', methods=['POST'])
@login_required
def activate_client(client_id):
    """Activate a client"""
    if not current_user.is_admin:
        flash('Only administrators can activate clients', 'error')
        return redirect(url_for('clients.view_client', client_id=client_id))
    
    client = Client.query.get_or_404(client_id)
    
    if client.status == 'active':
        flash('Client is already active', 'info')
    else:
        client.activate()
        flash(f'Client "{client.name}" activated successfully', 'success')
    
    return redirect(url_for('clients.list_clients'))

@clients_bp.route('/clients/<int:client_id>/delete', methods=['POST'])
@login_required
def delete_client(client_id):
    """Delete a client (only if no projects exist)"""
    if not current_user.is_admin:
        flash('Only administrators can delete clients', 'error')
        return redirect(url_for('clients.view_client', client_id=client_id))
    
    client = Client.query.get_or_404(client_id)
    
    # Check if client has projects
    if client.projects.count() > 0:
        flash('Cannot delete client with existing projects', 'error')
        return redirect(url_for('clients.view_client', client_id=client_id))
    
    client_name = client.name
    client_id_for_log = client.id
    db.session.delete(client)
    if not safe_commit('delete_client', {'client_id': client.id}):
        flash('Could not delete client due to a database error. Please check server logs.', 'error')
        return redirect(url_for('clients.view_client', client_id=client.id))
    
    # Log client deletion
    log_event("client.deleted", user_id=current_user.id, client_id=client_id_for_log)
    track_event(current_user.id, "client.deleted", {"client_id": client_id_for_log})
    
    flash(f'Client "{client_name}" deleted successfully', 'success')
    return redirect(url_for('clients.list_clients'))

@clients_bp.route('/api/clients')
@login_required
def api_clients():
    """API endpoint to get clients for dropdowns"""
    clients = Client.get_active_clients()
    return {'clients': [{'id': c.id, 'name': c.name, 'default_rate': float(c.default_hourly_rate) if c.default_hourly_rate else None} for c in clients]}
