from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db, log_event, track_event
from app.models import User, Project, TimeEntry, Invoice, InvoiceItem, Settings, RateOverride, ProjectCost, ExtraGood, Expense
from datetime import datetime, timedelta, date
from decimal import Decimal, InvalidOperation
import io
import csv
import json
from app.utils.db import safe_commit
from app.utils.excel_export import create_invoices_list_excel
from app.utils.posthog_funnels import (
    track_invoice_page_viewed,
    track_invoice_project_selected,
    track_invoice_previewed,
    track_invoice_generated
)

invoices_bp = Blueprint('invoices', __name__)

@invoices_bp.route('/invoices')
@login_required
def list_invoices():
    """List all invoices"""
    # Track invoice page viewed
    track_invoice_page_viewed(current_user.id)
    
    # Get invoices (scope by user unless admin)
    if current_user.is_admin:
        invoices = Invoice.query.order_by(Invoice.created_at.desc()).all()
    else:
        invoices = Invoice.query.filter_by(created_by=current_user.id).order_by(Invoice.created_at.desc()).all()
    
    # Get summary statistics
    total_invoices = len(invoices)
    total_amount = sum(invoice.total_amount for invoice in invoices)
    
    # Use payment tracking for more accurate statistics
    actual_paid_amount = sum(invoice.amount_paid or 0 for invoice in invoices)
    fully_paid_amount = sum(invoice.total_amount for invoice in invoices if invoice.payment_status == 'fully_paid')
    partially_paid_amount = sum(invoice.amount_paid or 0 for invoice in invoices if invoice.payment_status == 'partially_paid')
    overdue_amount = sum(invoice.outstanding_amount for invoice in invoices if invoice.status == 'overdue')
    
    summary = {
        'total_invoices': total_invoices,
        'total_amount': float(total_amount),
        'paid_amount': float(actual_paid_amount),
        'fully_paid_amount': float(fully_paid_amount),
        'partially_paid_amount': float(partially_paid_amount),
        'overdue_amount': float(overdue_amount),
        'outstanding_amount': float(total_amount - actual_paid_amount)
    }
    
    return render_template('invoices/list.html', invoices=invoices, summary=summary)

@invoices_bp.route('/invoices/create', methods=['GET', 'POST'])
@login_required
def create_invoice():
    """Create a new invoice"""
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
        project = Project.query.get(project_id)
        if not project:
            flash('Selected project not found', 'error')
            return render_template('invoices/create.html')
        
        # Generate invoice number
        invoice_number = Invoice.generate_invoice_number()
        
        # Track project selected for invoice
        track_invoice_project_selected(current_user.id, {
            "project_id": project_id,
            "has_email": bool(client_email),
            "has_tax": tax_rate > 0
        })
        
        # Get currency from settings
        settings = Settings.get_settings()
        currency_code = settings.currency if settings else 'USD'
        
        # Create invoice
        invoice = Invoice(
            invoice_number=invoice_number,
            project_id=project_id,
            client_name=client_name,
            due_date=due_date,
            created_by=current_user.id,
            client_id=project.client_id,
            client_email=client_email,
            client_address=client_address,
            tax_rate=tax_rate,
            notes=notes,
            terms=terms,
            currency_code=currency_code
        )
        
        db.session.add(invoice)
        if not safe_commit('create_invoice', {'invoice_number': invoice_number, 'project_id': project_id}):
            flash('Could not create invoice due to a database error. Please check server logs.', 'error')
            return render_template('invoices/create.html')
        
        # Track invoice created
        track_invoice_generated(current_user.id, {
            "invoice_id": invoice.id,
            "invoice_number": invoice_number,
            "has_tax": float(tax_rate) > 0,
            "has_notes": bool(notes)
        })
        
        flash(f'Invoice {invoice_number} created successfully', 'success')
        return redirect(url_for('invoices.edit_invoice', invoice_id=invoice.id))
    
    # GET request - show form
    projects = Project.query.filter_by(status='active', billable=True).order_by(Project.name).all()
    settings = Settings.get_settings()
    
    # Set default due date to 30 days from now
    default_due_date = (datetime.utcnow() + timedelta(days=30)).strftime('%Y-%m-%d')
    
    return render_template('invoices/create.html', 
                         projects=projects, 
                         settings=settings,
                         default_due_date=default_due_date)

