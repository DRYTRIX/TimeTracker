"""Add custom fields to clients and link templates

Revision ID: 075_custom_fields_link_templates
Revises: 074_password_change_required
Create Date: 2025-01-27

This migration adds:
- custom_fields JSON column to clients table for flexible custom data storage
- link_templates table for storing URL templates that can use custom field values
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '075_custom_fields_link_templates'
down_revision = '074_password_change_required'
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    try:
        return column_name in [col['name'] for col in inspector.get_columns(table_name)]
    except Exception:
        return False


def upgrade():
    """Add custom_fields to clients and create link_templates table"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    dialect_name = bind.dialect.name if bind else "generic"
    bool_true_default = '1' if dialect_name == 'sqlite' else ('true' if dialect_name == 'postgresql' else '1')

    # Add custom_fields column to clients table if it doesn't exist
    if 'clients' in inspector.get_table_names():
        if not _has_column(inspector, 'clients', 'custom_fields'):
            # Use portable JSON type for cross-db compatibility (SQLite + PostgreSQL).
            op.add_column('clients', sa.Column('custom_fields', sa.JSON(), nullable=True))

    # Create link_templates table
    op.create_table(
        'link_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('url_template', sa.String(length=1000), nullable=False),
        sa.Column('icon', sa.String(length=50), nullable=True),
        sa.Column('field_key', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text(bool_true_default)),
        sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_link_templates_is_active', 'link_templates', ['is_active'])
    op.create_index('idx_link_templates_field_key', 'link_templates', ['field_key'])


def downgrade():
    """Remove custom_fields and link_templates table"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Drop link_templates table
    if 'link_templates' in inspector.get_table_names():
        op.drop_index('idx_link_templates_field_key', table_name='link_templates')
        op.drop_index('idx_link_templates_is_active', table_name='link_templates')
        op.drop_table('link_templates')

    # Remove custom_fields column from clients table
    if 'clients' in inspector.get_table_names():
        if _has_column(inspector, 'clients', 'custom_fields'):
            op.drop_column('clients', 'custom_fields')

