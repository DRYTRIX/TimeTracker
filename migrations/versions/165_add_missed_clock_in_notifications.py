"""Add missed clock-in notification user preferences.

Revision ID: 165_add_missed_clock_in_notifications
Revises: 164_add_attendance_compliance
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "165_add_missed_clock_in_notifications"
down_revision = "164_add_attendance_compliance"
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
    if not _has_column(inspector, "users", "smart_notify_missed_clock_in"):
        op.add_column(
            "users",
            sa.Column("smart_notify_missed_clock_in", sa.Boolean(), nullable=False, server_default="0"),
        )
    if not _has_column(inspector, "users", "smart_notify_missed_clock_in_at"):
        op.add_column(
            "users",
            sa.Column("smart_notify_missed_clock_in_at", sa.String(length=5), nullable=True),
        )
    if not _has_column(inspector, "users", "notification_missed_clock_in"):
        op.add_column(
            "users",
            sa.Column("notification_missed_clock_in", sa.Boolean(), nullable=False, server_default="0"),
        )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    for col in (
        "notification_missed_clock_in",
        "smart_notify_missed_clock_in_at",
        "smart_notify_missed_clock_in",
    ):
        if _has_column(inspector, "users", col):
            op.drop_column("users", col)
