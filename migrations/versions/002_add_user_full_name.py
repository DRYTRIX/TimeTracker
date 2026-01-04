"""Add full_name to users

Revision ID: 002
Revises: 001
Create Date: 2025-01-15 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    """Add full_name column to users table"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    if 'users' not in existing_tables:
        return
    
    users_columns = {c['name'] for c in inspector.get_columns('users')}
    
    if 'full_name' in users_columns:
        print("✓ Column full_name already exists in users table")
        return
    
    try:
        op.add_column('users', sa.Column('full_name', sa.String(length=200), nullable=True))
        print("✓ Added full_name column to users table")
    except Exception as e:
        error_msg = str(e)
        if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
            print("✓ Column full_name already exists in users table (detected via error)")
        else:
            print(f"✗ Error adding full_name column: {e}")
            raise


def downgrade():
    """Remove full_name column from users table"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    if 'users' not in existing_tables:
        return
    
    users_columns = {c['name'] for c in inspector.get_columns('users')}
    
    if 'full_name' not in users_columns:
        print("⊘ Column full_name does not exist in users table, skipping")
        return
    
    try:
        op.drop_column('users', 'full_name')
        print("✓ Dropped full_name column from users table")
    except Exception as e:
        error_msg = str(e)
        if 'does not exist' in error_msg.lower() or 'no such column' in error_msg.lower():
            print("⊘ Column full_name does not exist in users table (detected via error)")
        else:
            print(f"⚠ Warning: Could not drop full_name column: {e}")


