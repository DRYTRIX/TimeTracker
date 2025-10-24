from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, current_app
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db, log_event, track_event
from app.models import Expense, Project, Client, User
from datetime import datetime, date, timedelta
from decimal import Decimal
from app.utils.db import safe_commit
import csv
import io
import os
from werkzeug.utils import secure_filename

expenses_bp = Blueprint('expenses', __name__)

# File upload configuration
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
UPLOAD_FOLDER = 'uploads/receipts'


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@expenses_bp.route('/expenses')
@login_required
def list_expenses():
    """List all expenses with filters"""
    # Track page view
    from app import track_page_view
    track_page_view("expenses_list")
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    
    # Filter parameters
    status = request.args.get('status', '').strip()
    category = request.args.get('category', '').strip()
    project_id = request.args.get('project_id', type=int)
    client_id = request.args.get('client_id', type=int)
    user_id = request.args.get('user_id', type=int)
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    search = request.args.get('search', '').strip()
    billable = request.args.get('billable', '').strip()
    reimbursable = request.args.get('reimbursable', '').strip()
    
    # Build query
    query = Expense.query
    
    # Non-admin users can only see their own expenses or expenses they approved
    if not current_user.is_admin:
        query = query.filter(
            db.or_(
                Expense.user_id == current_user.id,
                Expense.approved_by == current_user.id
            )
        )
    
    # Apply filters
    if status:
        query = query.filter(Expense.status == status)
    
    if category:
        query = query.filter(Expense.category == category)
    
    if project_id:
        query = query.filter(Expense.project_id == project_id)
    
    if client_id:
        query = query.filter(Expense.client_id == client_id)
    
    if user_id and current_user.is_admin:
        query = query.filter(Expense.user_id == user_id)
    
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(Expense.expense_date >= start)
        except ValueError:
            pass
    
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(Expense.expense_date <= end)
        except ValueError:
            pass
    
    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                Expense.title.ilike(like),
                Expense.description.ilike(like),
                Expense.vendor.ilike(like),
                Expense.notes.ilike(like)
            )
        )
    
    if billable == 'true':
        query = query.filter(Expense.billable == True)
    elif billable == 'false':
        query = query.filter(Expense.billable == False)
    
    if reimbursable == 'true':
        query = query.filter(Expense.reimbursable == True)
    elif reimbursable == 'false':
        query = query.filter(Expense.reimbursable == False)
    
    # Paginate
    expenses_pagination = query.order_by(Expense.expense_date.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    # Get filter options
    projects = Project.query.filter_by(status='active').order_by(Project.name).all()
    clients = Client.get_active_clients()
    categories = Expense.get_expense_categories()
    
    # Get users for admin filter
    users = []
    if current_user.is_admin:
        users = User.query.filter_by(is_active=True).order_by(User.username).all()
    
    # Calculate totals for current filters (without pagination)
    total_amount = 0
    total_count = query.count()
    
    if total_count > 0:
        total_query = db.session.query(
            db.func.sum(Expense.amount + db.func.coalesce(Expense.tax_amount, 0))
        )
        
        # Apply same filters
        if status:
            total_query = total_query.filter(Expense.status == status)
        if category:
            total_query = total_query.filter(Expense.category == category)
        if project_id:
            total_query = total_query.filter(Expense.project_id == project_id)
        if client_id:
            total_query = total_query.filter(Expense.client_id == client_id)
        if user_id and current_user.is_admin:
            total_query = total_query.filter(Expense.user_id == user_id)
        if start_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                total_query = total_query.filter(Expense.expense_date >= start)
            except ValueError:
                pass
        if end_date:
            try:
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
                total_query = total_query.filter(Expense.expense_date <= end)
            except ValueError:
                pass
        
        # Non-admin users restriction
        if not current_user.is_admin:
            total_query = total_query.filter(
                db.or_(
                    Expense.user_id == current_user.id,
                    Expense.approved_by == current_user.id
                )
            )
        
        total_amount = total_query.scalar() or 0
    
    return render_template(
        'expenses/list.html',
        expenses=expenses_pagination.items,
        pagination=expenses_pagination,
        projects=projects,
        clients=clients,
        categories=categories,
        users=users,
        total_amount=float(total_amount),
        total_count=total_count,
        # Pass back filter values
        status=status,
        category=category,
        project_id=project_id,
        client_id=client_id,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        search=search,
        billable=billable,
        reimbursable=reimbursable
    )


@expenses_bp.route('/expenses/create', methods=['GET', 'POST'])
@login_required
def create_expense():
    """Create a new expense"""
    if request.method == 'GET':
        # Get data for form
        projects = Project.query.filter_by(status='active').order_by(Project.name).all()
        clients = Client.get_active_clients()
        categories = Expense.get_expense_categories()
        payment_methods = Expense.get_payment_methods()
        
        return render_template(
            'expenses/form.html',
            expense=None,
            projects=projects,
            clients=clients,
            categories=categories,
            payment_methods=payment_methods
        )
    
    try:
        # Get form data
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        amount = request.form.get('amount', '0').strip()
        currency_code = request.form.get('currency_code', 'EUR').strip()
        tax_amount = request.form.get('tax_amount', '0').strip()
        expense_date = request.form.get('expense_date', '').strip()
        
        # Validate required fields
        if not title:
            flash(_('Title is required'), 'error')
            return redirect(url_for('expenses.create_expense'))
        
        if not category:
            flash(_('Category is required'), 'error')
            return redirect(url_for('expenses.create_expense'))
        
        if not amount:
            flash(_('Amount is required'), 'error')
            return redirect(url_for('expenses.create_expense'))
        
        if not expense_date:
            flash(_('Expense date is required'), 'error')
            return redirect(url_for('expenses.create_expense'))
        
        # Parse date
        try:
            expense_date_obj = datetime.strptime(expense_date, '%Y-%m-%d').date()
        except ValueError:
            flash(_('Invalid date format'), 'error')
            return redirect(url_for('expenses.create_expense'))
        
        # Parse amounts
        try:
            amount_decimal = Decimal(amount)
            tax_amount_decimal = Decimal(tax_amount) if tax_amount else Decimal('0')
        except (ValueError, Decimal.InvalidOperation):
            flash(_('Invalid amount format'), 'error')
            return redirect(url_for('expenses.create_expense'))
        
        # Optional fields
        project_id = request.form.get('project_id', type=int)
        client_id = request.form.get('client_id', type=int)
        payment_method = request.form.get('payment_method', '').strip()
        payment_date = request.form.get('payment_date', '').strip()
        vendor = request.form.get('vendor', '').strip()
        receipt_number = request.form.get('receipt_number', '').strip()
        notes = request.form.get('notes', '').strip()
        tags = request.form.get('tags', '').strip()
        billable = request.form.get('billable') == 'on'
        reimbursable = request.form.get('reimbursable') == 'on'
        
        # Parse payment date if provided
        payment_date_obj = None
        if payment_date:
            try:
                payment_date_obj = datetime.strptime(payment_date, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        # Handle file upload
        receipt_path = None
        if 'receipt_file' in request.files:
            file = request.files['receipt_file']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Add timestamp to filename to avoid collisions
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{filename}"
                
                # Ensure upload directory exists
                upload_dir = os.path.join(current_app.root_path, '..', UPLOAD_FOLDER)
                os.makedirs(upload_dir, exist_ok=True)
                
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)
                receipt_path = os.path.join(UPLOAD_FOLDER, filename)
        
        # Create expense
        expense = Expense(
            user_id=current_user.id,
            title=title,
            category=category,
            amount=amount_decimal,
            expense_date=expense_date_obj,
            description=description,
            currency_code=currency_code,
            tax_amount=tax_amount_decimal,
            project_id=project_id,
            client_id=client_id,
            payment_method=payment_method,
            payment_date=payment_date_obj,
            vendor=vendor,
            receipt_number=receipt_number,
            receipt_path=receipt_path,
            notes=notes,
            tags=tags,
            billable=billable,
            reimbursable=reimbursable
        )
        
        db.session.add(expense)
        
        if safe_commit(db):
            flash(_('Expense created successfully'), 'success')
            log_event('expense_created', user_id=current_user.id, expense_id=expense.id)
            track_event(current_user.id, 'expense.created', {
                'expense_id': expense.id,
                'category': category,
                'amount': float(amount_decimal),
                'billable': billable,
                'reimbursable': reimbursable
            })
            return redirect(url_for('expenses.view_expense', expense_id=expense.id))
        else:
            flash(_('Error creating expense'), 'error')
            return redirect(url_for('expenses.create_expense'))
    
    except Exception as e:
        current_app.logger.error(f"Error creating expense: {e}")
        flash(_('Error creating expense'), 'error')
        return redirect(url_for('expenses.create_expense'))


@expenses_bp.route('/expenses/<int:expense_id>')
@login_required
def view_expense(expense_id):
    """View expense details"""
    expense = Expense.query.get_or_404(expense_id)
    
    # Check permission
    if not current_user.is_admin and expense.user_id != current_user.id and expense.approved_by != current_user.id:
        flash(_('You do not have permission to view this expense'), 'error')
        return redirect(url_for('expenses.list_expenses'))
    
    # Track page view
    from app import track_page_view
    track_page_view("expense_detail", properties={'expense_id': expense_id})
    
    return render_template('expenses/view.html', expense=expense)


@expenses_bp.route('/expenses/<int:expense_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_expense(expense_id):
    """Edit an existing expense"""
    expense = Expense.query.get_or_404(expense_id)
    
    # Check permission - only owner can edit (unless admin)
    if not current_user.is_admin and expense.user_id != current_user.id:
        flash(_('You do not have permission to edit this expense'), 'error')
        return redirect(url_for('expenses.view_expense', expense_id=expense_id))
    
    # Cannot edit approved or reimbursed expenses without admin privileges
    if not current_user.is_admin and expense.status in ['approved', 'reimbursed']:
        flash(_('Cannot edit approved or reimbursed expenses'), 'error')
        return redirect(url_for('expenses.view_expense', expense_id=expense_id))
    
    if request.method == 'GET':
        projects = Project.query.filter_by(status='active').order_by(Project.name).all()
        clients = Client.get_active_clients()
        categories = Expense.get_expense_categories()
        payment_methods = Expense.get_payment_methods()
        
        return render_template(
            'expenses/form.html',
            expense=expense,
            projects=projects,
            clients=clients,
            categories=categories,
            payment_methods=payment_methods
        )
    
    try:
        # Get form data
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        amount = request.form.get('amount', '0').strip()
        currency_code = request.form.get('currency_code', 'EUR').strip()
        tax_amount = request.form.get('tax_amount', '0').strip()
        expense_date = request.form.get('expense_date', '').strip()
        
        # Validate required fields
        if not title or not category or not amount or not expense_date:
            flash(_('Please fill in all required fields'), 'error')
            return redirect(url_for('expenses.edit_expense', expense_id=expense_id))
        
        # Parse date
        try:
            expense_date_obj = datetime.strptime(expense_date, '%Y-%m-%d').date()
        except ValueError:
            flash(_('Invalid date format'), 'error')
            return redirect(url_for('expenses.edit_expense', expense_id=expense_id))
        
        # Parse amounts
        try:
            amount_decimal = Decimal(amount)
            tax_amount_decimal = Decimal(tax_amount) if tax_amount else Decimal('0')
        except (ValueError, Decimal.InvalidOperation):
            flash(_('Invalid amount format'), 'error')
            return redirect(url_for('expenses.edit_expense', expense_id=expense_id))
        
        # Update expense fields
        expense.title = title
        expense.description = description
        expense.category = category
        expense.amount = amount_decimal
        expense.currency_code = currency_code
        expense.tax_amount = tax_amount_decimal
        expense.expense_date = expense_date_obj
        
        # Optional fields
        expense.project_id = request.form.get('project_id', type=int)
        expense.client_id = request.form.get('client_id', type=int)
        expense.payment_method = request.form.get('payment_method', '').strip()
        expense.vendor = request.form.get('vendor', '').strip()
        expense.receipt_number = request.form.get('receipt_number', '').strip()
        expense.notes = request.form.get('notes', '').strip()
        expense.tags = request.form.get('tags', '').strip()
        expense.billable = request.form.get('billable') == 'on'
        expense.reimbursable = request.form.get('reimbursable') == 'on'
        
        # Parse payment date if provided
        payment_date = request.form.get('payment_date', '').strip()
        if payment_date:
            try:
                expense.payment_date = datetime.strptime(payment_date, '%Y-%m-%d').date()
            except ValueError:
                expense.payment_date = None
        else:
            expense.payment_date = None
        
        # Handle file upload
        if 'receipt_file' in request.files:
            file = request.files['receipt_file']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{filename}"
                
                upload_dir = os.path.join(current_app.root_path, '..', UPLOAD_FOLDER)
                os.makedirs(upload_dir, exist_ok=True)
                
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)
                
                # Delete old receipt if exists
                if expense.receipt_path:
                    old_file_path = os.path.join(current_app.root_path, '..', expense.receipt_path)
                    if os.path.exists(old_file_path):
                        try:
                            os.remove(old_file_path)
                        except Exception:
                            pass
                
                expense.receipt_path = os.path.join(UPLOAD_FOLDER, filename)
        
        expense.updated_at = datetime.utcnow()
        
        if safe_commit(db):
            flash(_('Expense updated successfully'), 'success')
            log_event('expense_updated', user_id=current_user.id, expense_id=expense.id)
            track_event(current_user.id, 'expense.updated', {'expense_id': expense.id})
            return redirect(url_for('expenses.view_expense', expense_id=expense.id))
        else:
            flash(_('Error updating expense'), 'error')
            return redirect(url_for('expenses.edit_expense', expense_id=expense_id))
    
    except Exception as e:
        current_app.logger.error(f"Error updating expense: {e}")
        flash(_('Error updating expense'), 'error')
        return redirect(url_for('expenses.edit_expense', expense_id=expense_id))


@expenses_bp.route('/expenses/<int:expense_id>/delete', methods=['POST'])
@login_required
def delete_expense(expense_id):
    """Delete an expense"""
    expense = Expense.query.get_or_404(expense_id)
    
    # Check permission
    if not current_user.is_admin and expense.user_id != current_user.id:
        flash(_('You do not have permission to delete this expense'), 'error')
        return redirect(url_for('expenses.view_expense', expense_id=expense_id))
    
    # Cannot delete approved or invoiced expenses without admin privileges
    if not current_user.is_admin and (expense.status == 'approved' or expense.invoiced):
        flash(_('Cannot delete approved or invoiced expenses'), 'error')
        return redirect(url_for('expenses.view_expense', expense_id=expense_id))
    
    try:
        # Delete receipt file if exists
        if expense.receipt_path:
            file_path = os.path.join(current_app.root_path, '..', expense.receipt_path)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass
        
        db.session.delete(expense)
        
        if safe_commit(db):
            flash(_('Expense deleted successfully'), 'success')
            log_event('expense_deleted', user_id=current_user.id, expense_id=expense_id)
            track_event(current_user.id, 'expense.deleted', {'expense_id': expense_id})
        else:
            flash(_('Error deleting expense'), 'error')
    
    except Exception as e:
        current_app.logger.error(f"Error deleting expense: {e}")
        flash(_('Error deleting expense'), 'error')
    
    return redirect(url_for('expenses.list_expenses'))


@expenses_bp.route('/expenses/<int:expense_id>/approve', methods=['POST'])
@login_required
def approve_expense(expense_id):
    """Approve an expense"""
    if not current_user.is_admin:
        flash(_('Only administrators can approve expenses'), 'error')
        return redirect(url_for('expenses.view_expense', expense_id=expense_id))
    
    expense = Expense.query.get_or_404(expense_id)
    
    if expense.status != 'pending':
        flash(_('Only pending expenses can be approved'), 'error')
        return redirect(url_for('expenses.view_expense', expense_id=expense_id))
    
    try:
        notes = request.form.get('approval_notes', '').strip()
        expense.approve(current_user.id, notes)
        
        if safe_commit(db):
            flash(_('Expense approved successfully'), 'success')
            log_event('expense_approved', user_id=current_user.id, expense_id=expense_id)
            track_event(current_user.id, 'expense.approved', {'expense_id': expense_id})
        else:
            flash(_('Error approving expense'), 'error')
    
    except Exception as e:
        current_app.logger.error(f"Error approving expense: {e}")
        flash(_('Error approving expense'), 'error')
    
    return redirect(url_for('expenses.view_expense', expense_id=expense_id))


@expenses_bp.route('/expenses/<int:expense_id>/reject', methods=['POST'])
@login_required
def reject_expense(expense_id):
    """Reject an expense"""
    if not current_user.is_admin:
        flash(_('Only administrators can reject expenses'), 'error')
        return redirect(url_for('expenses.view_expense', expense_id=expense_id))
    
    expense = Expense.query.get_or_404(expense_id)
    
    if expense.status != 'pending':
        flash(_('Only pending expenses can be rejected'), 'error')
        return redirect(url_for('expenses.view_expense', expense_id=expense_id))
    
    try:
        reason = request.form.get('rejection_reason', '').strip()
        if not reason:
            flash(_('Rejection reason is required'), 'error')
            return redirect(url_for('expenses.view_expense', expense_id=expense_id))
        
        expense.reject(current_user.id, reason)
        
        if safe_commit(db):
            flash(_('Expense rejected'), 'success')
            log_event('expense_rejected', user_id=current_user.id, expense_id=expense_id)
            track_event(current_user.id, 'expense.rejected', {'expense_id': expense_id})
        else:
            flash(_('Error rejecting expense'), 'error')
    
    except Exception as e:
        current_app.logger.error(f"Error rejecting expense: {e}")
        flash(_('Error rejecting expense'), 'error')
    
    return redirect(url_for('expenses.view_expense', expense_id=expense_id))


@expenses_bp.route('/expenses/<int:expense_id>/reimburse', methods=['POST'])
@login_required
def mark_reimbursed(expense_id):
    """Mark an expense as reimbursed"""
    if not current_user.is_admin:
        flash(_('Only administrators can mark expenses as reimbursed'), 'error')
        return redirect(url_for('expenses.view_expense', expense_id=expense_id))
    
    expense = Expense.query.get_or_404(expense_id)
    
    if expense.status != 'approved':
        flash(_('Only approved expenses can be marked as reimbursed'), 'error')
        return redirect(url_for('expenses.view_expense', expense_id=expense_id))
    
    if not expense.reimbursable:
        flash(_('This expense is not marked as reimbursable'), 'error')
        return redirect(url_for('expenses.view_expense', expense_id=expense_id))
    
    try:
        expense.mark_as_reimbursed()
        
        if safe_commit(db):
            flash(_('Expense marked as reimbursed'), 'success')
            log_event('expense_reimbursed', user_id=current_user.id, expense_id=expense_id)
            track_event(current_user.id, 'expense.reimbursed', {'expense_id': expense_id})
        else:
            flash(_('Error marking expense as reimbursed'), 'error')
    
    except Exception as e:
        current_app.logger.error(f"Error marking expense as reimbursed: {e}")
        flash(_('Error marking expense as reimbursed'), 'error')
    
    return redirect(url_for('expenses.view_expense', expense_id=expense_id))


@expenses_bp.route('/expenses/export')
@login_required
def export_expenses():
    """Export expenses to CSV"""
    # Get filter parameters (same as list_expenses)
    status = request.args.get('status', '').strip()
    category = request.args.get('category', '').strip()
    project_id = request.args.get('project_id', type=int)
    client_id = request.args.get('client_id', type=int)
    user_id = request.args.get('user_id', type=int)
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    
    # Build query
    query = Expense.query
    
    # Non-admin users can only export their own expenses
    if not current_user.is_admin:
        query = query.filter(Expense.user_id == current_user.id)
    
    # Apply filters
    if status:
        query = query.filter(Expense.status == status)
    if category:
        query = query.filter(Expense.category == category)
    if project_id:
        query = query.filter(Expense.project_id == project_id)
    if client_id:
        query = query.filter(Expense.client_id == client_id)
    if user_id and current_user.is_admin:
        query = query.filter(Expense.user_id == user_id)
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(Expense.expense_date >= start)
        except ValueError:
            pass
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(Expense.expense_date <= end)
        except ValueError:
            pass
    
    expenses = query.order_by(Expense.expense_date.desc()).all()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Date', 'Title', 'Category', 'Amount', 'Tax', 'Total', 'Currency',
        'Status', 'Vendor', 'Payment Method', 'Project', 'Client', 'User',
        'Billable', 'Reimbursable', 'Invoiced', 'Receipt Number', 'Notes'
    ])
    
    # Write data
    for expense in expenses:
        writer.writerow([
            expense.expense_date.isoformat() if expense.expense_date else '',
            expense.title,
            expense.category,
            float(expense.amount),
            float(expense.tax_amount) if expense.tax_amount else 0,
            float(expense.total_amount),
            expense.currency_code,
            expense.status,
            expense.vendor or '',
            expense.payment_method or '',
            expense.project.name if expense.project else '',
            expense.client.name if expense.client else '',
            expense.user.username if expense.user else '',
            'Yes' if expense.billable else 'No',
            'Yes' if expense.reimbursable else 'No',
            'Yes' if expense.invoiced else 'No',
            expense.receipt_number or '',
            expense.notes or ''
        ])
    
    # Prepare response
    output.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'expenses_{timestamp}.csv'
    
    # Track export
    log_event('expenses_exported', user_id=current_user.id, count=len(expenses))
    track_event(current_user.id, 'expenses.exported', {'count': len(expenses)})
    
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )


