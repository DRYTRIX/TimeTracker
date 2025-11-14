"""Add client portal fields to users table

Revision ID: 047
Revises: 046
Create Date: 2025-01-23

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '047'
down_revision = '046'
branch_labels = None
depends_on = None


def upgrade():
    """Add client_portal_enabled and client_id columns to users table"""
    
    # Add client_portal_enabled column
    op.add_column('users', 
        sa.Column('client_portal_enabled', sa.Boolean(), nullable=False, server_default='0')
    )
    
    # Add client_id column with foreign key
    op.add_column('users',
        sa.Column('client_id', sa.Integer(), nullable=True)
    )
    op.create_index('ix_users_client_id', 'users', ['client_id'])
    op.create_foreign_key(
        'fk_users_client_id',
        'users', 'clients',
        ['client_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade():
    """Remove client_portal_enabled and client_id columns from users table"""
    
    # Drop foreign key and index
    op.drop_constraint('fk_users_client_id', 'users', type_='foreignkey')
    op.drop_index('ix_users_client_id', 'users')
    
    # Drop columns
    op.drop_column('users', 'client_id')
    op.drop_column('users', 'client_portal_enabled')