@invoices_bp.route('/invoices/<int:invoice_id>')
@login_required
def view_invoice(invoice_id):
    """View invoice details"""
    invoice = Invoice.query.get_or_404(invoice_id)
    
    # Check access permissions
    if not current_user.is_admin and invoice.created_by != current_user.id:
        flash('You do not have permission to view this invoice', 'error')
        return redirect(url_for('invoices.list_invoices'))
    
    # Track invoice previewed
    track_invoice_previewed(current_user.id, {
        "invoice_id": invoice.id,
        "invoice_number": invoice.invoice_number
    })
    
    return render_template('invoices/view.html', invoice=invoice)

@invoices_bp.route('/invoices/<int:invoice_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_invoice(invoice_id):
    """Edit invoice"""
    invoice = Invoice.query.get_or_404(invoice_id)
    
    # Check access permissions
    if not current_user.is_admin and invoice.created_by != current_user.id:
        flash('You do not have permission to edit this invoice', 'error')
        return redirect(url_for('invoices.list_invoices'))
    
    if request.method == 'POST':
        # Update invoice details
        invoice.client_name = request.form.get('client_name', '').strip()
        invoice.client_email = request.form.get('client_email', '').strip()
        invoice.client_address = request.form.get('client_address', '').strip()
        invoice.due_date = datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date()
        invoice.tax_rate = Decimal(request.form.get('tax_rate', '0'))
        invoice.notes = request.form.get('notes', '').strip()
        invoice.terms = request.form.get('terms', '').strip()
        
        # Update items
        item_ids = request.form.getlist('item_id[]')
        descriptions = request.form.getlist('description[]')
        quantities = request.form.getlist('quantity[]')
        unit_prices = request.form.getlist('unit_price[]')
        
        # Remove existing items
        invoice.items.delete()
        
        # Add new items
        for i in range(len(descriptions)):
            if descriptions[i].strip() and quantities[i] and unit_prices[i]:
                try:
                    quantity = Decimal(quantities[i])
                    unit_price = Decimal(unit_prices[i])
                    
                    item = InvoiceItem(
                        invoice_id=invoice.id,
                        description=descriptions[i].strip(),
                        quantity=quantity,
                        unit_price=unit_price
                    )
                    db.session.add(item)
                except ValueError:
                    flash(f'Invalid quantity or price for item {i+1}', 'error')
                    continue
        
        # Update expenses
        expense_ids = request.form.getlist('expense_id[]')
        
        # Unlink expenses not in the list
        for expense in invoice.expenses.all():
            if str(expense.id) not in expense_ids:
                expense.unmark_as_invoiced()
        
        # Link expenses in the list
        if expense_ids:
            for expense_id in expense_ids:
                try:
                    expense = Expense.query.get(int(expense_id))
                    if expense and not expense.invoiced:
                        expense.mark_as_invoiced(invoice.id)
                except (ValueError, AttributeError):
                    continue
        
        # Update extra goods
        good_ids = request.form.getlist('good_id[]')
        good_names = request.form.getlist('good_name[]')
        good_descriptions = request.form.getlist('good_description[]')
        good_categories = request.form.getlist('good_category[]')
        good_quantities = request.form.getlist('good_quantity[]')
        good_unit_prices = request.form.getlist('good_unit_price[]')
        good_skus = request.form.getlist('good_sku[]')
        
        # Remove existing extra goods
        invoice.extra_goods.delete()
        
        # Add new extra goods
        for i in range(len(good_names)):
            if good_names[i].strip() and good_quantities[i] and good_unit_prices[i]:
                try:
                    quantity = Decimal(good_quantities[i])
                    unit_price = Decimal(good_unit_prices[i])
                    
                    good = ExtraGood(
                        name=good_names[i].strip(),
                        description=good_descriptions[i].strip() if i < len(good_descriptions) and good_descriptions[i] else None,
                        category=good_categories[i] if i < len(good_categories) and good_categories[i] else 'product',
                        quantity=quantity,
                        unit_price=unit_price,
                        sku=good_skus[i].strip() if i < len(good_skus) and good_skus[i] else None,
                        invoice_id=invoice.id,
                        created_by=current_user.id,
                        currency_code=invoice.currency_code
                    )
                    db.session.add(good)
                except ValueError:
                    flash(f'Invalid quantity or price for extra good {i+1}', 'error')
                    continue
        
        # Calculate totals
        invoice.calculate_totals()
        if not safe_commit('edit_invoice', {'invoice_id': invoice.id}):
            flash('Could not update invoice due to a database error. Please check server logs.', 'error')
            return render_template('invoices/edit.html', invoice=invoice, projects=Project.query.filter_by(status='active').order_by(Project.name).all())
        
        flash('Invoice updated successfully', 'success')
        return redirect(url_for('invoices.view_invoice', invoice_id=invoice.id))
    
    # GET request - show edit form
    projects = Project.query.filter_by(status='active').order_by(Project.name).all()
    return render_template('invoices/edit.html', invoice=invoice, projects=projects)

@invoices_bp.route('/invoices/<int:invoice_id>/status', methods=['POST'])
@login_required
def update_invoice_status(invoice_id):
    """Update invoice status"""
    invoice = Invoice.query.get_or_404(invoice_id)
    
    # Check access permissions
    if not current_user.is_admin and invoice.created_by != current_user.id:
        return jsonify({'error': 'Permission denied'}), 403
    
    new_status = request.form.get('new_status')
    if new_status not in ['draft', 'sent', 'paid', 'cancelled']:
        return jsonify({'error': 'Invalid status'}), 400
    
    invoice.status = new_status
    
    # Auto-update payment status if marking as paid
    if new_status == 'paid' and invoice.payment_status != 'fully_paid':
        invoice.amount_paid = invoice.total_amount
        invoice.payment_status = 'fully_paid'
        if not invoice.payment_date:
            invoice.payment_date = datetime.utcnow().date()
    
    if not safe_commit('update_invoice_status', {'invoice_id': invoice.id, 'status': new_status}):
        return jsonify({'error': 'Database error while updating status'}), 500
    
    return jsonify({'success': True, 'status': new_status})


@invoices_bp.route('/invoices/<int:invoice_id>/delete', methods=['POST'])
@login_required
def delete_invoice(invoice_id):
    """Delete invoice"""
    invoice = Invoice.query.get_or_404(invoice_id)
    
    # Check access permissions
    if not current_user.is_admin and invoice.created_by != current_user.id:
        flash('You do not have permission to delete this invoice', 'error')
        return redirect(url_for('invoices.list_invoices'))
    
    invoice_number = invoice.invoice_number
    db.session.delete(invoice)
    if not safe_commit('delete_invoice', {'invoice_id': invoice.id}):
        flash('Could not delete invoice due to a database error. Please check server logs.', 'error')
        return redirect(url_for('invoices.list_invoices'))
    
    flash(f'Invoice {invoice_number} deleted successfully', 'success')
    return redirect(url_for('invoices.list_invoices'))

@invoices_bp.route('/invoices/<int:invoice_id>/generate-from-time', methods=['GET', 'POST'])
@login_required
def generate_from_time(invoice_id):
    """Generate invoice items from time entries"""
    invoice = Invoice.query.get_or_404(invoice_id)
    
    # Check access permissions
    if not current_user.is_admin and invoice.created_by != current_user.id:
        flash('You do not have permission to edit this invoice', 'error')
        return redirect(url_for('invoices.list_invoices'))
    
    if request.method == 'POST':
        # Get selected time entries, costs, expenses, and extra goods
        selected_entries = request.form.getlist('time_entries[]')
        selected_costs = request.form.getlist('project_costs[]')
        selected_expenses = request.form.getlist('expenses[]')
        selected_goods = request.form.getlist('extra_goods[]')
        
        if not selected_entries and not selected_costs and not selected_expenses and not selected_goods:
            flash('No time entries, costs, expenses, or extra goods selected', 'error')
            return redirect(url_for('invoices.generate_from_time', invoice_id=invoice.id))
        
        # Clear existing items
        invoice.items.delete()
        
        # Process time entries
        if selected_entries:
            # Group time entries by task/project and create invoice items
            time_entries = TimeEntry.query.filter(TimeEntry.id.in_(selected_entries)).all()
            
            # Group by task (if available) or project
            grouped_entries = {}
            for entry in time_entries:
                if entry.task_id:
                    key = f"task_{entry.task_id}"
                    if key not in grouped_entries:
                        grouped_entries[key] = {
                            'description': f"Task: {entry.task.name if entry.task else 'Unknown Task'}",
                            'entries': [],
                            'total_hours': 0
                        }
                else:
                    key = f"project_{entry.project_id}"
                    if key not in grouped_entries:
                        grouped_entries[key] = {
                            'description': f"Project: {entry.project.name}",
                            'entries': [],
                            'total_hours': 0
                        }
                
                grouped_entries[key]['entries'].append(entry)
                grouped_entries[key]['total_hours'] += entry.duration_hours
            
            # Create invoice items from time entries
            for group in grouped_entries.values():
                # Resolve effective rate (project override -> project rate -> client default)
                hourly_rate = RateOverride.resolve_rate(invoice.project)
                
                item = InvoiceItem(
                    invoice_id=invoice.id,
                    description=group['description'],
                    quantity=group['total_hours'],
                    unit_price=hourly_rate,
                    time_entry_ids=','.join(str(entry.id) for entry in group['entries'])
                )
                db.session.add(item)
        
        # Process project costs
        if selected_costs:
            costs = ProjectCost.query.filter(ProjectCost.id.in_(selected_costs)).all()
            
            for cost in costs:
                # Create invoice item for each cost
                item = InvoiceItem(
                    invoice_id=invoice.id,
                    description=f"{cost.description} ({cost.category.title()})",
                    quantity=1,  # Costs are typically a single unit
                    unit_price=cost.amount
                )
                db.session.add(item)
                
                # Mark cost as invoiced
                cost.mark_as_invoiced(invoice.id)
        
        # Process expenses
        if selected_expenses:
            expenses = Expense.query.filter(Expense.id.in_(selected_expenses)).all()
            
            for expense in expenses:
                # Mark expense as invoiced (this links it to the invoice)
                expense.mark_as_invoiced(invoice.id)
        
        # Process extra goods from project
        if selected_goods:
            goods = ExtraGood.query.filter(ExtraGood.id.in_(selected_goods)).all()
            
            for good in goods:
                # Create a copy of the good for the invoice
                invoice_good = ExtraGood(
                    name=good.name,
                    description=good.description,
                    category=good.category,
                    quantity=good.quantity,
                    unit_price=good.unit_price,
                    sku=good.sku,
                    invoice_id=invoice.id,
                    created_by=current_user.id,
                    currency_code=good.currency_code
                )
                db.session.add(invoice_good)
        
        # Calculate totals
        invoice.calculate_totals()
        if not safe_commit('generate_from_time', {'invoice_id': invoice.id}):
            flash('Could not generate items due to a database error. Please check server logs.', 'error')
            return redirect(url_for('invoices.edit_invoice', invoice_id=invoice.id))
        
        flash('Invoice items generated successfully from time entries and costs', 'success')
        return redirect(url_for('invoices.edit_invoice', invoice_id=invoice.id))
    
    # GET request - show time entry and cost selection
    # Get unbilled time entries for this project
    time_entries = TimeEntry.query.filter(
        TimeEntry.project_id == invoice.project_id,
        TimeEntry.end_time.isnot(None),
        TimeEntry.billable == True
    ).order_by(TimeEntry.start_time.desc()).all()
    
    # Filter out entries already billed in other invoices
    unbilled_entries = []
    for entry in time_entries:
        # Check if this entry is already billed in another invoice
        already_billed = False
        for other_invoice in invoice.project.invoices:
            if other_invoice.id != invoice.id:
                for item in other_invoice.items:
                    if item.time_entry_ids and str(entry.id) in item.time_entry_ids.split(','):
                        already_billed = True
                        break
                if already_billed:
                    break
        
        if not already_billed:
            unbilled_entries.append(entry)
    
    # Get uninvoiced billable costs for this project
    unbilled_costs = ProjectCost.get_uninvoiced_costs(invoice.project_id)
    
    # Get uninvoiced billable expenses for this project
    unbilled_expenses = Expense.get_uninvoiced_expenses(project_id=invoice.project_id)
    
    # Get billable extra goods for this project (not yet on an invoice)
    project_goods = ExtraGood.query.filter(
        ExtraGood.project_id == invoice.project_id,
        ExtraGood.invoice_id.is_(None),
        ExtraGood.billable == True
    ).order_by(ExtraGood.created_at.desc()).all()
    
    # Calculate totals
    total_available_hours = sum(entry.duration_hours for entry in unbilled_entries)
    total_available_costs = sum(float(cost.amount) for cost in unbilled_costs)
    total_available_expenses = sum(float(expense.total_amount) for expense in unbilled_expenses)
    total_available_goods = sum(float(good.total_amount) for good in project_goods)
    
    # Get currency from settings
    settings = Settings.get_settings()
    currency = settings.currency if settings else 'USD'
    
    return render_template('invoices/generate_from_time.html', 
                         invoice=invoice, 
                         time_entries=unbilled_entries,
                         project_costs=unbilled_costs,
                         expenses=unbilled_expenses,
                         extra_goods=project_goods,
                         total_available_hours=total_available_hours,
                         total_available_costs=total_available_costs,
                         total_available_expenses=total_available_expenses,
                         total_available_goods=total_available_goods,
                         currency=currency)

@invoices_bp.route('/invoices/<int:invoice_id>/export/csv')
@login_required
def export_invoice_csv(invoice_id):
    """Export invoice as CSV"""
    invoice = Invoice.query.get_or_404(invoice_id)
    
    # Check access permissions
    if not current_user.is_admin and invoice.created_by != current_user.id:
        flash('You do not have permission to export this invoice', 'error')
        return redirect(url_for('invoices.list_invoices'))
    
    # Create CSV output
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Invoice Number', invoice.invoice_number])
    writer.writerow(['Client', invoice.client_name])
    writer.writerow(['Issue Date', invoice.issue_date.strftime('%Y-%m-%d')])
    writer.writerow(['Due Date', invoice.due_date.strftime('%Y-%m-%d')])
    writer.writerow(['Status', invoice.status])
    writer.writerow([])
    
    # Write items
    writer.writerow(['Description', 'Quantity (Hours)', 'Unit Price', 'Total Amount'])
    for item in invoice.items:
        writer.writerow([
            item.description,
            float(item.quantity),
            float(item.unit_price),
            float(item.total_amount)
        ])
    
    # Write expenses
    for expense in invoice.expenses:
        writer.writerow([
            f"{expense.title} ({expense.category})",
            1,
            float(expense.total_amount),
            float(expense.total_amount)
        ])
    
    # Write goods
    for good in invoice.extra_goods:
        writer.writerow([
            good.name,
            float(good.quantity),
            float(good.unit_price),
            float(good.total_amount)
        ])
    
    writer.writerow([])
    writer.writerow(['Subtotal', '', '', float(invoice.subtotal)])
    writer.writerow(['Tax Rate', '', '', f'{float(invoice.tax_rate)}%'])
    writer.writerow(['Tax Amount', '', '', float(invoice.tax_amount)])
    writer.writerow(['Total Amount', '', '', float(invoice.total_amount)])
    
    output.seek(0)
    
    filename = f'invoice_{invoice.invoice_number}.csv'
    
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )

