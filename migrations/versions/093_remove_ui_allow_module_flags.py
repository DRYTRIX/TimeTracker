"""Remove ui_allow_ module visibility flags from settings

Revision ID: 093_remove_ui_allow_flags
Revises: 092_missing_module_flags
Create Date: 2025-01-27 12:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "093_remove_ui_allow_flags"
down_revision = "092_missing_module_flags"
branch_labels = None
depends_on = None


def upgrade():
    """Remove ui_allow_* columns from settings table.
    
    These columns are no longer needed as modules are now enabled by default
    and controlled via the ModuleRegistry system and user preferences.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Check if settings table exists
    table_names = set(inspector.get_table_names())
    if 'settings' not in table_names:
        print("⚠ Settings table does not exist, skipping ui_allow_ column removal")
        return

    # List of all ui_allow_ columns to remove
    ui_allow_columns = [
        "ui_allow_calendar",
        "ui_allow_project_templates",
        "ui_allow_gantt_chart",
        "ui_allow_kanban_board",
        "ui_allow_weekly_goals",
        "ui_allow_issues",
        "ui_allow_time_entry_templates",
        "ui_allow_quotes",
        "ui_allow_contacts",
        "ui_allow_deals",
        "ui_allow_leads",
        "ui_allow_reports",
        "ui_allow_report_builder",
        "ui_allow_scheduled_reports",
        "ui_allow_invoices",
        "ui_allow_invoice_approvals",
        "ui_allow_recurring_invoices",
        "ui_allow_payments",
        "ui_allow_payment_gateways",
        "ui_allow_expenses",
        "ui_allow_mileage",
        "ui_allow_per_diem",
        "ui_allow_budget_alerts",
        "ui_allow_inventory",
        "ui_allow_analytics",
        "ui_allow_tools",
        "ui_allow_integrations",
        "ui_allow_import_export",
        "ui_allow_saved_filters",
        "ui_allow_workflows",
        "ui_allow_time_approvals",
        "ui_allow_activity_feed",
        "ui_allow_recurring_tasks",
        "ui_allow_team_chat",
        "ui_allow_client_portal",
        "ui_allow_kiosk",
    ]

    # Helper to drop a column if it exists
    def _drop_column_if_exists(table_name: str, column_name: str):
        try:
            current_cols = {c['name'] for c in inspector.get_columns(table_name)}
            if column_name in current_cols:
                op.drop_column(table_name, column_name)
                print(f"✓ Dropped {column_name} column from {table_name} table")
            else:
                print(f"⊘ Column {column_name} does not exist in {table_name} table, skipping")
        except Exception as e:
            error_msg = str(e)
            # Column might already be dropped or not exist
            if 'does not exist' in error_msg.lower() or 'no such column' in error_msg.lower():
                print(f"⊘ Column {column_name} does not exist in {table_name} table (detected via error)")
            else:
                print(f"⚠ Warning: Could not drop {column_name} column: {e}")

    # Drop all ui_allow_ columns
    for column_name in ui_allow_columns:
        _drop_column_if_exists("settings", column_name)


def downgrade():
    """Re-add ui_allow_* columns to settings table.
    
    Note: This will restore the columns with default value True.
    """
    bind = op.get_bind()
    
    # Determine database dialect for proper default values
    dialect_name = bind.dialect.name if bind else "generic"
    
    # Set appropriate boolean defaults based on database
    if dialect_name == 'sqlite':
        bool_true_default = '1'
    elif dialect_name == 'postgresql':
        bool_true_default = 'true'
    else:  # MySQL/MariaDB and others
        bool_true_default = '1'

    # List of all ui_allow_ columns to re-add
    ui_allow_columns = [
        "ui_allow_calendar",
        "ui_allow_project_templates",
        "ui_allow_gantt_chart",
        "ui_allow_kanban_board",
        "ui_allow_weekly_goals",
        "ui_allow_issues",
        "ui_allow_time_entry_templates",
        "ui_allow_quotes",
        "ui_allow_contacts",
        "ui_allow_deals",
        "ui_allow_leads",
        "ui_allow_reports",
        "ui_allow_report_builder",
        "ui_allow_scheduled_reports",
        "ui_allow_invoices",
        "ui_allow_invoice_approvals",
        "ui_allow_recurring_invoices",
        "ui_allow_payments",
        "ui_allow_payment_gateways",
        "ui_allow_expenses",
        "ui_allow_mileage",
        "ui_allow_per_diem",
        "ui_allow_budget_alerts",
        "ui_allow_inventory",
        "ui_allow_analytics",
        "ui_allow_tools",
        "ui_allow_integrations",
        "ui_allow_import_export",
        "ui_allow_saved_filters",
        "ui_allow_workflows",
        "ui_allow_time_approvals",
        "ui_allow_activity_feed",
        "ui_allow_recurring_tasks",
        "ui_allow_team_chat",
        "ui_allow_client_portal",
        "ui_allow_kiosk",
    ]

    # Re-add all columns with default True
    for column_name in ui_allow_columns:
        try:
            op.add_column(
                "settings",
                sa.Column(column_name, sa.Boolean(), nullable=False, server_default=sa.text(bool_true_default)),
            )
            print(f"✓ Re-added {column_name} column to settings table")
        except Exception as e:
            error_msg = str(e)
            if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
                print(f"⊘ Column {column_name} already exists in settings table")
            else:
                print(f"⚠ Warning: Could not re-add {column_name} column: {e}")

