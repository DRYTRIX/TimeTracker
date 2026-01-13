"""Add push_subscriptions table for browser push notifications

Revision ID: 090_add_push_subscriptions
Revises: 089_allow_auto_entries_no_project
Create Date: 2026-01-13

This migration adds:
- push_subscriptions table for storing browser push notification subscriptions
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '090_add_push_subscriptions'
down_revision = '089_allow_auto_entries_no_project'
branch_labels = None
depends_on = None


def upgrade():
    """Create push_subscriptions table"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    
    # Create push_subscriptions table
    if 'push_subscriptions' in existing_tables:
        print("✓ Table push_subscriptions already exists")
        # Ensure indexes exist
        try:
            existing_indexes = [idx['name'] for idx in inspector.get_indexes('push_subscriptions')]
            for idx_name, cols in [
                ('ix_push_subscriptions_user_id', ['user_id']),
            ]:
                if idx_name not in existing_indexes:
                    try:
                        op.create_index(idx_name, 'push_subscriptions', cols, unique=False)
                    except Exception:
                        pass
        except Exception:
            pass
    else:
        try:
            op.create_table('push_subscriptions',
                sa.Column('id', sa.Integer(), nullable=False),
                sa.Column('user_id', sa.Integer(), nullable=False),
                sa.Column('endpoint', sa.Text(), nullable=False),
                sa.Column('keys', sa.JSON(), nullable=False),
                sa.Column('user_agent', sa.String(length=500), nullable=True),
                sa.Column('created_at', sa.DateTime(), nullable=False),
                sa.Column('updated_at', sa.DateTime(), nullable=False),
                sa.Column('last_used_at', sa.DateTime(), nullable=True),
                sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
                sa.PrimaryKeyConstraint('id')
            )
            op.create_index('ix_push_subscriptions_user_id', 'push_subscriptions', ['user_id'], unique=False)
            print("✓ Created push_subscriptions table")
        except Exception as e:
            error_msg = str(e)
            if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
                print("✓ Table push_subscriptions already exists (detected via error)")
            else:
                print(f"✗ Error creating push_subscriptions table: {e}")
                raise


def downgrade():
    """Drop push_subscriptions table"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    
    if 'push_subscriptions' in existing_tables:
        try:
            existing_indexes = [idx['name'] for idx in inspector.get_indexes('push_subscriptions')]
            for idx_name in ['ix_push_subscriptions_user_id']:
                if idx_name in existing_indexes:
                    try:
                        op.drop_index(idx_name, table_name='push_subscriptions')
                    except Exception:
                        pass
            op.drop_table('push_subscriptions')
            print("✓ Dropped push_subscriptions table")
        except Exception as e:
            error_msg = str(e)
            if 'does not exist' in error_msg.lower() or 'no such table' in error_msg.lower():
                print("⊘ Table push_subscriptions does not exist (detected via error)")
            else:
                print(f"⚠ Warning: Could not drop push_subscriptions table: {e}")
