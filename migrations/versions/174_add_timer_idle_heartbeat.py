"""Add last_heartbeat_at and idle_notified_at to time_entries for idle timeout.

Revision ID: 174_add_timer_idle_heartbeat
Revises: 173_add_auto_break_settings
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "174_add_timer_idle_heartbeat"
down_revision = "173_add_auto_break_settings"
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    try:
        return column_name in {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return False


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    try:
        return index_name in {ix["name"] for ix in inspector.get_indexes(table_name)}
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if not _has_column(inspector, "time_entries", "last_heartbeat_at"):
        op.add_column(
            "time_entries",
            sa.Column("last_heartbeat_at", sa.DateTime(), nullable=True),
        )
    if not _has_column(inspector, "time_entries", "idle_notified_at"):
        op.add_column(
            "time_entries",
            sa.Column("idle_notified_at", sa.DateTime(), nullable=True),
        )
    # Refresh inspector after potential adds
    inspector = inspect(bind)
    if not _has_index(inspector, "time_entries", "ix_time_entries_last_heartbeat_at"):
        try:
            op.create_index(
                "ix_time_entries_last_heartbeat_at",
                "time_entries",
                ["last_heartbeat_at"],
                unique=False,
            )
        except Exception:
            pass


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if _has_index(inspector, "time_entries", "ix_time_entries_last_heartbeat_at"):
        op.drop_index("ix_time_entries_last_heartbeat_at", table_name="time_entries")
    if _has_column(inspector, "time_entries", "idle_notified_at"):
        op.drop_column("time_entries", "idle_notified_at")
    if _has_column(inspector, "time_entries", "last_heartbeat_at"):
        op.drop_column("time_entries", "last_heartbeat_at")
