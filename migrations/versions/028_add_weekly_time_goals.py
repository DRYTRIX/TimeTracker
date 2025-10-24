"""Add weekly time goals table for tracking weekly hour targets

Revision ID: 028
Revises: 027
Create Date: 2025-10-24 12:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '028'
down_revision = '027'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create weekly_time_goals table"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    # Check if weekly_time_goals table already exists
    if 'weekly_time_goals' not in inspector.get_table_names():
        op.create_table('weekly_time_goals',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('target_hours', sa.Float(), nullable=False),
            sa.Column('week_start_date', sa.Date(), nullable=False),
            sa.Column('week_end_date', sa.Date(), nullable=False),
            sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Create indexes for better performance
        op.create_index('ix_weekly_time_goals_user_id', 'weekly_time_goals', ['user_id'], unique=False)
        op.create_index('ix_weekly_time_goals_week_start_date', 'weekly_time_goals', ['week_start_date'], unique=False)
        op.create_index('ix_weekly_time_goals_status', 'weekly_time_goals', ['status'], unique=False)
        
        # Create composite index for finding current week goals efficiently
        op.create_index(
            'ix_weekly_time_goals_user_week',
            'weekly_time_goals',
            ['user_id', 'week_start_date'],
            unique=False
        )
        
        print("✓ Created weekly_time_goals table")
    else:
        print("ℹ weekly_time_goals table already exists")


def downgrade() -> None:
    """Drop weekly_time_goals table"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    # Check if weekly_time_goals table exists before trying to drop it
    if 'weekly_time_goals' in inspector.get_table_names():
        try:
            # Drop indexes first
            op.drop_index('ix_weekly_time_goals_user_week', table_name='weekly_time_goals')
            op.drop_index('ix_weekly_time_goals_status', table_name='weekly_time_goals')
            op.drop_index('ix_weekly_time_goals_week_start_date', table_name='weekly_time_goals')
            op.drop_index('ix_weekly_time_goals_user_id', table_name='weekly_time_goals')
            
            # Drop the table
            op.drop_table('weekly_time_goals')
            print("✓ Dropped weekly_time_goals table")
        except Exception as e:
            print(f"⚠ Warning dropping weekly_time_goals table: {e}")
    else:
        print("ℹ weekly_time_goals table does not exist")

