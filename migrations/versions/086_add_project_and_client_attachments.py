"""Add project and client attachments tables

Revision ID: 086_project_client_attachments
Revises: 085_add_project_custom_fields
Create Date: 2025-01-29

This migration adds:
- project_attachments table for file attachments to projects
- client_attachments table for file attachments to clients
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '086_project_client_attachments'
down_revision = '085_add_project_custom_fields'
branch_labels = None
depends_on = None


def upgrade():
    """Create project_attachments and client_attachments tables"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    
    # Create project_attachments table
    if 'project_attachments' in existing_tables:
        print("✓ Table project_attachments already exists")
        # Ensure indexes exist
        try:
            existing_indexes = [idx['name'] for idx in inspector.get_indexes('project_attachments')]
            for idx_name, cols in [
                ('ix_project_attachments_project_id', ['project_id']),
                ('ix_project_attachments_uploaded_by', ['uploaded_by']),
            ]:
                if idx_name not in existing_indexes:
                    try:
                        op.create_index(idx_name, 'project_attachments', cols, unique=False)
                    except Exception:
                        pass
        except Exception:
            pass
    else:
        try:
            op.create_table('project_attachments',
                sa.Column('id', sa.Integer(), nullable=False),
                sa.Column('project_id', sa.Integer(), nullable=False),
                sa.Column('filename', sa.String(length=255), nullable=False),
                sa.Column('original_filename', sa.String(length=255), nullable=False),
                sa.Column('file_path', sa.String(length=500), nullable=False),
                sa.Column('file_size', sa.Integer(), nullable=False),
                sa.Column('mime_type', sa.String(length=100), nullable=True),
                sa.Column('description', sa.Text(), nullable=True),
                sa.Column('is_visible_to_client', sa.Boolean(), nullable=False, server_default='false'),
                sa.Column('uploaded_by', sa.Integer(), nullable=False),
                sa.Column('uploaded_at', sa.DateTime(), nullable=False),
                sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
                sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ondelete='CASCADE'),
                sa.PrimaryKeyConstraint('id')
            )
            op.create_index('ix_project_attachments_project_id', 'project_attachments', ['project_id'], unique=False)
            op.create_index('ix_project_attachments_uploaded_by', 'project_attachments', ['uploaded_by'], unique=False)
            print("✓ Created project_attachments table")
        except Exception as e:
            error_msg = str(e)
            if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
                print("✓ Table project_attachments already exists (detected via error)")
            else:
                print(f"✗ Error creating project_attachments table: {e}")
                raise

    # Create client_attachments table
    if 'client_attachments' in existing_tables:
        print("✓ Table client_attachments already exists")
        # Ensure indexes exist
        try:
            existing_indexes = [idx['name'] for idx in inspector.get_indexes('client_attachments')]
            for idx_name, cols in [
                ('ix_client_attachments_client_id', ['client_id']),
                ('ix_client_attachments_uploaded_by', ['uploaded_by']),
            ]:
                if idx_name not in existing_indexes:
                    try:
                        op.create_index(idx_name, 'client_attachments', cols, unique=False)
                    except Exception:
                        pass
        except Exception:
            pass
    else:
        try:
            op.create_table('client_attachments',
                sa.Column('id', sa.Integer(), nullable=False),
                sa.Column('client_id', sa.Integer(), nullable=False),
                sa.Column('filename', sa.String(length=255), nullable=False),
                sa.Column('original_filename', sa.String(length=255), nullable=False),
                sa.Column('file_path', sa.String(length=500), nullable=False),
                sa.Column('file_size', sa.Integer(), nullable=False),
                sa.Column('mime_type', sa.String(length=100), nullable=True),
                sa.Column('description', sa.Text(), nullable=True),
                sa.Column('is_visible_to_client', sa.Boolean(), nullable=False, server_default='false'),
                sa.Column('uploaded_by', sa.Integer(), nullable=False),
                sa.Column('uploaded_at', sa.DateTime(), nullable=False),
                sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
                sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ondelete='CASCADE'),
                sa.PrimaryKeyConstraint('id')
            )
            op.create_index('ix_client_attachments_client_id', 'client_attachments', ['client_id'], unique=False)
            op.create_index('ix_client_attachments_uploaded_by', 'client_attachments', ['uploaded_by'], unique=False)
            print("✓ Created client_attachments table")
        except Exception as e:
            error_msg = str(e)
            if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
                print("✓ Table client_attachments already exists (detected via error)")
            else:
                print(f"✗ Error creating client_attachments table: {e}")
                raise


def downgrade():
    """Drop project_attachments and client_attachments tables"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    
    if 'client_attachments' in existing_tables:
        try:
            existing_indexes = [idx['name'] for idx in inspector.get_indexes('client_attachments')]
            for idx_name in ['ix_client_attachments_uploaded_by', 'ix_client_attachments_client_id']:
                if idx_name in existing_indexes:
                    try:
                        op.drop_index(idx_name, table_name='client_attachments')
                    except Exception:
                        pass
            op.drop_table('client_attachments')
            print("✓ Dropped client_attachments table")
        except Exception as e:
            error_msg = str(e)
            if 'does not exist' in error_msg.lower() or 'no such table' in error_msg.lower():
                print("⊘ Table client_attachments does not exist (detected via error)")
            else:
                print(f"⚠ Warning: Could not drop client_attachments table: {e}")
    
    if 'project_attachments' in existing_tables:
        try:
            existing_indexes = [idx['name'] for idx in inspector.get_indexes('project_attachments')]
            for idx_name in ['ix_project_attachments_uploaded_by', 'ix_project_attachments_project_id']:
                if idx_name in existing_indexes:
                    try:
                        op.drop_index(idx_name, table_name='project_attachments')
                    except Exception:
                        pass
            op.drop_table('project_attachments')
            print("✓ Dropped project_attachments table")
        except Exception as e:
            error_msg = str(e)
            if 'does not exist' in error_msg.lower() or 'no such table' in error_msg.lower():
                print("⊘ Table project_attachments does not exist (detected via error)")
            else:
                print(f"⚠ Warning: Could not drop project_attachments table: {e}")

