"""Add global integrations support

Revision ID: 082_add_global_integrations
Revises: 081_add_int_oauth_creds
Create Date: 2025-01-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '082_add_global_integrations'
down_revision = '081_add_int_oauth_creds'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('integrations', schema=None) as batch_op:
        # Add is_global flag
        batch_op.add_column(sa.Column('is_global', sa.Boolean(), nullable=False, server_default='0'))
        
        # Make user_id nullable for global integrations
        batch_op.alter_column('user_id',
                              existing_type=sa.Integer(),
                              nullable=True)
        
        # Add index for global integrations
        batch_op.create_index('ix_integrations_is_global', ['is_global'], unique=False)
        
        # Note: Unique constraint for global integrations enforced at application level
        # (one global integration per provider) since SQLite doesn't support partial indexes


def downgrade():
    with op.batch_alter_table('integrations', schema=None) as batch_op:
        # Remove index
        batch_op.drop_index('ix_integrations_is_global')
        
        # Make user_id required again (set to first user for existing records)
        # First, set user_id for any null values
        op.execute("UPDATE integrations SET user_id = (SELECT id FROM users LIMIT 1) WHERE user_id IS NULL")
        
        batch_op.alter_column('user_id',
                              existing_type=sa.Integer(),
                              nullable=False)
        
        # Remove is_global column
        batch_op.drop_column('is_global')

