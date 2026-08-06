"""Add auto_close_confirmed_at to workday_sessions for forgotten clock-out prompts.

Revision ID: 172_add_workday_auto_close_confirmation
Revises: 171_merge_kanban_feature_heads
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "172_add_workday_auto_close_confirmation"
down_revision = "171_merge_kanban_feature_heads"
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
    if not _has_column(inspector, "workday_sessions", "auto_close_confirmed_at"):
        op.add_column(
            "workday_sessions",
            sa.Column("auto_close_confirmed_at", sa.DateTime(), nullable=True),
        )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if _has_column(inspector, "workday_sessions", "auto_close_confirmed_at"):
        op.drop_column("workday_sessions", "auto_close_confirmed_at")
