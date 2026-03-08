"""Merge heads 132_add_timesheet_governance_and_time_off and 129_add_task_tags

Revision ID: 133_merge_132_129_heads
Revises: 132_add_timesheet_governance_and_time_off, 129_add_task_tags
Create Date: 2026-03-08

Resolves multiple heads so 'alembic upgrade head' / 'flask db upgrade' can run.
Branch from 117: 118_add_locked_client_id -> 119..128 -> 129_add_task_tags.
Branch from 129_merge_118_128_heads: 130 -> 131 -> 132.
"""
from alembic import op


revision = "133_merge_132_129_heads"
down_revision = ("132_add_timesheet_governance_and_time_off", "129_add_task_tags")
branch_labels = None
depends_on = None


def upgrade():
    """No schema changes - merge only."""
    pass


def downgrade():
    """No schema changes - merge only."""
    pass
