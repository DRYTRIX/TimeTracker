"""Add calendar_events table for agenda/calendar support

Revision ID: 034_add_calendar_events
Revises: 033_add_email_settings
Create Date: 2025-10-27

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '034_add_calendar_events'
down_revision = '033_add_email_settings'
branch_labels = None
depends_on = None


def upgrade():
    """Create calendar_events table"""
    op.create_table(
        'calendar_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=False),
        sa.Column('all_day', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('location', sa.String(length=200), nullable=True),
        sa.Column('event_type', sa.String(length=50), nullable=False, server_default='event'),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('task_id', sa.Integer(), nullable=True),
        sa.Column('client_id', sa.Integer(), nullable=True),
        sa.Column('is_recurring', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('recurrence_rule', sa.String(length=200), nullable=True),
        sa.Column('recurrence_end_date', sa.DateTime(), nullable=True),
        sa.Column('parent_event_id', sa.Integer(), nullable=True),
        sa.Column('reminder_minutes', sa.Integer(), nullable=True),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('is_private', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_calendar_events_user_id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name='fk_calendar_events_project_id'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], name='fk_calendar_events_task_id'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], name='fk_calendar_events_client_id'),
        sa.ForeignKeyConstraint(['parent_event_id'], ['calendar_events.id'], name='fk_calendar_events_parent_event_id'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for better query performance
    with op.batch_alter_table('calendar_events', schema=None) as batch_op:
        batch_op.create_index('ix_calendar_events_user_id', ['user_id'])
        batch_op.create_index('ix_calendar_events_start_time', ['start_time'])
        batch_op.create_index('ix_calendar_events_end_time', ['end_time'])
        batch_op.create_index('ix_calendar_events_event_type', ['event_type'])
        batch_op.create_index('ix_calendar_events_project_id', ['project_id'])
        batch_op.create_index('ix_calendar_events_task_id', ['task_id'])
        batch_op.create_index('ix_calendar_events_client_id', ['client_id'])
        batch_op.create_index('ix_calendar_events_parent_event_id', ['parent_event_id'])


def downgrade():
    """Drop calendar_events table"""
    op.drop_table('calendar_events')

