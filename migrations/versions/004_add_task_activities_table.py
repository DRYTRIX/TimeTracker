"""add task_activities table

Revision ID: 004
Revises: 003
Create Date: 2025-09-07 10:35:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create task_activities table"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    
    if 'task_activities' in existing_tables:
        print("✓ Table task_activities already exists")
        # Ensure indexes exist
        try:
            existing_indexes = [idx['name'] for idx in inspector.get_indexes('task_activities')]
            indexes_to_create = [
                ('idx_task_activities_task_id', ['task_id']),
                ('idx_task_activities_user_id', ['user_id']),
                ('idx_task_activities_event', ['event']),
                ('idx_task_activities_created_at', ['created_at']),
            ]
            for idx_name, cols in indexes_to_create:
                if idx_name not in existing_indexes:
                    try:
                        op.create_index(idx_name, 'task_activities', cols)
                    except Exception:
                        pass
        except Exception:
            pass
        return
    
    try:
        op.create_table(
            'task_activities',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('task_id', sa.Integer(), sa.ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True),
            sa.Column('event', sa.String(length=50), nullable=False, index=True),
            sa.Column('details', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        )

        # Explicit indexes (in addition to inline index=True for portability)
        op.create_index('idx_task_activities_task_id', 'task_activities', ['task_id'])
        op.create_index('idx_task_activities_user_id', 'task_activities', ['user_id'])
        op.create_index('idx_task_activities_event', 'task_activities', ['event'])
        op.create_index('idx_task_activities_created_at', 'task_activities', ['created_at'])
        print("✓ Created task_activities table")
    except Exception as e:
        error_msg = str(e)
        if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
            print("✓ Table task_activities already exists (detected via error)")
        else:
            print(f"✗ Error creating task_activities table: {e}")
            raise


def downgrade() -> None:
    """Drop task_activities table"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    
    if 'task_activities' not in existing_tables:
        print("⊘ Table task_activities does not exist, skipping")
        return
    
    try:
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('task_activities')]
        for idx_name in ['idx_task_activities_created_at', 'idx_task_activities_event', 
                        'idx_task_activities_user_id', 'idx_task_activities_task_id']:
            if idx_name in existing_indexes:
                try:
                    op.drop_index(idx_name, table_name='task_activities')
                except Exception:
                    pass
        op.drop_table('task_activities')
        print("✓ Dropped task_activities table")
    except Exception as e:
        error_msg = str(e)
        if 'does not exist' in error_msg.lower() or 'no such table' in error_msg.lower():
            print("⊘ Table task_activities does not exist (detected via error)")
        else:
            print(f"⚠ Warning: Could not drop task_activities table: {e}")


