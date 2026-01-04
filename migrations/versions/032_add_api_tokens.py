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
    """Create api_tokens table"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    
    if 'api_tokens' in existing_tables:
        print("✓ Table api_tokens already exists")
        # Ensure indexes exist
        try:
            existing_indexes = [idx['name'] for idx in inspector.get_indexes('api_tokens')]
            if op.f('ix_api_tokens_token_hash') not in existing_indexes:
                op.create_index(op.f('ix_api_tokens_token_hash'), 'api_tokens', ['token_hash'], unique=True)
            if op.f('ix_api_tokens_user_id') not in existing_indexes:
                op.create_index(op.f('ix_api_tokens_user_id'), 'api_tokens', ['user_id'], unique=False)
        except Exception:
            pass
        return
    
    try:
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
        print("✓ Created api_tokens table")
    except Exception as e:
        error_msg = str(e)
        if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
            print("✓ Table api_tokens already exists (detected via error)")
        else:
            print(f"✗ Error creating api_tokens table: {e}")
            raise


def downgrade():
    """Drop api_tokens table"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    
    if 'api_tokens' not in existing_tables:
        print("⊘ Table api_tokens does not exist, skipping")
        return
    
    try:
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('api_tokens')]
        if op.f('ix_api_tokens_user_id') in existing_indexes:
            op.drop_index(op.f('ix_api_tokens_user_id'), table_name='api_tokens')
        if op.f('ix_api_tokens_token_hash') in existing_indexes:
            op.drop_index(op.f('ix_api_tokens_token_hash'), table_name='api_tokens')
        op.drop_table('api_tokens')
        print("✓ Dropped api_tokens table")
    except Exception as e:
        error_msg = str(e)
        if 'does not exist' in error_msg.lower() or 'no such table' in error_msg.lower():
            print("⊘ Table api_tokens does not exist (detected via error)")
        else:
            print(f"⚠ Warning: Could not drop api_tokens table: {e}")

