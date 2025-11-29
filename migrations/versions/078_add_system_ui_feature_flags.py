"""Add system-wide UI feature flags to settings

Revision ID: 078_system_ui_feature_flags
Revises: 077_ui_feature_flags
Create Date: 2025-01-22 00:10:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "078_system_ui_feature_flags"
down_revision = "077_ui_feature_flags"
branch_labels = None
depends_on = None


def upgrade():
    """Add system-wide UI feature flags to settings table.

    These flags control which UI features are available for users to customize.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Check if settings table exists
    table_names = set(inspector.get_table_names())
    if 'settings' not in table_names:
        print("⚠ Settings table does not exist, skipping UI feature flag columns")
        return

    # Determine database dialect for proper default values
    dialect_name = bind.dialect.name if bind else "generic"
    
    # Set appropriate boolean defaults based on database
    if dialect_name == 'sqlite':
        bool_true_default = '1'
    elif dialect_name == 'postgresql':
        bool_true_default = 'true'
    else:  # MySQL/MariaDB and others
        bool_true_default = '1'

    # Helper to add a boolean column with server default true
    def _add_bool_column(name: str):
        # Refresh column list each time to handle partial migrations
        try:
            current_cols = {c['name'] for c in inspector.get_columns('settings')}
            if name in current_cols:
                print(f"✓ Column {name} already exists in settings table")
                return
        except Exception as e:
            print(f"⚠ Warning checking for {name} column: {e}")
        
        try:
            op.add_column(
                "settings",
                sa.Column(name, sa.Boolean(), nullable=False, server_default=sa.text(bool_true_default)),
            )
            print(f"✓ Added {name} column to settings table")
        except Exception as e:
            error_msg = str(e)
            # Check if column already exists (different error messages for different databases)
            if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
                print(f"✓ Column {name} already exists in settings table (detected via error)")
            else:
                # Re-raise the exception for other errors so Alembic can handle it properly
                print(f"✗ Error adding {name} column to settings table: {e}")
                raise

    # Calendar section
    _add_bool_column("ui_allow_calendar")

    # Time Tracking section items
    _add_bool_column("ui_allow_project_templates")
    _add_bool_column("ui_allow_gantt_chart")
    _add_bool_column("ui_allow_kanban_board")
    _add_bool_column("ui_allow_weekly_goals")

    # CRM section
    _add_bool_column("ui_allow_quotes")

    # Finance & Expenses section items
    _add_bool_column("ui_allow_reports")
    _add_bool_column("ui_allow_report_builder")
    _add_bool_column("ui_allow_scheduled_reports")
    _add_bool_column("ui_allow_invoice_approvals")
    _add_bool_column("ui_allow_payment_gateways")
    _add_bool_column("ui_allow_recurring_invoices")
    _add_bool_column("ui_allow_payments")
    _add_bool_column("ui_allow_mileage")
    _add_bool_column("ui_allow_per_diem")
    _add_bool_column("ui_allow_budget_alerts")

    # Inventory section
    _add_bool_column("ui_allow_inventory")

    # Analytics
    _add_bool_column("ui_allow_analytics")

    # Tools & Data section
    _add_bool_column("ui_allow_tools")


def downgrade():
    """Remove system-wide UI feature flags from settings table."""
    columns_to_drop = [
        "ui_allow_tools",
        "ui_allow_analytics",
        "ui_allow_inventory",
        "ui_allow_budget_alerts",
        "ui_allow_per_diem",
        "ui_allow_mileage",
        "ui_allow_payments",
        "ui_allow_recurring_invoices",
        "ui_allow_payment_gateways",
        "ui_allow_invoice_approvals",
        "ui_allow_scheduled_reports",
        "ui_allow_report_builder",
        "ui_allow_reports",
        "ui_allow_quotes",
        "ui_allow_weekly_goals",
        "ui_allow_kanban_board",
        "ui_allow_gantt_chart",
        "ui_allow_project_templates",
        "ui_allow_calendar",
    ]

    for name in columns_to_drop:
        try:
            op.drop_column("settings", name)
            print(f"✓ Dropped {name} column from settings table")
        except Exception as e:
            print(f"⚠ Warning dropping {name} column from settings table: {e}")


