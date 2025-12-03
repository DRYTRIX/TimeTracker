"""Add salesman email mapping table

Revision ID: 087_salesman_email_mapping
Revises: 086_project_client_attachments
Create Date: 2025-01-29

This migration adds:
- salesman_email_mappings table for mapping salesman initials to email addresses
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '087_salesman_email_mapping'
down_revision = '086_project_client_attachments'
branch_labels = None
depends_on = None


def upgrade():
    """Create salesman_email_mappings table"""
    op.create_table('salesman_email_mappings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('salesman_initial', sa.String(length=20), nullable=False),
        sa.Column('email_address', sa.String(length=255), nullable=True),
        sa.Column('email_pattern', sa.String(length=255), nullable=True),  # e.g., '{value}@test.de'
        sa.Column('domain', sa.String(length=255), nullable=True),  # e.g., 'test.de' for pattern-based emails
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('salesman_initial', name='uq_salesman_email_mapping_initial')
    )
    op.create_index('ix_salesman_email_mappings_initial', 'salesman_email_mappings', ['salesman_initial'], unique=False)
    op.create_index('ix_salesman_email_mappings_active', 'salesman_email_mappings', ['is_active'], unique=False)


def downgrade():
    """Drop salesman_email_mappings table"""
    op.drop_index('ix_salesman_email_mappings_active', table_name='salesman_email_mappings')
    op.drop_index('ix_salesman_email_mappings_initial', table_name='salesman_email_mappings')
    op.drop_table('salesman_email_mappings')

