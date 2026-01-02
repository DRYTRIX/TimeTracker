"""Add missing module visibility flags to settings and users

Revision ID: 092_missing_module_flags
Revises: 091
Create Date: 2025-01-27 12:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "092_missing_module_flags"
# Important: this migration must come AFTER 091, otherwise Alembic sees 090 as a
# branchpoint (multiple heads) and upgrades can fail.
down_revision = "091_add_integration_external_event_links"
branch_labels = None
depends_on = None


def upgrade():
    """Add missing module visibility flags to settings and users tables."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

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
    def _add_bool_column(table_name: str, column_name: str):
        try:
            # Check if table exists
            table_names = set(inspector.get_table_names())
            if table_name not in table_names:
                print(f"⚠ {table_name} table does not exist, skipping {column_name} column")
                return
            
            # Check if column already exists
            current_cols = {c['name'] for c in inspector.get_columns(table_name)}
            if column_name in current_cols:
                print(f"✓ Column {column_name} already exists in {table_name} table")
                return
        except Exception as e:
            print(f"⚠ Warning checking for {column_name} column: {e}")
        
        try:
            op.add_column(
                table_name,
                sa.Column(column_name, sa.Boolean(), nullable=False, server_default=sa.text(bool_true_default)),
            )
            print(f"✓ Added {column_name} column to {table_name} table")
        except Exception as e:
            error_msg = str(e)
            if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
                print(f"✓ Column {column_name} already exists in {table_name} table (detected via error)")
            else:
                print(f"✗ Error adding {column_name} column to {table_name} table: {e}")
                raise

    # Settings table - Tools & Data section
    _add_bool_column("settings", "ui_allow_integrations")
    _add_bool_column("settings", "ui_allow_import_export")
    _add_bool_column("settings", "ui_allow_saved_filters")

    # Settings table - CRM section (additional)
    _add_bool_column("settings", "ui_allow_contacts")
    _add_bool_column("settings", "ui_allow_deals")
    _add_bool_column("settings", "ui_allow_leads")

    # Settings table - Finance section (additional)
    _add_bool_column("settings", "ui_allow_invoices")
    _add_bool_column("settings", "ui_allow_expenses")

    # Settings table - Time Tracking section (additional)
    _add_bool_column("settings", "ui_allow_time_entry_templates")

    # Settings table - Advanced features
    _add_bool_column("settings", "ui_allow_workflows")
    _add_bool_column("settings", "ui_allow_time_approvals")
    _add_bool_column("settings", "ui_allow_activity_feed")
    _add_bool_column("settings", "ui_allow_recurring_tasks")
    _add_bool_column("settings", "ui_allow_team_chat")
    _add_bool_column("settings", "ui_allow_client_portal")
    _add_bool_column("settings", "ui_allow_kiosk")

    # Users table - Tools & Data section
    _add_bool_column("users", "ui_show_integrations")
    _add_bool_column("users", "ui_show_import_export")
    _add_bool_column("users", "ui_show_saved_filters")

    # Users table - CRM section (additional)
    _add_bool_column("users", "ui_show_contacts")
    _add_bool_column("users", "ui_show_deals")
    _add_bool_column("users", "ui_show_leads")

    # Users table - Finance section (additional)
    _add_bool_column("users", "ui_show_invoices")
    _add_bool_column("users", "ui_show_expenses")

    # Users table - Time Tracking section (additional)
    _add_bool_column("users", "ui_show_time_entry_templates")
    _add_bool_column("users", "ui_show_issues")  # Missing from migration 077

    # Users table - Advanced features
    _add_bool_column("users", "ui_show_workflows")
    _add_bool_column("users", "ui_show_time_approvals")
    _add_bool_column("users", "ui_show_activity_feed")
    _add_bool_column("users", "ui_show_recurring_tasks")
    _add_bool_column("users", "ui_show_team_chat")
    _add_bool_column("users", "ui_show_client_portal")
    _add_bool_column("users", "ui_show_kiosk")


def downgrade():
    """Remove missing module visibility flags from settings and users tables."""
    columns_to_drop_settings = [
        "ui_allow_kiosk",
        "ui_allow_client_portal",
        "ui_allow_team_chat",
        "ui_allow_recurring_tasks",
        "ui_allow_activity_feed",
        "ui_allow_time_approvals",
        "ui_allow_workflows",
        "ui_allow_time_entry_templates",
        "ui_allow_expenses",
        "ui_allow_invoices",
        "ui_allow_leads",
        "ui_allow_deals",
        "ui_allow_contacts",
        "ui_allow_saved_filters",
        "ui_allow_import_export",
        "ui_allow_integrations",
    ]

    columns_to_drop_users = [
        "ui_show_kiosk",
        "ui_show_client_portal",
        "ui_show_team_chat",
        "ui_show_recurring_tasks",
        "ui_show_activity_feed",
        "ui_show_time_approvals",
        "ui_show_workflows",
        "ui_show_time_entry_templates",
        "ui_show_expenses",
        "ui_show_invoices",
        "ui_show_leads",
        "ui_show_deals",
        "ui_show_contacts",
        "ui_show_saved_filters",
        "ui_show_import_export",
        "ui_show_integrations",
    ]

    for name in columns_to_drop_settings:
        try:
            op.drop_column("settings", name)
            print(f"✓ Dropped {name} column from settings table")
        except Exception as e:
            print(f"⚠ Warning dropping {name} column from settings table: {e}")

    for name in columns_to_drop_users:
        try:
            op.drop_column("users", name)
            print(f"✓ Dropped {name} column from users table")
        except Exception as e:
            print(f"⚠ Warning dropping {name} column from users table: {e}")

