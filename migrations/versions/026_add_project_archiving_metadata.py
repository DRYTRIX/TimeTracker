"""Add project archiving metadata fields

Revision ID: 026
Revises: 025
Create Date: 2025-10-24 00:00:00

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '026'
down_revision = '025'
branch_labels = None
depends_on = None


def upgrade():
    """Add archived_at, archived_by, and archived_reason columns to projects table"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()
    
    if 'projects' not in existing_tables:
        return
    
    projects_columns = [col['name'] for col in inspector.get_columns('projects')]
    projects_indexes = [idx['name'] for idx in inspector.get_indexes('projects')]
    projects_fks = [fk['name'] for fk in inspector.get_foreign_keys('projects')]
    
    try:
        with op.batch_alter_table('projects', schema=None) as batch_op:
            # Add archived_at timestamp field (idempotent)
            if 'archived_at' not in projects_columns:
                batch_op.add_column(sa.Column('archived_at', sa.DateTime(), nullable=True))
            
            # Add archived_by user reference (who archived the project) (idempotent)
            if 'archived_by' not in projects_columns:
                batch_op.add_column(sa.Column('archived_by', sa.Integer(), nullable=True))
            
            # Add archived_reason text field (why the project was archived) (idempotent)
            if 'archived_reason' not in projects_columns:
                batch_op.add_column(sa.Column('archived_reason', sa.Text(), nullable=True))
            
            # Create foreign key for archived_by (idempotent)
            if 'archived_by' in projects_columns and 'fk_projects_archived_by_users' not in projects_fks:
                try:
                    batch_op.create_foreign_key(
                        'fk_projects_archived_by_users',
                        'users',
                        ['archived_by'],
                        ['id']
                    )
                except Exception as e:
                    print(f"⚠ Warning creating foreign key for archived_by: {e}")
            
            # Create index on archived_at for faster filtering (idempotent)
            if 'archived_at' in projects_columns and 'ix_projects_archived_at' not in projects_indexes:
                try:
                    batch_op.create_index('ix_projects_archived_at', ['archived_at'])
                except Exception as e:
                    print(f"⚠ Warning creating index on archived_at: {e}")
        
        print("✓ Added project archiving metadata fields")
        
    except Exception as e:
        print(f"⚠ Warning adding archiving metadata fields: {e}")


def downgrade():
    """Remove archived_at, archived_by, and archived_reason columns from projects table"""
    try:
        with op.batch_alter_table('projects', schema=None) as batch_op:
            # Drop index
            try:
                batch_op.drop_index('ix_projects_archived_at')
            except Exception:
                pass
            
            # Drop foreign key
            try:
                batch_op.drop_constraint('fk_projects_archived_by_users', type_='foreignkey')
            except Exception:
                pass
            
            # Drop columns
            try:
                batch_op.drop_column('archived_reason')
            except Exception:
                pass
            
            try:
                batch_op.drop_column('archived_by')
            except Exception:
                pass
            
            try:
                batch_op.drop_column('archived_at')
            except Exception:
                pass
        
        print("✓ Removed project archiving metadata fields")
        
    except Exception as e:
        print(f"⚠ Warning removing archiving metadata fields: {e}")

