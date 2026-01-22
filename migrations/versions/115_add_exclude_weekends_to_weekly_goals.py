"""Add exclude_weekends column to weekly_time_goals table

Revision ID: 115_add_exclude_weekends
Revises: 114_enhance_audit_logs_timeentry
Create Date: 2025-01-30

Adds exclude_weekends boolean column to support 5-day work week goals
(excluding weekends) in addition to the existing 7-day week goals.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '115_add_exclude_weekends'
down_revision = '114_enhance_audit_logs_timeentry'
branch_labels = None
depends_on = None


def upgrade():
    """Add exclude_weekends column to weekly_time_goals table"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    # Check if weekly_time_goals table exists
    if 'weekly_time_goals' in inspector.get_table_names():
        # Check if column already exists
        columns = [col['name'] for col in inspector.get_columns('weekly_time_goals')]
        
        if 'exclude_weekends' not in columns:
            try:
                op.add_column(
                    'weekly_time_goals',
                    sa.Column('exclude_weekends', sa.Boolean(), nullable=False, server_default='false')
                )
                print("✓ Added exclude_weekends column to weekly_time_goals table")
            except Exception as e:
                print(f"✗ Error adding exclude_weekends column: {e}")
        else:
            print("ℹ Column exclude_weekends already exists in weekly_time_goals table")
    else:
        print("ℹ weekly_time_goals table does not exist, skipping")


def downgrade():
    """Remove exclude_weekends column from weekly_time_goals table"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    # Check if weekly_time_goals table exists
    if 'weekly_time_goals' in inspector.get_table_names():
        # Check if column exists
        columns = [col['name'] for col in inspector.get_columns('weekly_time_goals')]
        
        if 'exclude_weekends' in columns:
            try:
                op.drop_column('weekly_time_goals', 'exclude_weekends')
                print("✓ Dropped exclude_weekends column from weekly_time_goals table")
            except Exception as e:
                print(f"⚠ Warning: Could not drop exclude_weekends column: {e}")
        else:
            print("ℹ Column exclude_weekends does not exist in weekly_time_goals table, skipping")
    else:
        print("ℹ weekly_time_goals table does not exist, skipping")
