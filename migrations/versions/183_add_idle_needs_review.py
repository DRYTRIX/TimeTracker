"""Add idle_flagged_at to time_entries for needs-review idle handling.

When the idle grace window expires unanswered, the timer is no longer
auto-stopped: it keeps running and is flagged for review instead.

Revision ID: 183_add_idle_needs_review
Revises: 182_add_project_last_used_at
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "183_add_idle_needs_review"
down_revision = "182_add_project_last_used_at"
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
    if not _has_column(inspector, "time_entries", "idle_flagged_at"):
        op.add_column(
            "time_entries",
            sa.Column("idle_flagged_at", sa.DateTime(), nullable=True),
        )
    if not _has_column(inspector, "settings", "idle_auto_stop_hours"):
        op.add_column(
            "settings",
            sa.Column("idle_auto_stop_hours", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if _has_column(inspector, "settings", "idle_auto_stop_hours"):
        op.drop_column("settings", "idle_auto_stop_hours")
    if _has_column(inspector, "time_entries", "idle_flagged_at"):
        op.drop_column("time_entries", "idle_flagged_at")
