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
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    
    if 'calendar_events' in existing_tables:
        print("✓ Table calendar_events already exists")
        # Ensure indexes exist
        try:
            existing_indexes = [idx['name'] for idx in inspector.get_indexes('calendar_events')]
            indexes_to_create = [
                ('ix_calendar_events_user_id', ['user_id']),
                ('ix_calendar_events_start_time', ['start_time']),
                ('ix_calendar_events_end_time', ['end_time']),
                ('ix_calendar_events_event_type', ['event_type']),
                ('ix_calendar_events_project_id', ['project_id']),
                ('ix_calendar_events_task_id', ['task_id']),
                ('ix_calendar_events_client_id', ['client_id']),
                ('ix_calendar_events_parent_event_id', ['parent_event_id']),
            ]
            for idx_name, cols in indexes_to_create:
                if idx_name not in existing_indexes:
                    try:
                        op.create_index(idx_name, 'calendar_events', cols, unique=False)
                    except Exception:
                        pass
        except Exception:
            pass
        return
    
    try:
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
        print("✓ Created calendar_events table")
    except Exception as e:
        error_msg = str(e)
        if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
            print("✓ Table calendar_events already exists (detected via error)")
        else:
            print(f"✗ Error creating calendar_events table: {e}")
            raise


def downgrade():
    """Drop calendar_events table"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    
    if 'calendar_events' not in existing_tables:
        print("⊘ Table calendar_events does not exist, skipping")
        return
    
    try:
        # Drop indexes first
        try:
            existing_indexes = [idx['name'] for idx in inspector.get_indexes('calendar_events')]
            for idx_name in existing_indexes:
                try:
                    op.drop_index(idx_name, table_name='calendar_events')
                except Exception:
                    pass
        except Exception:
            pass
        
        op.drop_table('calendar_events')
        print("✓ Dropped calendar_events table")
    except Exception as e:
        error_msg = str(e)
        if 'does not exist' in error_msg.lower() or 'no such table' in error_msg.lower():
            print("⊘ Table calendar_events does not exist (detected via error)")
        else:
            print(f"⚠ Warning: Could not drop calendar_events table: {e}")

