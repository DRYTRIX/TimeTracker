"""Add user time rounding preferences

Revision ID: 027
Revises: 026
Create Date: 2025-10-24 00:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '027'
down_revision = '026'
branch_labels = None
depends_on = None


def upgrade():
    """Add time rounding preference fields to users table"""
    bind = op.get_bind()
    dialect_name = bind.dialect.name if bind else 'generic'
    
    # Add time rounding preferences to users table
    try:
        # Enable/disable time rounding for this user
        op.add_column('users', sa.Column('time_rounding_enabled', sa.Boolean(), nullable=False, server_default='1'))
        print("✓ Added time_rounding_enabled column to users table")
    except Exception as e:
        print(f"⚠ Warning adding time_rounding_enabled column: {e}")
    
    try:
        # Rounding interval in minutes (1, 5, 10, 15, 30, 60)
        # Default to 1 (no rounding, use exact time)
        op.add_column('users', sa.Column('time_rounding_minutes', sa.Integer(), nullable=False, server_default='1'))
        print("✓ Added time_rounding_minutes column to users table")
    except Exception as e:
        print(f"⚠ Warning adding time_rounding_minutes column: {e}")
    
    try:
        # Rounding method: 'nearest', 'up', 'down'
        # 'nearest' = round to nearest interval
        # 'up' = always round up (ceil)
        # 'down' = always round down (floor)
        op.add_column('users', sa.Column('time_rounding_method', sa.String(10), nullable=False, server_default='nearest'))
        print("✓ Added time_rounding_method column to users table")
    except Exception as e:
        print(f"⚠ Warning adding time_rounding_method column: {e}")


def downgrade():
    """Remove time rounding preference fields from users table"""
    try:
        op.drop_column('users', 'time_rounding_method')
        print("✓ Dropped time_rounding_method column from users table")
    except Exception as e:
        print(f"⚠ Warning dropping time_rounding_method column: {e}")
    
    try:
        op.drop_column('users', 'time_rounding_minutes')
        print("✓ Dropped time_rounding_minutes column from users table")
    except Exception as e:
        print(f"⚠ Warning dropping time_rounding_minutes column: {e}")
    
    try:
        op.drop_column('users', 'time_rounding_enabled')
        print("✓ Dropped time_rounding_enabled column from users table")
    except Exception as e:
        print(f"⚠ Warning dropping time_rounding_enabled column: {e}")

