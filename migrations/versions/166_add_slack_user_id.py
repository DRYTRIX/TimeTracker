"""Add slack_user_id to users for Slack attendance mapping.

Revision ID: 166_add_slack_user_id
Revises: 165_add_missed_clock_in_notifications
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "166_add_slack_user_id"
down_revision = "165_add_missed_clock_in_notifications"
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    try:
        return column_name in {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return False


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    try:
        return index_name in {idx["name"] for idx in inspector.get_indexes(table_name)}
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if not _has_column(inspector, "users", "slack_user_id"):
        op.add_column("users", sa.Column("slack_user_id", sa.String(length=50), nullable=True))
    if not _has_index(inspector, "users", "ix_users_slack_user_id"):
        op.create_index("ix_users_slack_user_id", "users", ["slack_user_id"], unique=True)


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if _has_index(inspector, "users", "ix_users_slack_user_id"):
        op.drop_index("ix_users_slack_user_id", table_name="users")
    if _has_column(inspector, "users", "slack_user_id"):
        op.drop_column("users", "slack_user_id")