@invoices_bp.route('/invoices/<int:invoice_id>/export/pdf')
@login_required
def export_invoice_pdf(invoice_id):
    """Export invoice as PDF with optional page size selection"""
    # Debug logging - output to stdout for Docker
    import sys
    print(f"\n{'='*80}", file=sys.stdout, flush=True)
    print(f"INVOICE EXPORT ROUTE CALLED - Invoice ID: {invoice_id}", file=sys.stdout, flush=True)
    print(f"{'='*80}", file=sys.stdout, flush=True)
    
    invoice = Invoice.query.get_or_404(invoice_id)
    print(f"[ROUTE DEBUG] Invoice found: {invoice.invoice_number}", file=sys.stdout, flush=True)
    
    if not current_user.is_admin and invoice.created_by != current_user.id:
        print(f"[ROUTE DEBUG] Permission denied", file=sys.stdout, flush=True)
        flash(_('You do not have permission to export this invoice'), 'error')
        return redirect(request.referrer or url_for('invoices.list_invoices'))
    
    # Get page size from query parameter, default to A4
    page_size = request.args.get('size', 'A4')
    print(f"[ROUTE DEBUG] Page size from request: '{page_size}'", file=sys.stdout, flush=True)
    
    # Validate page size
    valid_sizes = ['A4', 'Letter', 'Legal', 'A3', 'A5', 'Tabloid']
    if page_size not in valid_sizes:
        print(f"[ROUTE DEBUG] Invalid page size, defaulting to A4", file=sys.stdout, flush=True)
        page_size = 'A4'
    
    print(f"[ROUTE DEBUG] Final page size: '{page_size}'", file=sys.stdout, flush=True)
    print(f"[ROUTE DEBUG] Calling InvoicePDFGenerator.generate_pdf()...", file=sys.stdout, flush=True)
    
    try:
        from app.utils.pdf_generator import InvoicePDFGenerator
        settings = Settings.get_settings()
        print(f"[ROUTE DEBUG] Creating InvoicePDFGenerator with page_size='{page_size}'", file=sys.stdout, flush=True)
        pdf_generator = InvoicePDFGenerator(invoice, settings=settings, page_size=page_size)
        print(f"[ROUTE DEBUG] Calling pdf_generator.generate_pdf()...", file=sys.stdout, flush=True)
        pdf_bytes = pdf_generator.generate_pdf()
        print(f"[ROUTE DEBUG] PDF generated successfully, size: {len(pdf_bytes)} bytes", file=sys.stdout, flush=True)
        filename = f'invoice_{invoice.invoice_number}_{page_size}.pdf'
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        import sys
        import traceback
        print(f"[ROUTE DEBUG] Exception in PDF generation: {e}", file=sys.stdout, flush=True)
        print(f"[ROUTE DEBUG] Traceback:", file=sys.stdout, flush=True)
        print(traceback.format_exc(), file=sys.stdout, flush=True)
        try:
            print(f"[ROUTE DEBUG] Falling back to InvoicePDFGeneratorFallback", file=sys.stdout, flush=True)
            from app.utils.pdf_generator_fallback import InvoicePDFGeneratorFallback
            settings = Settings.get_settings()
            pdf_generator = InvoicePDFGeneratorFallback(invoice, settings=settings)
            pdf_bytes = pdf_generator.generate_pdf()
            print(f"[ROUTE DEBUG] Fallback PDF generated successfully", file=sys.stdout, flush=True)
            filename = f'invoice_{invoice.invoice_number}_{page_size}.pdf'
            return send_file(
                io.BytesIO(pdf_bytes),
                mimetype='application/pdf',
                as_attachment=True,
                download_name=filename
            )
        except Exception as fallback_error:
            flash(_('PDF generation failed: %(err)s. Fallback also failed: %(fb)s', err=str(e), fb=str(fallback_error)), 'error')
            return redirect(request.referrer or url_for('invoices.view_invoice', invoice_id=invoice.id))

