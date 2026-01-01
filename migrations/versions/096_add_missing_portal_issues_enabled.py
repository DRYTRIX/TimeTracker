"""Add missing portal_issues_enabled column to clients table

Revision ID: 096_add_missing_portal_issues_enabled
Revises: 095_add_missing_ui_show_issues
Create Date: 2026-01-01 08:30:00

This migration adds the missing portal_issues_enabled column that was expected by the Client model
but was not included in migration 048.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '096_add_missing_portal_issues_enabled'
down_revision = '095_add_missing_ui_show_issues'
branch_labels = None
depends_on = None


def upgrade():
    """Add missing portal_issues_enabled column to clients table"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    if 'clients' not in existing_tables:
        return
    
    clients_columns = {c['name'] for c in inspector.get_columns('clients')}
    
    if 'portal_issues_enabled' in clients_columns:
        print("✓ Column portal_issues_enabled already exists in clients table")
        return
    
    # Determine database dialect for proper default values
    dialect_name = bind.dialect.name if bind else 'generic'
    bool_true_default = '1' if dialect_name == 'sqlite' else ('true' if dialect_name == 'postgresql' else '1')
    
    try:
        op.add_column('clients', sa.Column('portal_issues_enabled', sa.Boolean(), nullable=False, server_default=sa.text(bool_true_default)))
        print("✓ Added portal_issues_enabled column to clients table")
    except Exception as e:
        error_msg = str(e)
        if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
            print("✓ Column portal_issues_enabled already exists in clients table (detected via error)")
        else:
            print(f"✗ Error adding portal_issues_enabled column: {e}")
            raise


def downgrade():
    """Remove portal_issues_enabled column from clients table"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    if 'clients' not in existing_tables:
        return
    
    clients_columns = {c['name'] for c in inspector.get_columns('clients')}
    
    if 'portal_issues_enabled' not in clients_columns:
        print("⊘ Column portal_issues_enabled does not exist in clients table, skipping")
        return
    
    try:
        op.drop_column('clients', 'portal_issues_enabled')
        print("✓ Dropped portal_issues_enabled column from clients table")
    except Exception as e:
        error_msg = str(e)
        if 'does not exist' in error_msg.lower() or 'no such column' in error_msg.lower():
            print("⊘ Column portal_issues_enabled does not exist in clients table (detected via error)")
        else:
            print(f"⚠ Warning: Could not drop portal_issues_enabled column: {e}")
