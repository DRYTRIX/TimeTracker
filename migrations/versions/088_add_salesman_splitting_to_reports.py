"""Add salesman splitting to report email schedules

Revision ID: 088_salesman_splitting_reports
Revises: 087_salesman_email_mapping
Create Date: 2025-01-29

This migration adds:
- split_by_salesman field to report_email_schedules table
- salesman_field_name field to specify which custom field to use
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '088_salesman_splitting_reports'
down_revision = '087_salesman_email_mapping'
branch_labels = None
depends_on = None


def upgrade():
    """Add salesman splitting fields to report_email_schedules"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    # Check existing columns (idempotent)
    existing_tables = inspector.get_table_names()
    if 'report_email_schedules' not in existing_tables:
        return
    
    columns = {c['name'] for c in inspector.get_columns('report_email_schedules')}
    
    # Helper function to add column if it doesn't exist
    def _add_column_if_missing(column_name, column_def, description=""):
        if column_name in columns:
            print(f"✓ Column {column_name} already exists in report_email_schedules table")
            return
        try:
            op.add_column('report_email_schedules', column_def)
            print(f"✓ Added {column_name} column to report_email_schedules table{(' - ' + description) if description else ''}")
        except Exception as e:
            error_msg = str(e)
            if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
                print(f"✓ Column {column_name} already exists in report_email_schedules table (detected via error)")
            else:
                print(f"⚠ Warning adding {column_name} column: {e}")
                raise
    
    # Add split_by_salesman field
    _add_column_if_missing('split_by_salesman',
        sa.Column('split_by_salesman', sa.Boolean(), nullable=False, server_default='false'),
        'Enable splitting reports by salesman')
    
    # Add salesman_field_name field (defaults to 'salesman')
    _add_column_if_missing('salesman_field_name',
        sa.Column('salesman_field_name', sa.String(length=50), nullable=True),
        'Custom field name to use for salesman splitting')


def downgrade():
    """Remove salesman splitting fields"""
    op.drop_column('report_email_schedules', 'salesman_field_name')
    op.drop_column('report_email_schedules', 'split_by_salesman')

