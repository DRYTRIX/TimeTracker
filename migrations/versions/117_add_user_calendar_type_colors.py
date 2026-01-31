"""Add user calendar item type colors

Revision ID: 117_add_user_calendar_type_colors
Revises: 116_merge_three_heads
Create Date: 2026-01-31

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '117_add_user_calendar_type_colors'
down_revision = '116_merge_three_heads'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('calendar_color_events', sa.String(length=7), nullable=True))
        batch_op.add_column(sa.Column('calendar_color_tasks', sa.String(length=7), nullable=True))
        batch_op.add_column(sa.Column('calendar_color_time_entries', sa.String(length=7), nullable=True))


def downgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('calendar_color_time_entries')
        batch_op.drop_column('calendar_color_tasks')
        batch_op.drop_column('calendar_color_events')
