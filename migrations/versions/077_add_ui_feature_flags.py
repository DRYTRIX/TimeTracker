"""Add UI feature flags to users table

Revision ID: 077
Revises: 076
Create Date: 2025-01-22 00:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '077_ui_feature_flags'
down_revision = '076_client_billing_time_entries'
branch_labels = None
depends_on = None


def upgrade():
    """Add UI feature flag fields to users table"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    dialect_name = bind.dialect.name if bind else 'generic'
    
    # Check existing columns (idempotent)
    existing_tables = inspector.get_table_names()
    if 'users' not in existing_tables:
        return
    
    users_columns = {c['name'] for c in inspector.get_columns('users')}
    
    # Helper function to add column if it doesn't exist
    def _add_column_if_missing(column_name, description=""):
        if column_name in users_columns:
            print(f"✓ Column {column_name} already exists in users table")
            return
        try:
            op.add_column('users', sa.Column(column_name, sa.Boolean(), nullable=False, server_default='1'))
            print(f"✓ Added {column_name} column to users table{(' - ' + description) if description else ''}")
        except Exception as e:
            error_msg = str(e)
            if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
                print(f"✓ Column {column_name} already exists in users table (detected via error)")
            else:
                print(f"⚠ Warning adding {column_name} column: {e}")
                raise
    
    # Add UI feature flags to users table
    # All default to True (enabled) for backward compatibility
    _add_column_if_missing('ui_show_inventory', 'Show/hide Inventory section in navigation')
    
    _add_column_if_missing('ui_show_mileage', 'Show/hide Mileage under Finance & Expenses')
    _add_column_if_missing('ui_show_per_diem', 'Show/hide Per Diem under Finance & Expenses')
    _add_column_if_missing('ui_show_kanban_board', 'Show/hide Kanban Board under Time Tracking')
    
    # Calendar section
    _add_column_if_missing('ui_show_calendar', 'Show/hide Calendar section')
    
    # Time Tracking section items
    _add_column_if_missing('ui_show_project_templates', 'Show/hide Project Templates')
    _add_column_if_missing('ui_show_gantt_chart', 'Show/hide Gantt Chart')
    _add_column_if_missing('ui_show_weekly_goals', 'Show/hide Weekly Goals')
    _add_column_if_missing('ui_show_issues', 'Show/hide Issues feature')
    
    # CRM section
    _add_column_if_missing('ui_show_quotes', 'Show/hide Quotes')
    
    # Finance & Expenses section items
    _add_column_if_missing('ui_show_reports', 'Show/hide Reports')
    _add_column_if_missing('ui_show_report_builder', 'Show/hide Report Builder')
    _add_column_if_missing('ui_show_scheduled_reports', 'Show/hide Scheduled Reports')
    _add_column_if_missing('ui_show_invoice_approvals', 'Show/hide Invoice Approvals')
    _add_column_if_missing('ui_show_payment_gateways', 'Show/hide Payment Gateways')
    _add_column_if_missing('ui_show_recurring_invoices', 'Show/hide Recurring Invoices')
    _add_column_if_missing('ui_show_payments', 'Show/hide Payments')
    _add_column_if_missing('ui_show_budget_alerts', 'Show/hide Budget Alerts')
    
    # Analytics
    _add_column_if_missing('ui_show_analytics', 'Show/hide Analytics')
    
    # Tools & Data section
    _add_column_if_missing('ui_show_tools', 'Show/hide Tools & Data section')


def downgrade():
    """Remove UI feature flag fields from users table"""
    # Remove in reverse order
    columns_to_drop = [
        'ui_show_tools',
        'ui_show_analytics',
        'ui_show_budget_alerts',
        'ui_show_payments',
        'ui_show_recurring_invoices',
        'ui_show_payment_gateways',
        'ui_show_invoice_approvals',
        'ui_show_scheduled_reports',
        'ui_show_report_builder',
        'ui_show_reports',
        'ui_show_quotes',
        'ui_show_weekly_goals',
        'ui_show_gantt_chart',
        'ui_show_project_templates',
        'ui_show_calendar',
        'ui_show_kanban_board',
        'ui_show_per_diem',
        'ui_show_mileage',
        'ui_show_inventory',
    ]
    
    for column in columns_to_drop:
        try:
            op.drop_column('users', column)
            print(f"✓ Dropped {column} column from users table")
        except Exception as e:
            print(f"⚠ Warning dropping {column} column: {e}")

