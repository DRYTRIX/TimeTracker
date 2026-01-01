"""Add missing ui_show_issues column to users table

Revision ID: 095_add_missing_ui_show_issues
Revises: 094_add_donation_interactions
Create Date: 2025-12-31 14:25:00

This migration adds the missing ui_show_issues column that was expected by the User model
but was not included in migration 077.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '095_add_missing_ui_show_issues'
down_revision = '094_add_donation_interactions'
branch_labels = None
depends_on = None


def upgrade():
    """Add missing ui_show_issues column to users table"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    if 'users' not in existing_tables:
        return
    
    users_columns = {c['name'] for c in inspector.get_columns('users')}
    
    if 'ui_show_issues' in users_columns:
        print("✓ Column ui_show_issues already exists in users table")
        return
    
    # Determine database dialect for proper default values
    dialect_name = bind.dialect.name if bind else 'generic'
    bool_true_default = '1' if dialect_name == 'sqlite' else ('true' if dialect_name == 'postgresql' else '1')
    
    try:
        op.add_column('users', sa.Column('ui_show_issues', sa.Boolean(), nullable=False, server_default=sa.text(bool_true_default)))
        print("✓ Added ui_show_issues column to users table")
    except Exception as e:
        error_msg = str(e)
        if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
            print("✓ Column ui_show_issues already exists in users table (detected via error)")
        else:
            print(f"✗ Error adding ui_show_issues column: {e}")
            raise


def downgrade():
    """Remove ui_show_issues column from users table"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    if 'users' not in existing_tables:
        return
    
    users_columns = {c['name'] for c in inspector.get_columns('users')}
    
    if 'ui_show_issues' not in users_columns:
        print("⊘ Column ui_show_issues does not exist in users table, skipping")
        return
    
    try:
        op.drop_column('users', 'ui_show_issues')
        print("✓ Dropped ui_show_issues column from users table")
    except Exception as e:
        error_msg = str(e)
        if 'does not exist' in error_msg.lower() or 'no such column' in error_msg.lower():
            print("⊘ Column ui_show_issues does not exist in users table (detected via error)")
        else:
            print(f"⚠ Warning: Could not drop ui_show_issues column: {e}")
