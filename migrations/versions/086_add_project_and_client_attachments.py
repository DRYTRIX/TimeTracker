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
    # Create project_attachments table
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

    # Create client_attachments table
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


def downgrade():
    """Drop project_attachments and client_attachments tables"""
    op.drop_index('ix_client_attachments_uploaded_by', table_name='client_attachments')
    op.drop_index('ix_client_attachments_client_id', table_name='client_attachments')
    op.drop_table('client_attachments')
    op.drop_index('ix_project_attachments_uploaded_by', table_name='project_attachments')
    op.drop_index('ix_project_attachments_project_id', table_name='project_attachments')
    op.drop_table('project_attachments')

