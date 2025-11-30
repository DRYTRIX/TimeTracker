"""Add custom field definitions table for global custom field management

Revision ID: 084_custom_field_definitions
Revises: 083_add_paid_status_time_entries
Create Date: 2025-01-27

This migration adds:
- custom_field_definitions table for storing global custom field definitions
- Fields include: field_key, label, description, is_mandatory, is_active, order
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '084_custom_field_definitions'
down_revision = '083_add_paid_status_time_entries'
branch_labels = None
depends_on = None


def upgrade():
    """Create custom_field_definitions table"""
    op.create_table(
        'custom_field_definitions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('field_key', sa.String(length=100), nullable=False),
        sa.Column('label', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_mandatory', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('field_key')
    )
    op.create_index('idx_custom_field_definitions_field_key', 'custom_field_definitions', ['field_key'])
    op.create_index('idx_custom_field_definitions_is_active', 'custom_field_definitions', ['is_active'])


def downgrade():
    """Drop custom_field_definitions table"""
    op.drop_index('idx_custom_field_definitions_is_active', table_name='custom_field_definitions')
    op.drop_index('idx_custom_field_definitions_field_key', table_name='custom_field_definitions')
    op.drop_table('custom_field_definitions')
