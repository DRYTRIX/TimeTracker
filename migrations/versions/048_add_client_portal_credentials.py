"""Add client portal credentials to clients table

Revision ID: 048
Revises: 047
Create Date: 2025-01-23

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '048'
down_revision = '047'
branch_labels = None
depends_on = None


def upgrade():
    """Add portal_enabled, portal_username, portal_password_hash, and portal_issues_enabled columns to clients table"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    dialect_name = bind.dialect.name if bind else 'generic'
    
    # Determine boolean default based on database dialect
    bool_true_default = '1' if dialect_name == 'sqlite' else ('true' if dialect_name == 'postgresql' else '1')
    bool_false_default = '0' if dialect_name == 'sqlite' else ('false' if dialect_name == 'postgresql' else '0')
    
    # Check existing columns (idempotent)
    existing_tables = inspector.get_table_names()
    if 'clients' not in existing_tables:
        return
    
    clients_columns = {c['name'] for c in inspector.get_columns('clients')}
    clients_indexes = [idx['name'] for idx in inspector.get_indexes('clients')]
    
    # Add portal_enabled column (idempotent)
    if 'portal_enabled' not in clients_columns:
        op.add_column('clients', 
            sa.Column('portal_enabled', sa.Boolean(), nullable=False, server_default=sa.text(bool_false_default))
        )
    
    # Add portal_username column (idempotent)
    if 'portal_username' not in clients_columns:
        op.add_column('clients',
            sa.Column('portal_username', sa.String(length=80), nullable=True)
        )
    
    # Create index for portal_username (idempotent)
    if 'ix_clients_portal_username' not in clients_indexes:
        try:
            op.create_index('ix_clients_portal_username', 'clients', ['portal_username'], unique=True)
        except:
            pass  # Index might already exist
    
    # Add portal_password_hash column (idempotent)
    if 'portal_password_hash' not in clients_columns:
        op.add_column('clients',
            sa.Column('portal_password_hash', sa.String(length=255), nullable=True)
        )
    
    # Add portal_issues_enabled column (idempotent) - default True
    if 'portal_issues_enabled' not in clients_columns:
        op.add_column('clients',
            sa.Column('portal_issues_enabled', sa.Boolean(), nullable=False, server_default=sa.text(bool_true_default))
        )


def downgrade():
    """Remove client portal columns from clients table"""
    
    # Drop columns
    try:
        op.drop_index('ix_clients_portal_username', 'clients')
    except:
        pass
    try:
        op.drop_column('clients', 'portal_issues_enabled')
    except:
        pass
    try:
        op.drop_column('clients', 'portal_password_hash')
    except:
        pass
    try:
        op.drop_column('clients', 'portal_username')
    except:
        pass
    try:
        op.drop_column('clients', 'portal_enabled')
    except:
        pass

