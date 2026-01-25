"""Merge three migration heads into one

Revision ID: 116_merge_three_heads
Revises: 090_add_push_subscriptions, 100_gantt_colors_modules, 115_add_exclude_weekends
Create Date: 2026-01-25

Merge revision to resolve multiple heads:
- 090_add_push_subscriptions
- 100_gantt_colors_modules
- 115_add_exclude_weekends
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '116_merge_three_heads'
down_revision = ('090_add_push_subscriptions', '100_gantt_colors_modules', '115_add_exclude_weekends')
branch_labels = None
depends_on = None


def upgrade():
    """No schema changes - merge only."""
    pass


def downgrade():
    """No schema changes - merge only."""
    pass
