"""Add password setup token fields to clients table

Revision ID: 049
Revises: 048
Create Date: 2025-01-23

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '049'
down_revision = '048'
branch_labels = None
depends_on = None


def upgrade():
    """Add password_setup_token and password_setup_token_expires columns to clients table"""
    
    # Add password_setup_token column
    op.add_column('clients',
        sa.Column('password_setup_token', sa.String(length=100), nullable=True)
    )
    op.create_index('ix_clients_password_setup_token', 'clients', ['password_setup_token'])
    
    # Add password_setup_token_expires column
    op.add_column('clients',
        sa.Column('password_setup_token_expires', sa.DateTime(), nullable=True)
    )


def downgrade():
    """Remove password setup token columns from clients table"""
    
    # Drop columns
    op.drop_index('ix_clients_password_setup_token', 'clients')
    op.drop_column('clients', 'password_setup_token_expires')
    op.drop_column('clients', 'password_setup_token')

