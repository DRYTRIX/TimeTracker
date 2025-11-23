"""
Refactored invoice routes using service layer.
This demonstrates the new architecture pattern.

To use: Replace functions in app/routes/invoices.py with these implementations.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_babel import gettext as _
from flask_login import login_required, current_user
from datetime import datetime, timedelta, date
from decimal import Decimal
from app import db, log_event, track_event
from app.services import InvoiceService, ProjectService
from app.repositories import InvoiceRepository, ProjectRepository
from app.models import Invoice, Project, Settings
from app.utils.api_responses import success_response, error_response, paginated_response
from app.utils.event_bus import emit_event
from app.constants import WebhookEvent, InvoiceStatus
from app.utils.posthog_funnels import (
    track_invoice_page_viewed,
    track_invoice_project_selected,
    track_invoice_generated
)

invoices_bp = Blueprint('invoices', __name__)


@invoices_bp.route('/invoices')
@login_required
def list_invoices():
    """List all invoices - REFACTORED VERSION"""
    track_invoice_page_viewed(current_user.id)
    
    # Get filter parameters
    status = request.args.get('status', '').strip()
    payment_status = request.args.get('payment_status', '').strip()
    search_query = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)
    
    # Use repository
    invoice_repo = InvoiceRepository()
    
    # Build query
    if current_user.is_admin:
        query = invoice_repo.query()
    else:
        query = invoice_repo.query().filter_by(created_by=current_user.id)
    
    # Apply filters
    if status:
        query = query.filter(Invoice.status == status)
    
    if payment_status:
        query = query.filter(Invoice.payment_status == payment_status)
    
    if search_query:
        like = f"%{search_query}%"
        query = query.filter(
            db.or_(
                Invoice.invoice_number.ilike(like),
                Invoice.client_name.ilike(like)
            )
        )
    
    # Paginate
    invoices_pagination = query.order_by(Invoice.created_at.desc()).paginate(
        page=page,
        per_page=50,
        error_out=False
    )
    
    # Calculate overdue status
    today = date.today()
    for invoice in invoices_pagination.items:
        invoice._is_overdue = (
            invoice.due_date and
            invoice.due_date < today and
            invoice.payment_status != 'fully_paid' and
            invoice.status != 'paid'
        )
    
    # Get summary statistics
    if current_user.is_admin:
        all_invoices = invoice_repo.get_all()
    else:
        all_invoices = invoice_repo.find_by(created_by=current_user.id)
    
    total_invoices = len(all_invoices)
    total_amount = sum(inv.total_amount for inv in all_invoices)
    actual_paid_amount = sum(inv.amount_paid or 0 for inv in all_invoices)
    fully_paid_amount = sum(inv.total_amount for inv in all_invoices if inv.payment_status == 'fully_paid')
    partially_paid_amount = sum(inv.amount_paid or 0 for inv in all_invoices if inv.payment_status == 'partially_paid')
    overdue_amount = sum(inv.outstanding_amount for inv in all_invoices if inv.status == 'overdue')
    
    summary = {
        'total_invoices': total_invoices,
        'total_amount': float(total_amount),
        'paid_amount': float(actual_paid_amount),
        'fully_paid_amount': float(fully_paid_amount),
        'partially_paid_amount': float(partially_paid_amount),
        'overdue_amount': float(overdue_amount),
        'outstanding_amount': float(total_amount - actual_paid_amount)
    }
    
    return render_template(
        'invoices/list.html',
        invoices=invoices_pagination.items,
        pagination=invoices_pagination,
        summary=summary
    )


@invoices_bp.route('/invoices/create', methods=['GET', 'POST'])
@login_required
def create_invoice():
    """Create a new invoice - REFACTORED VERSION"""
    if request.method == 'POST':
        # Get form data
        project_id = request.form.get('project_id', type=int)
        client_name = request.form.get('client_name', '').strip()
        client_email = request.form.get('client_email', '').strip()
        client_address = request.form.get('client_address', '').strip()
        due_date_str = request.form.get('due_date', '').strip()
        tax_rate = request.form.get('tax_rate', '0').strip()
        notes = request.form.get('notes', '').strip()
        terms = request.form.get('terms', '').strip()
        
        # Validate required fields
        if not project_id or not client_name or not due_date_str:
            flash('Project, client name, and due date are required', 'error')
            return render_template('invoices/create.html')
        
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid due date format', 'error')
            return render_template('invoices/create.html')
        
        try:
            tax_rate = Decimal(tax_rate)
        except ValueError:
            flash('Invalid tax rate format', 'error')
            return render_template('invoices/create.html')
        
        # Get project
        project_repo = ProjectRepository()
        project = project_repo.get_by_id(project_id)
        if not project:
            flash('Selected project not found', 'error')
            return render_template('invoices/create.html')
        
        # Generate invoice number
        invoice_repo = InvoiceRepository()
        invoice_number = invoice_repo.generate_invoice_number()
        
        # Track project selected
        track_invoice_project_selected(current_user.id, {
            "project_id": project_id,
            "has_email": bool(client_email),
            "has_tax": tax_rate > 0
        })
        
        # Get currency from settings
        settings = Settings.get_settings()
        currency_code = settings.currency if settings else 'USD'
        
        # Create invoice using repository
        invoice = invoice_repo.create(
            invoice_number=invoice_number,
            project_id=project_id,
            client_name=client_name,
            due_date=due_date,
            created_by=current_user.id,
            client_id=project.client_id,
            quote_id=project.quote_id if hasattr(project, 'quote_id') else None,
            client_email=client_email,
            client_address=client_address,
            tax_rate=tax_rate,
            notes=notes,
            terms=terms,
            currency_code=currency_code,
            status=InvoiceStatus.DRAFT.value
        )
        
        if not safe_commit('create_invoice', {'project_id': project_id, 'created_by': current_user.id}):
            flash('Could not create invoice due to a database error', 'error')
            return render_template('invoices/create.html')
        
        # Track invoice created
        track_invoice_generated(current_user.id, {
            "invoice_id": invoice.id,
            "invoice_number": invoice_number,
            "has_tax": float(tax_rate) > 0,
            "has_notes": bool(notes)
        })
        
        # Emit domain event
        emit_event(WebhookEvent.INVOICE_CREATED.value, {
            'invoice_id': invoice.id,
            'project_id': project_id,
            'client_id': project.client_id
        })
        
        flash(f'Invoice {invoice_number} created successfully', 'success')
        return redirect(url_for('invoices.edit_invoice', invoice_id=invoice.id))
    
    # GET request - show form
    project_repo = ProjectRepository()
    projects = project_repo.get_billable_projects()
    settings = Settings.get_settings()
    default_due_date = (datetime.utcnow() + timedelta(days=30)).strftime('%Y-%m-%d')
    
    return render_template(
        'invoices/create.html',
        projects=projects,
        settings=settings,
        default_due_date=default_due_date
    )


@invoices_bp.route('/invoices/<int:invoice_id>/mark-sent', methods=['POST'])
@login_required
def mark_invoice_sent(invoice_id):
    """Mark invoice as sent - REFACTORED VERSION"""
    # Use service layer
    service = InvoiceService()
    result = service.mark_as_sent(invoice_id)
    
    if result['success']:
        # Emit domain event
        emit_event(WebhookEvent.INVOICE_SENT.value, {
            'invoice_id': invoice_id
        })
        
        flash(_('Invoice marked as sent'), 'success')
    else:
        flash(_(result['message']), 'error')
    
    return redirect(url_for('invoices.view_invoice', invoice_id=invoice_id))


@invoices_bp.route('/invoices/<int:invoice_id>/mark-paid', methods=['POST'])
@login_required
def mark_invoice_paid(invoice_id):
    """Mark invoice as paid - REFACTORED VERSION"""
    payment_date_str = request.form.get('payment_date', '').strip()
    payment_method = request.form.get('payment_method', '').strip()
    payment_reference = request.form.get('payment_reference', '').strip()
    
    payment_date = None
    if payment_date_str:
        try:
            payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date()
        except ValueError:
            payment_date = date.today()
    else:
        payment_date = date.today()
    
    # Use service layer
    service = InvoiceService()
    result = service.mark_as_paid(
        invoice_id=invoice_id,
        payment_date=payment_date,
        payment_method=payment_method or None,
        payment_reference=payment_reference or None
    )
    
    if result['success']:
        # Emit domain event
        emit_event(WebhookEvent.INVOICE_PAID.value, {
            'invoice_id': invoice_id,
            'payment_date': payment_date.isoformat()
        })
        
        flash(_('Invoice marked as paid'), 'success')
    else:
        flash(_(result['message']), 'error')
    
    return redirect(url_for('invoices.view_invoice', invoice_id=invoice_id))

