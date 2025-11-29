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
    bind = op.get_bind()
    dialect_name = bind.dialect.name if bind else 'generic'
    
    # Add UI feature flags to users table
    # All default to True (enabled) for backward compatibility
    try:
        # Show/hide Inventory section in navigation
        op.add_column('users', sa.Column('ui_show_inventory', sa.Boolean(), nullable=False, server_default='1'))
        print("✓ Added ui_show_inventory column to users table")
    except Exception as e:
        print(f"⚠ Warning adding ui_show_inventory column: {e}")
    
    try:
        # Show/hide Mileage under Finance & Expenses
        op.add_column('users', sa.Column('ui_show_mileage', sa.Boolean(), nullable=False, server_default='1'))
        print("✓ Added ui_show_mileage column to users table")
    except Exception as e:
        print(f"⚠ Warning adding ui_show_mileage column: {e}")
    
    try:
        # Show/hide Per Diem under Finance & Expenses
        op.add_column('users', sa.Column('ui_show_per_diem', sa.Boolean(), nullable=False, server_default='1'))
        print("✓ Added ui_show_per_diem column to users table")
    except Exception as e:
        print(f"⚠ Warning adding ui_show_per_diem column: {e}")
    
    try:
        # Show/hide Kanban Board under Time Tracking
        op.add_column('users', sa.Column('ui_show_kanban_board', sa.Boolean(), nullable=False, server_default='1'))
        print("✓ Added ui_show_kanban_board column to users table")
    except Exception as e:
        print(f"⚠ Warning adding ui_show_kanban_board column: {e}")
    
    # Calendar section
    try:
        op.add_column('users', sa.Column('ui_show_calendar', sa.Boolean(), nullable=False, server_default='1'))
        print("✓ Added ui_show_calendar column to users table")
    except Exception as e:
        print(f"⚠ Warning adding ui_show_calendar column: {e}")
    
    # Time Tracking section items
    try:
        op.add_column('users', sa.Column('ui_show_project_templates', sa.Boolean(), nullable=False, server_default='1'))
        print("✓ Added ui_show_project_templates column to users table")
    except Exception as e:
        print(f"⚠ Warning adding ui_show_project_templates column: {e}")
    
    try:
        op.add_column('users', sa.Column('ui_show_gantt_chart', sa.Boolean(), nullable=False, server_default='1'))
        print("✓ Added ui_show_gantt_chart column to users table")
    except Exception as e:
        print(f"⚠ Warning adding ui_show_gantt_chart column: {e}")
    
    try:
        op.add_column('users', sa.Column('ui_show_weekly_goals', sa.Boolean(), nullable=False, server_default='1'))
        print("✓ Added ui_show_weekly_goals column to users table")
    except Exception as e:
        print(f"⚠ Warning adding ui_show_weekly_goals column: {e}")
    
    # CRM section
    try:
        op.add_column('users', sa.Column('ui_show_quotes', sa.Boolean(), nullable=False, server_default='1'))
        print("✓ Added ui_show_quotes column to users table")
    except Exception as e:
        print(f"⚠ Warning adding ui_show_quotes column: {e}")
    
    # Finance & Expenses section items
    try:
        op.add_column('users', sa.Column('ui_show_reports', sa.Boolean(), nullable=False, server_default='1'))
        print("✓ Added ui_show_reports column to users table")
    except Exception as e:
        print(f"⚠ Warning adding ui_show_reports column: {e}")
    
    try:
        op.add_column('users', sa.Column('ui_show_report_builder', sa.Boolean(), nullable=False, server_default='1'))
        print("✓ Added ui_show_report_builder column to users table")
    except Exception as e:
        print(f"⚠ Warning adding ui_show_report_builder column: {e}")
    
    try:
        op.add_column('users', sa.Column('ui_show_scheduled_reports', sa.Boolean(), nullable=False, server_default='1'))
        print("✓ Added ui_show_scheduled_reports column to users table")
    except Exception as e:
        print(f"⚠ Warning adding ui_show_scheduled_reports column: {e}")
    
    try:
        op.add_column('users', sa.Column('ui_show_invoice_approvals', sa.Boolean(), nullable=False, server_default='1'))
        print("✓ Added ui_show_invoice_approvals column to users table")
    except Exception as e:
        print(f"⚠ Warning adding ui_show_invoice_approvals column: {e}")
    
    try:
        op.add_column('users', sa.Column('ui_show_payment_gateways', sa.Boolean(), nullable=False, server_default='1'))
        print("✓ Added ui_show_payment_gateways column to users table")
    except Exception as e:
        print(f"⚠ Warning adding ui_show_payment_gateways column: {e}")
    
    try:
        op.add_column('users', sa.Column('ui_show_recurring_invoices', sa.Boolean(), nullable=False, server_default='1'))
        print("✓ Added ui_show_recurring_invoices column to users table")
    except Exception as e:
        print(f"⚠ Warning adding ui_show_recurring_invoices column: {e}")
    
    try:
        op.add_column('users', sa.Column('ui_show_payments', sa.Boolean(), nullable=False, server_default='1'))
        print("✓ Added ui_show_payments column to users table")
    except Exception as e:
        print(f"⚠ Warning adding ui_show_payments column: {e}")
    
    try:
        op.add_column('users', sa.Column('ui_show_budget_alerts', sa.Boolean(), nullable=False, server_default='1'))
        print("✓ Added ui_show_budget_alerts column to users table")
    except Exception as e:
        print(f"⚠ Warning adding ui_show_budget_alerts column: {e}")
    
    # Analytics
    try:
        op.add_column('users', sa.Column('ui_show_analytics', sa.Boolean(), nullable=False, server_default='1'))
        print("✓ Added ui_show_analytics column to users table")
    except Exception as e:
        print(f"⚠ Warning adding ui_show_analytics column: {e}")
    
    # Tools & Data section
    try:
        op.add_column('users', sa.Column('ui_show_tools', sa.Boolean(), nullable=False, server_default='1'))
        print("✓ Added ui_show_tools column to users table")
    except Exception as e:
        print(f"⚠ Warning adding ui_show_tools column: {e}")


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

