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
    # Add split_by_salesman field
    op.add_column('report_email_schedules', 
        sa.Column('split_by_salesman', sa.Boolean(), nullable=False, server_default='false'))
    
    # Add salesman_field_name field (defaults to 'salesman')
    op.add_column('report_email_schedules',
        sa.Column('salesman_field_name', sa.String(length=50), nullable=True))


def downgrade():
    """Remove salesman splitting fields"""
    op.drop_column('report_email_schedules', 'salesman_field_name')
    op.drop_column('report_email_schedules', 'split_by_salesman')

