"""Add custom fields to projects

Revision ID: 085_add_project_custom_fields
Revises: 084_add_custom_field_definitions
Create Date: 2025-01-28

This migration adds:
- custom_fields JSON column to projects table for flexible custom data storage
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '085_add_project_custom_fields'
down_revision = '084_custom_field_definitions'
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    try:
        return column_name in [col['name'] for col in inspector.get_columns(table_name)]
    except Exception:
        return False


def upgrade():
    """Add custom_fields to projects table"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Add custom_fields column to projects table if it doesn't exist
    if 'projects' in inspector.get_table_names():
        if not _has_column(inspector, 'projects', 'custom_fields'):
            # Use JSONB for PostgreSQL, JSON for SQLite
            try:
                op.add_column('projects', sa.Column('custom_fields', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
            except Exception:
                # Fallback to JSON for SQLite
                op.add_column('projects', sa.Column('custom_fields', sa.JSON(), nullable=True))


def downgrade():
    """Remove custom_fields from projects table"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Remove custom_fields column from projects table
    if 'projects' in inspector.get_table_names():
        if _has_column(inspector, 'projects', 'custom_fields'):
            op.drop_column('projects', 'custom_fields')