@expenses_bp.route('/expenses/dashboard')
@login_required
def dashboard():
    """Expense dashboard with analytics"""
    # Track page view
    from app import track_page_view
    track_page_view("expenses_dashboard")
    
    # Date range - default to current month
    today = date.today()
    start_date = date(today.year, today.month, 1)
    end_date = today
    
    # Get date range from query params if provided
    start_date_str = request.args.get('start_date', '').strip()
    end_date_str = request.args.get('end_date', '').strip()
    
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
    
    # Build base query
    if current_user.is_admin:
        query = Expense.query
    else:
        query = Expense.query.filter_by(user_id=current_user.id)
    
    # Apply date filter
    query = query.filter(
        Expense.expense_date >= start_date,
        Expense.expense_date <= end_date
    )
    
    # Get statistics
    total_expenses = query.count()
    
    # Total amount
    total_amount_query = db.session.query(
        db.func.sum(Expense.amount + db.func.coalesce(Expense.tax_amount, 0))
    ).filter(Expense.expense_date >= start_date, Expense.expense_date <= end_date)
    
    if not current_user.is_admin:
        total_amount_query = total_amount_query.filter(Expense.user_id == current_user.id)
    
    total_amount = total_amount_query.scalar() or 0
    
    # By status
    pending_count = query.filter_by(status='pending').count()
    approved_count = query.filter_by(status='approved').count()
    rejected_count = query.filter_by(status='rejected').count()
    reimbursed_count = query.filter_by(status='reimbursed').count()
    
    # Pending reimbursement
    pending_reimbursement = query.filter(
        Expense.status == 'approved',
        Expense.reimbursable == True,
        Expense.reimbursed == False
    ).count()
    
    # By category
    category_stats = Expense.get_expenses_by_category(
        user_id=None if current_user.is_admin else current_user.id,
        start_date=start_date,
        end_date=end_date
    )
    
    # Recent expenses
    recent_expenses = query.order_by(Expense.expense_date.desc()).limit(10).all()
    
    return render_template(
        'expenses/dashboard.html',
        total_expenses=total_expenses,
        total_amount=float(total_amount),
        pending_count=pending_count,
        approved_count=approved_count,
        rejected_count=rejected_count,
        reimbursed_count=reimbursed_count,
        pending_reimbursement=pending_reimbursement,
        category_stats=category_stats,
        recent_expenses=recent_expenses,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat()
    )


