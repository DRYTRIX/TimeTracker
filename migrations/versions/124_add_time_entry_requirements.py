"""Add time entry requirements settings

Revision ID: 124_add_time_entry_requirements
Revises: 123_add_calendar_default_view
Create Date: 2026-02-13

Admin-configurable requirements for task and description when logging time.
"""
from alembic import op
import sqlalchemy as sa

revision = "124_add_time_entry_requirements"
down_revision = "123_add_calendar_default_view"
branch_labels = None
depends_on = None


def upgrade():
    """Add time entry requirements settings"""
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)

    existing_tables = inspector.get_table_names()
    if "settings" not in existing_tables:
        return

    settings_columns = {c["name"] for c in inspector.get_columns("settings")}

    columns_to_add = [
        (
            "time_entry_require_task",
            sa.Column("time_entry_require_task", sa.Boolean(), nullable=False, server_default="0"),
        ),
        (
            "time_entry_require_description",
            sa.Column("time_entry_require_description", sa.Boolean(), nullable=False, server_default="0"),
        ),
        (
            "time_entry_description_min_length",
            sa.Column("time_entry_description_min_length", sa.Integer(), nullable=False, server_default="20"),
        ),
    ]

    for col_name, col_def in columns_to_add:
        if col_name in settings_columns:
            print(f"✓ Column {col_name} already exists in settings table")
            continue

        try:
            op.add_column("settings", col_def)
            print(f"✓ Added {col_name} column to settings table")
        except Exception as e:
            error_msg = str(e)
            if "already exists" in error_msg.lower() or "duplicate" in error_msg.lower():
                print(f"✓ Column {col_name} already exists in settings table (detected via error)")
            else:
                print(f"✗ Error adding {col_name} column: {e}")
                raise


def downgrade():
    """Remove time entry requirements settings"""
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)

    existing_tables = inspector.get_table_names()
    if "settings" not in existing_tables:
        return

    settings_columns = {c["name"] for c in inspector.get_columns("settings")}

    columns_to_drop = [
        "time_entry_description_min_length",
        "time_entry_require_description",
        "time_entry_require_task",
    ]

    for col_name in columns_to_drop:
        if col_name not in settings_columns:
            print(f"⊘ Column {col_name} does not exist in settings table, skipping")
            continue

        try:
            op.drop_column("settings", col_name)
            print(f"✓ Dropped {col_name} column from settings table")
        except Exception as e:
            error_msg = str(e)
            if "does not exist" in error_msg.lower() or "no such column" in error_msg.lower():
                print(f"⊘ Column {col_name} does not exist in settings table (detected via error)")
            else:
                print(f"⚠ Warning: Could not drop {col_name} column: {e}")
