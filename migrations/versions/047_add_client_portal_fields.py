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
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    is_sqlite = conn.dialect.name == 'sqlite'
    existing_tables = inspector.get_table_names()
    
    if 'users' not in existing_tables:
        return
    
    users_columns = [col['name'] for col in inspector.get_columns('users')]
    users_indexes = [idx['name'] for idx in inspector.get_indexes('users')]
    users_fks = [fk['name'] for fk in inspector.get_foreign_keys('users')]
    
    # Add client_portal_enabled column (idempotent)
    if 'client_portal_enabled' not in users_columns:
        op.add_column('users', 
            sa.Column('client_portal_enabled', sa.Boolean(), nullable=False, server_default='0')
        )
    
    # Add client_id column with foreign key (idempotent)
    if 'client_id' not in users_columns:
        op.add_column('users',
            sa.Column('client_id', sa.Integer(), nullable=True)
        )
    
    if 'client_id' in users_columns:
        if 'ix_users_client_id' not in users_indexes:
            op.create_index('ix_users_client_id', 'users', ['client_id'])
        
        if 'fk_users_client_id' not in users_fks:
            if is_sqlite:
                with op.batch_alter_table('users', schema=None) as batch_op:
                    batch_op.create_foreign_key('fk_users_client_id', 'clients', ['client_id'], ['id'])
            else:
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

