"""Add standard_hours_per_day to users

Revision ID: 031
Revises: 030
Create Date: 2025-10-27 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '031'
down_revision = '030'
branch_labels = None
depends_on = None


def upgrade():
    """Add standard_hours_per_day column to users table"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    if 'users' not in existing_tables:
        return
    
    users_columns = {c['name'] for c in inspector.get_columns('users')}
    
    if 'standard_hours_per_day' in users_columns:
        print("✓ Column standard_hours_per_day already exists in users table")
        return
    
    try:
        op.add_column('users', 
            sa.Column('standard_hours_per_day', sa.Float(), nullable=False, server_default='8.0')
        )
        print("✓ Added standard_hours_per_day column to users table")
    except Exception as e:
        error_msg = str(e)
        if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
            print("✓ Column standard_hours_per_day already exists in users table (detected via error)")
        else:
            print(f"✗ Error adding standard_hours_per_day column: {e}")
            raise


def downgrade():
    """Remove standard_hours_per_day column from users table"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    if 'users' not in existing_tables:
        return
    
    users_columns = {c['name'] for c in inspector.get_columns('users')}
    
    if 'standard_hours_per_day' not in users_columns:
        print("⊘ Column standard_hours_per_day does not exist in users table, skipping")
        return
    
    try:
        op.drop_column('users', 'standard_hours_per_day')
        print("✓ Dropped standard_hours_per_day column from users table")
    except Exception as e:
        error_msg = str(e)
        if 'does not exist' in error_msg.lower() or 'no such column' in error_msg.lower():
            print("⊘ Column standard_hours_per_day does not exist in users table (detected via error)")
        else:
            print(f"⚠ Warning: Could not drop standard_hours_per_day column: {e}")

