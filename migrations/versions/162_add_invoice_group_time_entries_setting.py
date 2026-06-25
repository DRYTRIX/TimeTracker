"""Add invoice_group_time_entries setting.

Revision ID: 162_add_invoice_group_time_entries_setting
Revises: 161_add_workflow_templates
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "162_add_invoice_group_time_entries_setting"
down_revision = "161_add_workflow_templates"
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
    if "settings" in inspector.get_table_names() and not _has_column(
        inspector, "settings", "invoice_group_time_entries"
    ):
        op.add_column(
            "settings",
            sa.Column("invoice_group_time_entries", sa.Boolean(), nullable=False, server_default=sa.true()),
        )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if "settings" in inspector.get_table_names() and _has_column(inspector, "settings", "invoice_group_time_entries"):
        op.drop_column("settings", "invoice_group_time_entries")
