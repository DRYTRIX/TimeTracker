"""Enhance Report Builder with iterative generation and email distribution

Revision ID: 090_report_builder_iteration
Revises: 089_fix_role_perm_sequences
Create Date: 2025-01-30

This migration adds:
- iterative_report_generation field to saved_report_views (enable one report per custom field value)
- email_distribution_mode field to report_email_schedules (mapping, template, or single)
- recipient_email_template field to report_email_schedules (for dynamic email generation)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '090_report_builder_iteration'
down_revision = '089_fix_role_perm_sequences'
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    try:
        return column_name in [col['name'] for col in inspector.get_columns(table_name)]
    except Exception:
        return False


def upgrade():
    """Add iterative report generation and email distribution fields"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    is_postgresql = bind.dialect.name == 'postgresql'
    
    # Fix alembic_version.version_num column size if it's too small
    # Some revision IDs are longer than the default VARCHAR(32)
    # This is needed for PostgreSQL; SQLite doesn't enforce VARCHAR lengths
    if is_postgresql and 'alembic_version' in inspector.get_table_names():
        try:
            # Try to alter the column to VARCHAR(50) to accommodate longer revision IDs
            # This is idempotent - if it's already VARCHAR(50) or larger, it will just work
            op.execute("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(50)")
        except Exception as e:
            # Column might already be the right size, or alteration might have failed
            # In either case, we'll continue - this is best-effort
            print(f"[Migration 090] ⚠ Could not expand alembic_version.version_num: {e}")
    
    # Add iterative report generation to saved_report_views
    if 'saved_report_views' in inspector.get_table_names():
        if not _has_column(inspector, 'saved_report_views', 'iterative_report_generation'):
            op.add_column('saved_report_views',
                sa.Column('iterative_report_generation', sa.Boolean(), nullable=False, server_default='false'))
        
        if not _has_column(inspector, 'saved_report_views', 'iterative_custom_field_name'):
            op.add_column('saved_report_views',
                sa.Column('iterative_custom_field_name', sa.String(length=50), nullable=True))
    
    # Add email distribution options to report_email_schedules
    if 'report_email_schedules' in inspector.get_table_names():
        if not _has_column(inspector, 'report_email_schedules', 'email_distribution_mode'):
            op.add_column('report_email_schedules',
                sa.Column('email_distribution_mode', sa.String(length=20), nullable=True))  # 'mapping', 'template', 'single'
        
        if not _has_column(inspector, 'report_email_schedules', 'recipient_email_template'):
            op.add_column('report_email_schedules',
                sa.Column('recipient_email_template', sa.String(length=255), nullable=True))  # e.g., '{value}@test.de'


def downgrade():
    """Remove iterative report generation and email distribution fields"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    if 'report_email_schedules' in inspector.get_table_names():
        if _has_column(inspector, 'report_email_schedules', 'recipient_email_template'):
            op.drop_column('report_email_schedules', 'recipient_email_template')
        if _has_column(inspector, 'report_email_schedules', 'email_distribution_mode'):
            op.drop_column('report_email_schedules', 'email_distribution_mode')
    
    if 'saved_report_views' in inspector.get_table_names():
        if _has_column(inspector, 'saved_report_views', 'iterative_custom_field_name'):
            op.drop_column('saved_report_views', 'iterative_custom_field_name')
        if _has_column(inspector, 'saved_report_views', 'iterative_report_generation'):
            op.drop_column('saved_report_views', 'iterative_report_generation')

