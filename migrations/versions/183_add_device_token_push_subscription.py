"""Add device_token and platform to push_subscriptions for FCM (Issue #722).

Revision ID: 183_add_device_token_push_subscription
Revises: 182_add_project_last_used_at
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "183_add_device_token_push_subscription"
down_revision = "182_add_project_last_used_at"
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    try:
        return column_name in {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return False


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    try:
        if table_name not in inspector.get_table_names():
            return False
        return any(idx["name"] == index_name for idx in inspector.get_indexes(table_name))
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if "push_subscriptions" not in inspector.get_table_names():
        return

    if not _has_column(inspector, "push_subscriptions", "device_token"):
        op.add_column(
            "push_subscriptions",
            sa.Column("device_token", sa.String(length=512), nullable=True),
        )
    if not _has_column(inspector, "push_subscriptions", "platform"):
        op.add_column(
            "push_subscriptions",
            sa.Column("platform", sa.String(length=20), nullable=True),
        )

    inspector = inspect(bind)
    if not _has_index(inspector, "push_subscriptions", "ix_push_subscriptions_device_token"):
        try:
            op.create_index(
                "ix_push_subscriptions_device_token",
                "push_subscriptions",
                ["device_token"],
                unique=False,
            )
        except Exception:
            pass


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if "push_subscriptions" not in inspector.get_table_names():
        return
    if _has_index(inspector, "push_subscriptions", "ix_push_subscriptions_device_token"):
        try:
            op.drop_index("ix_push_subscriptions_device_token", table_name="push_subscriptions")
        except Exception:
            pass
    if _has_column(inspector, "push_subscriptions", "platform"):
        op.drop_column("push_subscriptions", "platform")
    if _has_column(inspector, "push_subscriptions", "device_token"):
        op.drop_column("push_subscriptions", "device_token")
