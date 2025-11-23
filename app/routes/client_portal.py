"""Client Portal Routes

Provides a simplified interface for clients to view their projects,
invoices, and time entries. Uses separate authentication from regular users.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, session
from flask_babel import gettext as _
from app import db
from app.models import Client, Project, Invoice, TimeEntry, User, Quote
from app.utils.db import safe_commit
from datetime import datetime, timedelta
from sqlalchemy import func
from functools import wraps

client_portal_bp = Blueprint('client_portal', __name__)


def get_current_client():
    """Get the currently logged-in client from session (either Client or User portal access)"""
    # Check for Client portal authentication
    client_id = session.get('client_portal_id')
    if client_id:
        return Client.query.get(client_id)
    
    # Check for User portal authentication
    user_id = session.get('_user_id')
    if user_id:
        user = User.query.get(user_id)
        if user and user.is_client_portal_user:
            return user.client  # Return the Client object linked to the user
    
    return None


# Make get_current_client available to templates
@client_portal_bp.app_context_processor
def inject_get_current_client():
    """Make get_current_client available in templates"""
    return dict(get_current_client=get_current_client)


def check_client_portal_access():
    """Helper function to check if client has portal access - returns 403 for users without access, redirects to login if not authenticated
    
    Returns:
        Client: The Client object if access is granted
        Response: A redirect response if authentication is needed
        None: If 403 is raised (abort is called)
    """
    # Check for Client portal authentication
    client_id = session.get('client_portal_id')
    if client_id:
        client = Client.query.get(client_id)
        if not client:
            flash(_('Please log in to access the client portal.'), 'error')
            return redirect(url_for('client_portal.login', next=request.url))
        
        if not client.has_portal_access:
            flash(_('Client portal access is not enabled for your account.'), 'error')
            session.pop('client_portal_id', None)  # Clear invalid session
            return redirect(url_for('client_portal.login'))
        
        if not client.is_active:
            flash(_('Your client account is inactive.'), 'error')
            session.pop('client_portal_id', None)  # Clear invalid session
            return redirect(url_for('client_portal.login'))
        
        return client
    
    # Check for User portal authentication
    user_id = session.get('_user_id')
    if user_id:
        try:
            # Convert to int if it's a string (session stores it as string)
            if isinstance(user_id, str):
                user_id = int(user_id)
            # Query with options to ensure we get fresh data and load relationships
            from sqlalchemy.orm import joinedload
            user = User.query.options(joinedload(User.client)).get(user_id)
        except (ValueError, TypeError):
            # Invalid user_id format
            flash(_('Please log in to access the client portal.'), 'error')
            return redirect(url_for('client_portal.login', next=request.url))
        except Exception:
            # If there's a session error, try to rollback and retry
            try:
                db.session.rollback()
                user = User.query.options(joinedload(User.client)).get(user_id)
            except Exception:
                db.session.rollback()
                flash(_('Please log in to access the client portal.'), 'error')
                return redirect(url_for('client_portal.login', next=request.url))
        
        if not user:
            flash(_('Please log in to access the client portal.'), 'error')
            return redirect(url_for('client_portal.login', next=request.url))
        
        # Check portal access directly to ensure we have the latest values
        if not (user.client_portal_enabled and user.client_id is not None):
            # User is logged in but doesn't have portal access - return 403
            abort(403)
        
        if not user.is_active:
            abort(403)
        
        # Ensure client relationship is loaded - query directly if not loaded
        if not user.client and user.client_id:
            # Query the client directly if relationship not loaded
            from app.models import Client
            client = Client.query.get(user.client_id)
            if not client:
                abort(403)
            return client
        
        if not user.client:
            abort(403)
        
        return user.client
    
    # No authentication at all - redirect to login
    flash(_('Please log in to access the client portal.'), 'error')
    return redirect(url_for('client_portal.login', next=request.url))


def get_portal_data(client):
    """Get portal data for a client, handling both Client and User authentication"""
    # Check if this is a User accessing via client portal
    user_id = session.get('_user_id')
    if user_id:
        try:
            # Convert to int if it's a string
            if isinstance(user_id, str):
                user_id = int(user_id)
            db.session.rollback()
            user = User.query.get(user_id)
            if user and user.is_client_portal_user and user.client_id == client.id:
                # Use User's get_client_portal_data method
                return user.get_client_portal_data()
        except Exception:
            db.session.rollback()
            # Fall through to Client method
    
    # Otherwise use Client's get_portal_data method
    return client.get_portal_data()


@client_portal_bp.route('/client-portal/login', methods=['GET', 'POST'])
def login():
    """Client portal login page"""
    if request.method == 'GET':
        # If already logged in, redirect to dashboard
        if get_current_client():
            return redirect(url_for('client_portal.dashboard'))
        return render_template('client_portal/login.html')
    
    # POST - handle login
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    
    if not username or not password:
        flash(_('Username and password are required.'), 'error')
        return render_template('client_portal/login.html')
    
    # Authenticate client
    client = Client.authenticate_portal(username, password)
    
    if not client:
        flash(_('Invalid username or password.'), 'error')
        return render_template('client_portal/login.html')
    
    # Log in the client
    session['client_portal_id'] = client.id
    session.permanent = True
    
    flash(_('Welcome, %(client_name)s!', client_name=client.name), 'success')
    
    # Redirect to intended page or dashboard
    next_page = request.form.get('next') or request.args.get('next')
    if not next_page or not next_page.startswith('/client-portal'):
        next_page = url_for('client_portal.dashboard')
    
    return redirect(next_page)


@client_portal_bp.route('/client-portal/logout')
def logout():
    """Client portal logout"""
    session.pop('client_portal_id', None)
    flash(_('You have been logged out.'), 'info')
    return redirect(url_for('client_portal.login'))


@client_portal_bp.route('/client-portal/set-password', methods=['GET', 'POST'])
def set_password():
    """Set or reset password using token from email"""
    token = request.args.get('token')
    
    if not token:
        flash(_('Invalid or missing password setup token.'), 'error')
        return redirect(url_for('client_portal.login'))
    
    # Find client by token
    client = Client.find_by_password_token(token)
    
    if not client:
        flash(_('Invalid or expired password setup token. Please request a new one.'), 'error')
        return redirect(url_for('client_portal.login'))
    
    if request.method == 'POST':
        password = request.form.get('password', '').strip()
        password_confirm = request.form.get('password_confirm', '').strip()
        
        # Validate password
        if not password:
            flash(_('Password is required.'), 'error')
            return render_template('client_portal/set_password.html', client=client, token=token)
        
        if len(password) < 8:
            flash(_('Password must be at least 8 characters long.'), 'error')
            return render_template('client_portal/set_password.html', client=client, token=token)
        
        if password != password_confirm:
            flash(_('Passwords do not match.'), 'error')
            return render_template('client_portal/set_password.html', client=client, token=token)
        
        # Set password
        client.set_portal_password(password)
        client.clear_password_setup_token()
        
        if not safe_commit('client_set_password', {'client_id': client.id}):
            flash(_('Could not set password due to a database error.'), 'error')
            return render_template('client_portal/set_password.html', client=client, token=token)
        
        flash(_('Password set successfully! You can now log in to the portal.'), 'success')
        return redirect(url_for('client_portal.login'))
    
    return render_template('client_portal/set_password.html', client=client, token=token)


@client_portal_bp.route('/client-portal')
@client_portal_bp.route('/client-portal/dashboard')
def dashboard():
    """Client portal dashboard showing overview of projects, invoices, and time entries"""
    result = check_client_portal_access()
    if not isinstance(result, Client):  # It's a redirect response
        return result
    client = result
    portal_data = get_portal_data(client)
    
    if not portal_data:
        flash(_('Unable to load client portal data.'), 'error')
        return redirect(url_for('client_portal.login'))
    
    # Calculate statistics
    total_projects = len(portal_data['projects'])
    total_invoices = len(portal_data['invoices'])
    total_time_entries = len(portal_data['time_entries'])
    
    # Calculate total hours
    total_hours = sum(entry.duration_hours for entry in portal_data['time_entries'])
    
    # Calculate invoice totals
    total_invoice_amount = sum(inv.total_amount for inv in portal_data['invoices'])
    paid_invoice_amount = sum(
        inv.total_amount for inv in portal_data['invoices'] 
        if inv.payment_status == 'fully_paid'
    )
    unpaid_invoice_amount = sum(
        inv.outstanding_amount for inv in portal_data['invoices']
        if inv.payment_status != 'fully_paid'
    )
    
    # Get recent activity (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_time_entries = [
        entry for entry in portal_data['time_entries']
        if entry.start_time >= thirty_days_ago
    ]
    
    # Group time entries by project
    project_hours = {}
    for entry in portal_data['time_entries']:
        if not entry.project:
            continue
        project_id = entry.project.id
        if project_id not in project_hours:
            project_hours[project_id] = {
                'project': entry.project,
                'hours': 0.0
            }
        project_hours[project_id]['hours'] += entry.duration_hours
    
    return render_template(
        'client_portal/dashboard.html',
        client=client,
        projects=portal_data['projects'],
        invoices=portal_data['invoices'],
        time_entries=portal_data['time_entries'],
        total_projects=total_projects,
        total_invoices=total_invoices,
        total_time_entries=total_time_entries,
        total_hours=round(total_hours, 2),
        total_invoice_amount=total_invoice_amount,
        paid_invoice_amount=paid_invoice_amount,
        unpaid_invoice_amount=unpaid_invoice_amount,
        recent_time_entries=recent_time_entries,
        project_hours=list(project_hours.values())
    )


@client_portal_bp.route('/client-portal/projects')
def projects():
    """List all projects for the client"""
    result = check_client_portal_access()
    if not isinstance(result, Client):
        return result
    client = result
    portal_data = get_portal_data(client)
    
    if not portal_data:
        flash(_('Unable to load client portal data.'), 'error')
        return redirect(url_for('client_portal.dashboard'))
    
    # Calculate hours per project
    project_stats = []
    for project in portal_data['projects']:
        project_entries = [
            entry for entry in portal_data['time_entries']
            if entry.project_id == project.id
        ]
        total_hours = sum(entry.duration_hours for entry in project_entries)
        
        project_stats.append({
            'project': project,
            'total_hours': round(total_hours, 2),
            'entry_count': len(project_entries)
        })
    
    return render_template(
        'client_portal/projects.html',
        client=client,
        project_stats=project_stats
    )


@client_portal_bp.route('/client-portal/invoices')
def invoices():
    """List all invoices for the client"""
    result = check_client_portal_access()
    if not isinstance(result, Client):
        return result
    client = result
    portal_data = get_portal_data(client)
    
    if not portal_data:
        flash(_('Unable to load client portal data.'), 'error')
        return redirect(url_for('client_portal.dashboard'))
    
    # Filter invoices by status if requested
    status_filter = request.args.get('status', 'all')
    filtered_invoices = portal_data['invoices']
    
    if status_filter == 'paid':
        filtered_invoices = [inv for inv in filtered_invoices if inv.payment_status == 'fully_paid']
    elif status_filter == 'unpaid':
        filtered_invoices = [
            inv for inv in filtered_invoices 
            if inv.payment_status in ['unpaid', 'partially_paid']
        ]
    elif status_filter == 'overdue':
        filtered_invoices = [inv for inv in filtered_invoices if inv.is_overdue]
    
    return render_template(
        'client_portal/invoices.html',
        client=client,
        invoices=filtered_invoices,
        status_filter=status_filter
    )


@client_portal_bp.route('/client-portal/invoices/<int:invoice_id>')
def view_invoice(invoice_id):
    """View a specific invoice"""
    result = check_client_portal_access()
    if not isinstance(result, Client):
        return result
    client = result
    
    # Verify invoice belongs to this client
    invoice = Invoice.query.get_or_404(invoice_id)
    if invoice.client_id != client.id:
        flash(_('Invoice not found.'), 'error')
        abort(404)
    
    return render_template(
        'client_portal/invoice_detail.html',
        client=client,
        invoice=invoice
    )


@client_portal_bp.route('/client-portal/quotes')
def quotes():
    """List all quotes visible to the client"""
    result = check_client_portal_access()
    if not isinstance(result, Client):
        return result
    client = result
    
    # Get quotes visible to client
    quotes_list = Quote.query.filter_by(
        client_id=client.id,
        visible_to_client=True
    ).order_by(Quote.created_at.desc()).all()
    
    return render_template(
        'client_portal/quotes.html',
        client=client,
        quotes=quotes_list
    )


@client_portal_bp.route('/client-portal/quotes/<int:quote_id>')
def view_quote(quote_id):
    """View a specific quote"""
    result = check_client_portal_access()
    if not isinstance(result, Client):
        return result
    client = result
    
    # Verify quote belongs to this client and is visible
    quote = Quote.query.get_or_404(quote_id)
    if quote.client_id != client.id or not quote.visible_to_client:
        flash(_('Quote not found.'), 'error')
        abort(404)
    
    return render_template(
        'client_portal/quote_detail.html',
        client=client,
        quote=quote
    )


@client_portal_bp.route('/client-portal/time-entries')
def time_entries():
    """List time entries for the client's projects"""
    result = check_client_portal_access()
    if not isinstance(result, Client):
        return result
    client = result
    portal_data = get_portal_data(client)
    
    if not portal_data:
        flash(_('Unable to load client portal data.'), 'error')
        return redirect(url_for('client_portal.dashboard'))
    
    # Filter by project if requested
    project_id = request.args.get('project_id', type=int)
    filtered_entries = portal_data['time_entries']
    
    if project_id:
        filtered_entries = [
            entry for entry in filtered_entries
            if entry.project_id == project_id
        ]
    
    # Filter by date range if requested
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    if date_from:
        try:
            date_from_dt = datetime.strptime(date_from, '%Y-%m-%d')
            filtered_entries = [
                entry for entry in filtered_entries
                if entry.start_time.date() >= date_from_dt.date()
            ]
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_dt = datetime.strptime(date_to, '%Y-%m-%d')
            filtered_entries = [
                entry for entry in filtered_entries
                if entry.start_time.date() <= date_to_dt.date()
            ]
        except ValueError:
            pass
    
    return render_template(
        'client_portal/time_entries.html',
        client=client,
        projects=portal_data['projects'],
        time_entries=filtered_entries,
        selected_project_id=project_id,
        date_from=date_from,
        date_to=date_to
    )

