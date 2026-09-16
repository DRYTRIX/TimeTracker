"""Add Pomodoro default length columns to users.

Revision ID: 185_add_pomodoro_user_defaults
Revises: 184_merge_183_heads
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "185_add_pomodoro_user_defaults"
down_revision = "184_merge_183_heads"
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
    cols = [
        ("pomodoro_length", sa.Integer(), "25"),
        ("pomodoro_short_break", sa.Integer(), "5"),
        ("pomodoro_long_break", sa.Integer(), "15"),
        ("pomodoro_long_break_interval", sa.Integer(), "4"),
    ]
    for name, col_type, default in cols:
        if not _has_column(inspector, "users", name):
            op.add_column(
                "users",
                sa.Column(name, col_type, nullable=False, server_default=default),
            )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    for name in (
        "pomodoro_long_break_interval",
        "pomodoro_long_break",
        "pomodoro_short_break",
        "pomodoro_length",
    ):
        if _has_column(inspector, "users", name):
            op.drop_column("users", name)
