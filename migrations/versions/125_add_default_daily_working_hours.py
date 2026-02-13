"""Add default_daily_working_hours to settings

Revision ID: 125_add_default_daily_working_hours
Revises: 124_add_time_entry_requirements
Create Date: 2026-02-13

Admin-configurable default daily working hours for new users (overtime).
"""
from alembic import op
import sqlalchemy as sa

revision = "125_add_default_daily_working_hours"
down_revision = "124_add_time_entry_requirements"
branch_labels = None
depends_on = None


def upgrade():
    """Add default_daily_working_hours to settings"""
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)

    existing_tables = inspector.get_table_names()
    if "settings" not in existing_tables:
        return

    settings_columns = {c["name"] for c in inspector.get_columns("settings")}
    if "default_daily_working_hours" in settings_columns:
        print("✓ Column default_daily_working_hours already exists in settings table")
        return

    try:
        op.add_column(
            "settings",
            sa.Column("default_daily_working_hours", sa.Float(), nullable=False, server_default="8.0"),
        )
        print("✓ Added default_daily_working_hours column to settings table")
    except Exception as e:
        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
            print("✓ Column default_daily_working_hours already exists in settings table (detected via error)")
        else:
            raise


def downgrade():
    """Remove default_daily_working_hours from settings"""
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)

    existing_tables = inspector.get_table_names()
    if "settings" not in existing_tables:
        return

    settings_columns = {c["name"] for c in inspector.get_columns("settings")}
    if "default_daily_working_hours" not in settings_columns:
        print("⊘ Column default_daily_working_hours does not exist in settings table, skipping")
        return

    try:
        op.drop_column("settings", "default_daily_working_hours")
        print("✓ Dropped default_daily_working_hours column from settings table")
    except Exception as e:
        if "does not exist" in str(e).lower() or "no such column" in str(e).lower():
            print("⊘ Column default_daily_working_hours does not exist (detected via error)")
        else:
            raise
