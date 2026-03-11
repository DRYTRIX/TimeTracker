"""Add break_seconds and paused_at to time_entries (Issue #561)

Revision ID: 137_add_break_time
Revises: 136_seed_overtime_leave_type
Create Date: 2026-03-11

Break time for timers (pause/resume) and manual time entries.
"""
from alembic import op
import sqlalchemy as sa


revision = "137_add_break_time"
down_revision = "136_seed_overtime_leave_type"
branch_labels = None
depends_on = None


def upgrade():
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)
    if "time_entries" not in inspector.get_table_names():
        return
    columns = {c["name"] for c in inspector.get_columns("time_entries")}

    if "break_seconds" not in columns:
        op.add_column(
            "time_entries",
            sa.Column("break_seconds", sa.Integer(), nullable=True, server_default="0"),
        )
    if "paused_at" not in columns:
        op.add_column(
            "time_entries",
            sa.Column("paused_at", sa.DateTime(), nullable=True),
        )


def downgrade():
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)
    if "time_entries" not in inspector.get_table_names():
        return
    columns = {c["name"] for c in inspector.get_columns("time_entries")}
    if "paused_at" in columns:
        op.drop_column("time_entries", "paused_at")
    if "break_seconds" in columns:
        op.drop_column("time_entries", "break_seconds")
