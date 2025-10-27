"""Add API tokens table for REST API authentication

Revision ID: 032_add_api_tokens
Revises: 031
Create Date: 2025-10-27 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '032_add_api_tokens'
down_revision = '031'
branch_labels = None
depends_on = None


def upgrade():
    # Create api_tokens table
    op.create_table('api_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('token_hash', sa.String(length=128), nullable=False),
        sa.Column('token_prefix', sa.String(length=10), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('scopes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('ip_whitelist', sa.Text(), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash')
    )
    
    # Create index on token_hash for fast lookups
    op.create_index(op.f('ix_api_tokens_token_hash'), 'api_tokens', ['token_hash'], unique=True)
    
    # Create index on user_id for fast user lookups
    op.create_index(op.f('ix_api_tokens_user_id'), 'api_tokens', ['user_id'], unique=False)


def downgrade():
    # Drop indexes
    op.drop_index(op.f('ix_api_tokens_user_id'), table_name='api_tokens')
    op.drop_index(op.f('ix_api_tokens_token_hash'), table_name='api_tokens')
    
    # Drop table
    op.drop_table('api_tokens')