# API endpoints
@expenses_bp.route('/api/expenses', methods=['GET'])
@login_required
def api_list_expenses():
    """API endpoint to list expenses"""
    # Similar filters as list_expenses
    status = request.args.get('status', '').strip()
    category = request.args.get('category', '').strip()
    project_id = request.args.get('project_id', type=int)
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    
    # Build query
    query = Expense.query
    
    if not current_user.is_admin:
        query = query.filter_by(user_id=current_user.id)
    
    if status:
        query = query.filter(Expense.status == status)
    if category:
        query = query.filter(Expense.category == category)
    if project_id:
        query = query.filter(Expense.project_id == project_id)
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(Expense.expense_date >= start)
        except ValueError:
            pass
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(Expense.expense_date <= end)
        except ValueError:
            pass
    
    expenses = query.order_by(Expense.expense_date.desc()).all()
    
    return jsonify({
        'expenses': [expense.to_dict() for expense in expenses],
        'count': len(expenses)
    })


@expenses_bp.route('/api/expenses/<int:expense_id>', methods=['GET'])
@login_required
def api_get_expense(expense_id):
    """API endpoint to get a single expense"""
    expense = Expense.query.get_or_404(expense_id)
    
    # Check permission
    if not current_user.is_admin and expense.user_id != current_user.id:
        return jsonify({'error': 'Permission denied'}), 403
    
    return jsonify(expense.to_dict())

