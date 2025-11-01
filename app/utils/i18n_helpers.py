"""
Internationalization helpers for translating model field values and choices.

This module provides translation functions for all enum-based fields in models,
ensuring consistent translations across the application.
"""

from flask_babel import lazy_gettext as _l, gettext as _


# Task Status Translations
def get_task_status_display(status):
    """Get translated display name for task status"""
    status_map = {
        'todo': _('To Do'),
        'in_progress': _('In Progress'),
        'review': _('Review'),
        'done': _('Done'),
        'cancelled': _('Cancelled')
    }
    return status_map.get(status, status.replace('_', ' ').title())


def get_task_statuses():
    """Get list of all task statuses with translations"""
    return [
        ('todo', _('To Do')),
        ('in_progress', _('In Progress')),
        ('review', _('Review')),
        ('done', _('Done')),
        ('cancelled', _('Cancelled'))
    ]


# Task Priority Translations
def get_task_priority_display(priority):
    """Get translated display name for task priority"""
    priority_map = {
        'low': _('Low'),
        'medium': _('Medium'),
        'high': _('High'),
        'urgent': _('Urgent')
    }
    return priority_map.get(priority, priority.capitalize())


def get_task_priorities():
    """Get list of all task priorities with translations"""
    return [
        ('low', _('Low')),
        ('medium', _('Medium')),
        ('high', _('High')),
        ('urgent', _('Urgent'))
    ]


# Project Status Translations
def get_project_status_display(status):
    """Get translated display name for project status"""
    status_map = {
        'active': _('Active'),
        'inactive': _('Inactive'),
        'archived': _('Archived')
    }
    return status_map.get(status, status.capitalize())


def get_project_statuses():
    """Get list of all project statuses with translations"""
    return [
        ('active', _('Active')),
        ('inactive', _('Inactive')),
        ('archived', _('Archived'))
    ]


# Invoice Status Translations
def get_invoice_status_display(status):
    """Get translated display name for invoice status"""
    status_map = {
        'draft': _('Draft'),
        'sent': _('Sent'),
        'paid': _('Paid'),
        'overdue': _('Overdue'),
        'cancelled': _('Cancelled')
    }
    return status_map.get(status, status.capitalize())


def get_invoice_statuses():
    """Get list of all invoice statuses with translations"""
    return [
        ('draft', _('Draft')),
        ('sent', _('Sent')),
        ('paid', _('Paid')),
        ('overdue', _('Overdue')),
        ('cancelled', _('Cancelled'))
    ]


# Invoice Payment Status Translations
def get_payment_status_display(status):
    """Get translated display name for payment status"""
    status_map = {
        'unpaid': _('Unpaid'),
        'partially_paid': _('Partially Paid'),
        'fully_paid': _('Fully Paid'),
        'overpaid': _('Overpaid')
    }
    return status_map.get(status, status.replace('_', ' ').title())


def get_payment_statuses():
    """Get list of all payment statuses with translations"""
    return [
        ('unpaid', _('Unpaid')),
        ('partially_paid', _('Partially Paid')),
        ('fully_paid', _('Fully Paid')),
        ('overpaid', _('Overpaid'))
    ]


# Payment Method Translations
def get_payment_method_display(method):
    """Get translated display name for payment method"""
    method_map = {
        'cash': _('Cash'),
        'check': _('Check'),
        'bank_transfer': _('Bank Transfer'),
        'credit_card': _('Credit Card'),
        'debit_card': _('Debit Card'),
        'paypal': _('PayPal'),
        'stripe': _('Stripe'),
        'company_card': _('Company Card'),
        'other': _('Other')
    }
    return method_map.get(method, method.replace('_', ' ').title())


def get_payment_methods():
    """Get list of all payment methods with translations"""
    return [
        ('cash', _('Cash')),
        ('check', _('Check')),
        ('bank_transfer', _('Bank Transfer')),
        ('credit_card', _('Credit Card')),
        ('debit_card', _('Debit Card')),
        ('paypal', _('PayPal')),
        ('stripe', _('Stripe')),
        ('company_card', _('Company Card')),
        ('other', _('Other'))
    ]


# Expense Status Translations
def get_expense_status_display(status):
    """Get translated display name for expense status"""
    status_map = {
        'pending': _('Pending'),
        'approved': _('Approved'),
        'rejected': _('Rejected'),
        'reimbursed': _('Reimbursed')
    }
    return status_map.get(status, status.capitalize())


