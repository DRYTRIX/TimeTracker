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
    """Add portal_enabled, portal_username, and portal_password_hash columns to clients table"""
    
    # Add portal_enabled column
    op.add_column('clients', 
        sa.Column('portal_enabled', sa.Boolean(), nullable=False, server_default='0')
    )
    
    # Add portal_username column
    op.add_column('clients',
        sa.Column('portal_username', sa.String(length=80), nullable=True)
    )
    op.create_index('ix_clients_portal_username', 'clients', ['portal_username'], unique=True)
    
    # Add portal_password_hash column
    op.add_column('clients',
        sa.Column('portal_password_hash', sa.String(length=255), nullable=True)
    )


def downgrade():
    """Remove client portal columns from clients table"""
    
    # Drop columns
    op.drop_index('ix_clients_portal_username', 'clients')
    op.drop_column('clients', 'portal_password_hash')
    op.drop_column('clients', 'portal_username')
    op.drop_column('clients', 'portal_enabled')

