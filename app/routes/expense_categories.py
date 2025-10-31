from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db, log_event, track_event
from app.models import ExpenseCategory
from datetime import datetime, date
from decimal import Decimal
from app.utils.db import safe_commit
from app.utils.permissions import admin_or_permission_required

expense_categories_bp = Blueprint('expense_categories', __name__)


@expense_categories_bp.route('/expense-categories')
@login_required
@admin_or_permission_required('expense_categories.view')
def list_categories():
    """List all expense categories"""
    from app import track_page_view
    track_page_view("expense_categories_list")
    
    categories = ExpenseCategory.query.order_by(ExpenseCategory.name).all()
    
    # Get budget utilization for each category
    for category in categories:
        category.monthly_utilization = category.get_budget_utilization('monthly')
        category.yearly_utilization = category.get_budget_utilization('yearly')
    
    return render_template('expense_categories/list.html', categories=categories)


@expense_categories_bp.route('/expense-categories/create', methods=['GET', 'POST'])
@login_required
@admin_or_permission_required('expense_categories.create')
def create_category():
    """Create a new expense category"""
    if request.method == 'GET':
        return render_template('expense_categories/form.html', category=None)
    
    try:
        # Get form data
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        code = request.form.get('code', '').strip()
        color = request.form.get('color', '').strip()
        icon = request.form.get('icon', '').strip()
        
        # Validate required fields
        if not name:
            flash(_('Category name is required'), 'error')
            return redirect(url_for('expense_categories.create_category'))
        
        # Budget fields
        monthly_budget = request.form.get('monthly_budget', '').strip()
        quarterly_budget = request.form.get('quarterly_budget', '').strip()
        yearly_budget = request.form.get('yearly_budget', '').strip()
        budget_threshold_percent = request.form.get('budget_threshold_percent', '80')
        
        # Settings
        requires_receipt = request.form.get('requires_receipt') == 'on'
        requires_approval = request.form.get('requires_approval') == 'on'
        default_tax_rate = request.form.get('default_tax_rate', '').strip()
        is_active = request.form.get('is_active') == 'on'
        
        # Create category
        category = ExpenseCategory(
            name=name,
            description=description,
            code=code if code else None,
            color=color if color else None,
            icon=icon if icon else None,
            monthly_budget=Decimal(monthly_budget) if monthly_budget else None,
            quarterly_budget=Decimal(quarterly_budget) if quarterly_budget else None,
            yearly_budget=Decimal(yearly_budget) if yearly_budget else None,
            budget_threshold_percent=int(budget_threshold_percent) if budget_threshold_percent else 80,
            requires_receipt=requires_receipt,
            requires_approval=requires_approval,
            default_tax_rate=Decimal(default_tax_rate) if default_tax_rate else None,
            is_active=is_active
        )
        
        db.session.add(category)
        
        if safe_commit(db):
            flash(_('Expense category created successfully'), 'success')
            log_event('expense_category_created', user_id=current_user.id, category_id=category.id)
            track_event(current_user.id, 'expense_category.created', {'category_id': category.id})
            return redirect(url_for('expense_categories.list_categories'))
        else:
            flash(_('Error creating expense category'), 'error')
            return redirect(url_for('expense_categories.create_category'))
    
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Error creating expense category: {e}")
        flash(_('Error creating expense category'), 'error')
        return redirect(url_for('expense_categories.create_category'))


@expense_categories_bp.route('/expense-categories/<int:category_id>')
@login_required
@admin_or_permission_required('expense_categories.view')
def view_category(category_id):
    """View expense category details"""
    category = ExpenseCategory.query.get_or_404(category_id)
    
    from app import track_page_view
    track_page_view("expense_category_detail", properties={'category_id': category_id})
    
    # Get budget utilization
    monthly_util = category.get_budget_utilization('monthly')
    quarterly_util = category.get_budget_utilization('quarterly')
    yearly_util = category.get_budget_utilization('yearly')
    
    return render_template(
        'expense_categories/view.html',
        category=category,
        monthly_utilization=monthly_util,
        quarterly_utilization=quarterly_util,
        yearly_utilization=yearly_util
    )