@invoices_bp.route('/invoices/<int:invoice_id>/duplicate')
@login_required
def duplicate_invoice(invoice_id):
    """Duplicate an existing invoice"""
    original_invoice = Invoice.query.get_or_404(invoice_id)
    
    # Check access permissions
    if not current_user.is_admin and original_invoice.created_by != current_user.id:
        flash('You do not have permission to duplicate this invoice', 'error')
        return redirect(url_for('invoices.list_invoices'))
    
    # Generate new invoice number
    new_invoice_number = Invoice.generate_invoice_number()
    
    # Create new invoice
    new_invoice = Invoice(
        invoice_number=new_invoice_number,
        project_id=original_invoice.project_id,
        client_name=original_invoice.client_name,
        client_email=original_invoice.client_email,
        client_address=original_invoice.client_address,
        due_date=original_invoice.due_date + timedelta(days=30),  # 30 days from original due date
        created_by=current_user.id,
        client_id=original_invoice.client_id,
        tax_rate=original_invoice.tax_rate,
        notes=original_invoice.notes,
        terms=original_invoice.terms,
        currency_code=original_invoice.currency_code
    )
    
    db.session.add(new_invoice)
    if not safe_commit('duplicate_invoice_create', {'source_invoice_id': original_invoice.id, 'new_invoice_number': new_invoice_number}):
        flash('Could not duplicate invoice due to a database error. Please check server logs.', 'error')
        return redirect(url_for('invoices.list_invoices'))
    
    # Duplicate items
    for original_item in original_invoice.items:
        new_item = InvoiceItem(
            invoice_id=new_invoice.id,
            description=original_item.description,
            quantity=original_item.quantity,
            unit_price=original_item.unit_price
        )
        db.session.add(new_item)
    
    # Duplicate extra goods
    for original_good in original_invoice.extra_goods:
        new_good = ExtraGood(
            name=original_good.name,
            description=original_good.description,
            category=original_good.category,
            quantity=original_good.quantity,
            unit_price=original_good.unit_price,
            sku=original_good.sku,
            invoice_id=new_invoice.id,
            created_by=current_user.id,
            currency_code=original_good.currency_code
        )
        db.session.add(new_good)
    
    # Calculate totals
    new_invoice.calculate_totals()
    if not safe_commit('duplicate_invoice_finalize', {'invoice_id': new_invoice.id}):
        flash('Could not finalize duplicated invoice due to a database error. Please check server logs.', 'error')
        return redirect(url_for('invoices.list_invoices'))
    
    flash(f'Invoice {new_invoice_number} created as duplicate', 'success')
    return redirect(url_for('invoices.edit_invoice', invoice_id=new_invoice.id))


@invoices_bp.route('/invoices/export/excel')
@login_required
def export_invoices_excel():
    """Export invoice list as Excel file"""
    # Get invoices (scope by user unless admin)
    if current_user.is_admin:
        invoices = Invoice.query.order_by(Invoice.created_at.desc()).all()
    else:
        invoices = Invoice.query.filter_by(created_by=current_user.id).order_by(Invoice.created_at.desc()).all()
    
    # Create Excel file
    output, filename = create_invoices_list_excel(invoices)
    
    # Track Excel export event
    log_event("export.excel", 
             user_id=current_user.id, 
             export_type="invoices_list",
             num_rows=len(invoices))
    track_event(current_user.id, "export.excel", {
        "export_type": "invoices_list",
        "num_rows": len(invoices)
    })
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )
