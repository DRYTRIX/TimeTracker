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
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    if 'clients' not in existing_tables:
        return
    
    clients_columns = {c['name'] for c in inspector.get_columns('clients')}
    
    # Add password_setup_token column
    if 'password_setup_token' not in clients_columns:
        try:
            op.add_column('clients',
                sa.Column('password_setup_token', sa.String(length=100), nullable=True)
            )
            print("✓ Added password_setup_token column to clients table")
        except Exception as e:
            error_msg = str(e)
            if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
                print("✓ Column password_setup_token already exists in clients table (detected via error)")
            else:
                print(f"✗ Error adding password_setup_token column: {e}")
                raise
    else:
        print("✓ Column password_setup_token already exists in clients table")
    
    # Create index if it doesn't exist
    try:
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('clients')]
        if 'ix_clients_password_setup_token' not in existing_indexes:
            op.create_index('ix_clients_password_setup_token', 'clients', ['password_setup_token'])
    except Exception as e:
        error_msg = str(e)
        if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
            pass  # Index already exists
        else:
            print(f"⚠ Warning: Could not create index: {e}")
    
    # Add password_setup_token_expires column
    if 'password_setup_token_expires' not in clients_columns:
        try:
            op.add_column('clients',
                sa.Column('password_setup_token_expires', sa.DateTime(), nullable=True)
            )
            print("✓ Added password_setup_token_expires column to clients table")
        except Exception as e:
            error_msg = str(e)
            if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
                print("✓ Column password_setup_token_expires already exists in clients table (detected via error)")
            else:
                print(f"✗ Error adding password_setup_token_expires column: {e}")
                raise
    else:
        print("✓ Column password_setup_token_expires already exists in clients table")


def downgrade():
    """Remove password setup token columns from clients table"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    if 'clients' not in existing_tables:
        return
    
    clients_columns = {c['name'] for c in inspector.get_columns('clients')}
    
    # Drop index
    try:
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('clients')]
        if 'ix_clients_password_setup_token' in existing_indexes:
            op.drop_index('ix_clients_password_setup_token', 'clients')
    except Exception as e:
        error_msg = str(e)
        if 'does not exist' in error_msg.lower():
            pass  # Index doesn't exist
        else:
            print(f"⚠ Warning: Could not drop index: {e}")
    
    # Drop columns
    if 'password_setup_token_expires' in clients_columns:
        try:
            op.drop_column('clients', 'password_setup_token_expires')
            print("✓ Dropped password_setup_token_expires column from clients table")
        except Exception as e:
            error_msg = str(e)
            if 'does not exist' in error_msg.lower() or 'no such column' in error_msg.lower():
                print("⊘ Column password_setup_token_expires does not exist in clients table (detected via error)")
            else:
                print(f"⚠ Warning: Could not drop password_setup_token_expires column: {e}")
    
    if 'password_setup_token' in clients_columns:
        try:
            op.drop_column('clients', 'password_setup_token')
            print("✓ Dropped password_setup_token column from clients table")
        except Exception as e:
            error_msg = str(e)
            if 'does not exist' in error_msg.lower() or 'no such column' in error_msg.lower():
                print("⊘ Column password_setup_token does not exist in clients table (detected via error)")
            else:
                print(f"⚠ Warning: Could not drop password_setup_token column: {e}")