@expense_categories_bp.route('/expense-categories/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_or_permission_required('expense_categories.update')
def edit_category(category_id):
    """Edit an expense category"""
    category = ExpenseCategory.query.get_or_404(category_id)
    
    if request.method == 'GET':
        return render_template('expense_categories/form.html', category=category)
    
    try:
        # Get form data
        name = request.form.get('name', '').strip()
        if not name:
            flash(_('Category name is required'), 'error')
            return redirect(url_for('expense_categories.edit_category', category_id=category_id))
        
        # Update category fields
        category.name = name
        category.description = request.form.get('description', '').strip()
        category.code = request.form.get('code', '').strip() or None
        category.color = request.form.get('color', '').strip() or None
        category.icon = request.form.get('icon', '').strip() or None
        
        # Budget fields
        monthly_budget = request.form.get('monthly_budget', '').strip()
        quarterly_budget = request.form.get('quarterly_budget', '').strip()
        yearly_budget = request.form.get('yearly_budget', '').strip()
        
        category.monthly_budget = Decimal(monthly_budget) if monthly_budget else None
        category.quarterly_budget = Decimal(quarterly_budget) if quarterly_budget else None
        category.yearly_budget = Decimal(yearly_budget) if yearly_budget else None
        category.budget_threshold_percent = int(request.form.get('budget_threshold_percent', '80'))
        
        # Settings
        category.requires_receipt = request.form.get('requires_receipt') == 'on'
        category.requires_approval = request.form.get('requires_approval') == 'on'
        
        default_tax_rate = request.form.get('default_tax_rate', '').strip()
        category.default_tax_rate = Decimal(default_tax_rate) if default_tax_rate else None
        category.is_active = request.form.get('is_active') == 'on'
        
        category.updated_at = datetime.utcnow()
        
        if safe_commit(db):
            flash(_('Expense category updated successfully'), 'success')
            log_event('expense_category_updated', user_id=current_user.id, category_id=category.id)
            track_event(current_user.id, 'expense_category.updated', {'category_id': category.id})
            return redirect(url_for('expense_categories.view_category', category_id=category.id))
        else:
            flash(_('Error updating expense category'), 'error')
            return redirect(url_for('expense_categories.edit_category', category_id=category_id))
    
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Error updating expense category: {e}")
        flash(_('Error updating expense category'), 'error')
        return redirect(url_for('expense_categories.edit_category', category_id=category_id))


@expense_categories_bp.route('/expense-categories/<int:category_id>/delete', methods=['POST'])
@login_required
@admin_or_permission_required('expense_categories.delete')
def delete_category(category_id):
    """Delete an expense category"""
    category = ExpenseCategory.query.get_or_404(category_id)
    
    try:
        # Instead of deleting, just deactivate
        category.is_active = False
        category.updated_at = datetime.utcnow()
        
        if safe_commit(db):
            flash(_('Expense category deactivated successfully'), 'success')
            log_event('expense_category_deleted', user_id=current_user.id, category_id=category_id)
            track_event(current_user.id, 'expense_category.deleted', {'category_id': category_id})
        else:
            flash(_('Error deactivating expense category'), 'error')
    
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Error deactivating expense category: {e}")
        flash(_('Error deactivating expense category'), 'error')
    
    return redirect(url_for('expense_categories.list_categories'))


# API endpoints
@expense_categories_bp.route('/api/expense-categories', methods=['GET'])
@login_required
def api_list_categories():
    """API endpoint to list expense categories"""
    categories = ExpenseCategory.get_active_categories()
    
    return jsonify({
        'categories': [category.to_dict() for category in categories],
        'count': len(categories)
    })


@expense_categories_bp.route('/api/expense-categories/<int:category_id>', methods=['GET'])
@login_required
def api_get_category(category_id):
    """API endpoint to get a single expense category"""
    category = ExpenseCategory.query.get_or_404(category_id)
    
    return jsonify(category.to_dict())


@expense_categories_bp.route('/api/expense-categories/budget-alerts', methods=['GET'])
@login_required
@admin_or_permission_required('expense_categories.view')
def api_budget_alerts():
    """API endpoint to get categories over budget threshold"""
    period = request.args.get('period', 'monthly')
    
    over_budget = ExpenseCategory.get_categories_over_budget(period)
    
    return jsonify({
        'period': period,
        'alerts': [
            {
                'category': item['category'].to_dict(),
                'utilization': item['utilization']
            }
            for item in over_budget
        ],
        'count': len(over_budget)
    })

