"""Add keyboard_shortcuts_overrides to users for per-user shortcut customization

Revision ID: 139_keyboard_shortcuts
Revises: 138_add_break_rules
Create Date: 2026-03-16

Stores JSON dict { "shortcut_id": "normalized_key" }. None/empty = use defaults.
"""
from alembic import op
import sqlalchemy as sa


revision = "139_keyboard_shortcuts"
down_revision = "138_add_break_rules"
branch_labels = None
depends_on = None


def upgrade():
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)
    if "users" not in inspector.get_table_names():
        return
    columns = {c["name"] for c in inspector.get_columns("users")}
    if "keyboard_shortcuts_overrides" in columns:
        return
    op.add_column(
        "users",
        sa.Column("keyboard_shortcuts_overrides", sa.JSON(), nullable=True),
    )


def downgrade():
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)
    if "users" not in inspector.get_table_names():
        return
    columns = {c["name"] for c in inspector.get_columns("users")}
    if "keyboard_shortcuts_overrides" not in columns:
        return
    op.drop_column("users", "keyboard_shortcuts_overrides")
