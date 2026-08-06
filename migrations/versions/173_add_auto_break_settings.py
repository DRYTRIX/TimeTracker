"""Add auto-break deduction settings columns.

Revision ID: 173_add_auto_break_settings
Revises: 172_add_workday_auto_close_confirmation
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "173_add_auto_break_settings"
down_revision = "172_add_workday_auto_close_confirmation"
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    try:
        return column_name in {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if not _has_column(inspector, "settings", "auto_break_enabled"):
        op.add_column(
            "settings",
            sa.Column("auto_break_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
    if not _has_column(inspector, "settings", "auto_break_after_hours"):
        op.add_column(
            "settings",
            sa.Column("auto_break_after_hours", sa.Float(), nullable=False, server_default="6.0"),
        )
    if not _has_column(inspector, "settings", "auto_break_duration_minutes"):
        op.add_column(
            "settings",
            sa.Column("auto_break_duration_minutes", sa.Integer(), nullable=False, server_default="30"),
        )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    for col in (
        "auto_break_duration_minutes",
        "auto_break_after_hours",
        "auto_break_enabled",
    ):
        if _has_column(inspector, "settings", col):
            op.drop_column("settings", col)
