"""Add wip_limit to kanban_columns for per-column work-in-progress limits.

Revision ID: 168_add_kanban_wip_limit
Revises: 167_merge_claude_attendance_heads
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "168_add_kanban_wip_limit"
down_revision = "166_add_slack_user_id"
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
    if not _has_column(inspector, "kanban_columns", "wip_limit"):
        op.add_column("kanban_columns", sa.Column("wip_limit", sa.Integer(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if _has_column(inspector, "kanban_columns", "wip_limit"):
        op.drop_column("kanban_columns", "wip_limit")