def get_expense_statuses():
    """Get list of all expense statuses with translations"""
    return [
        ('pending', _('Pending')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected')),
        ('reimbursed', _('Reimbursed'))
    ]


# Expense Category Translations
def get_expense_category_display(category):
    """Get translated display name for expense category"""
    category_map = {
        'travel': _('Travel'),
        'meals': _('Meals'),
        'accommodation': _('Accommodation'),
        'supplies': _('Supplies'),
        'software': _('Software'),
        'equipment': _('Equipment'),
        'services': _('Services'),
        'marketing': _('Marketing'),
        'training': _('Training'),
        'other': _('Other')
    }
    return category_map.get(category, category.capitalize())


def get_expense_categories():
    """Get list of all expense categories with translations"""
    return [
        ('travel', _('Travel')),
        ('meals', _('Meals')),
        ('accommodation', _('Accommodation')),
        ('supplies', _('Supplies')),
        ('software', _('Software')),
        ('equipment', _('Equipment')),
        ('services', _('Services')),
        ('marketing', _('Marketing')),
        ('training', _('Training')),
        ('other', _('Other'))
    ]


# Mileage Status Translations (same as expense)
def get_mileage_status_display(status):
    """Get translated display name for mileage status"""
    return get_expense_status_display(status)


def get_mileage_statuses():
    """Get list of all mileage statuses with translations"""
    return get_expense_statuses()


# Per Diem Status Translations (same as expense)
def get_per_diem_status_display(status):
    """Get translated display name for per diem status"""
    return get_expense_status_display(status)


def get_per_diem_statuses():
    """Get list of all per diem statuses with translations"""
    return get_expense_statuses()


# Import/Export Job Status Translations
def get_job_status_display(status):
    """Get translated display name for import/export job status"""
    status_map = {
        'pending': _('Pending'),
        'processing': _('Processing'),
        'completed': _('Completed'),
        'failed': _('Failed'),
        'partial': _('Partial')
    }
    return status_map.get(status, status.capitalize())


def get_job_statuses():
    """Get list of all job statuses with translations"""
    return [
        ('pending', _('Pending')),
        ('processing', _('Processing')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
        ('partial', _('Partial'))
    ]


# Weekly Goal Status Translations
def get_goal_status_display(status):
    """Get translated display name for weekly goal status"""
    status_map = {
        'active': _('Active'),
        'completed': _('Completed'),
        'failed': _('Failed'),
        'cancelled': _('Cancelled')
    }
    return status_map.get(status, status.capitalize())


def get_goal_statuses():
    """Get list of all goal statuses with translations"""
    return [
        ('active', _('Active')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
        ('cancelled', _('Cancelled'))
    ]


# Budget Alert Type/Level Translations
def get_alert_type_display(alert_type):
    """Get translated display name for budget alert type"""
    alert_map = {
        'warning_80': _('80% Budget Warning'),
        'warning_100': _('Budget Limit Reached'),
        'over_budget': _('Over Budget')
    }
    return alert_map.get(alert_type, alert_type.replace('_', ' ').title())


def get_alert_level_display(alert_level):
    """Get translated display name for alert level"""
    level_map = {
        'info': _('Info'),
        'warning': _('Warning'),
        'critical': _('Critical')
    }
    return level_map.get(alert_level, alert_level.capitalize())


def get_alert_levels():
    """Get list of all alert levels with translations"""
    return [
        ('info', _('Info')),
        ('warning', _('Warning')),
        ('critical', _('Critical'))
    ]


# Client Status Translations
def get_client_status_display(status):
    """Get translated display name for client status"""
    status_map = {
        'active': _('Active'),
        'inactive': _('Inactive')
    }
    return status_map.get(status, status.capitalize())


def get_client_statuses():
    """Get list of all client statuses with translations"""
    return [
        ('active', _('Active')),
        ('inactive', _('Inactive'))
    ]


# Generic Status Badge Classes
def get_status_badge_class(status, status_type='generic'):
    """Get Tailwind CSS badge classes for status"""
    # Common status colors
    badge_classes = {
        # Task statuses
        'todo': 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
        'in_progress': 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
        'review': 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
        'done': 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
        'cancelled': 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
        
        # Invoice/Payment statuses
        'draft': 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
        'sent': 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
        'paid': 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
        'overdue': 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
        'unpaid': 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
        'partially_paid': 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
        'fully_paid': 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
        
        # Approval statuses
        'pending': 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
        'approved': 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
        'rejected': 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
        'reimbursed': 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300',
        
        # Processing statuses
        'processing': 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
        'completed': 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
        'failed': 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
        'partial': 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
        
        # Active/Inactive
        'active': 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
        'inactive': 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
        'archived': 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
    }
    
    return badge_classes.get(status, 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300')


def get_priority_badge_class(priority):
    """Get Tailwind CSS badge classes for priority"""
    priority_classes = {
        'low': 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
        'medium': 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
        'high': 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
        'urgent': 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
    }
    
    return priority_classes.get(priority, 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300')


# Register these functions to be available in templates
def register_i18n_filters(app):
    """Register i18n template filters"""
    app.jinja_env.filters['task_status'] = get_task_status_display
    app.jinja_env.filters['task_priority'] = get_task_priority_display
    app.jinja_env.filters['project_status'] = get_project_status_display
    app.jinja_env.filters['invoice_status'] = get_invoice_status_display
    app.jinja_env.filters['payment_status'] = get_payment_status_display
    app.jinja_env.filters['payment_method'] = get_payment_method_display
    app.jinja_env.filters['expense_status'] = get_expense_status_display
    app.jinja_env.filters['expense_category'] = get_expense_category_display
    app.jinja_env.filters['mileage_status'] = get_mileage_status_display
    app.jinja_env.filters['per_diem_status'] = get_per_diem_status_display
    app.jinja_env.filters['job_status'] = get_job_status_display
    app.jinja_env.filters['goal_status'] = get_goal_status_display
    app.jinja_env.filters['alert_type'] = get_alert_type_display
    app.jinja_env.filters['alert_level'] = get_alert_level_display
    app.jinja_env.filters['client_status'] = get_client_status_display
    app.jinja_env.filters['status_badge'] = get_status_badge_class
    app.jinja_env.filters['priority_badge'] = get_priority_badge_class

