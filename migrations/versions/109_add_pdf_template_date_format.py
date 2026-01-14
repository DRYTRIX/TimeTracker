"""Add date_format to PDF templates

Revision ID: 109_add_pdf_template_date_format
Revises: 108_add_decorative_images
Create Date: 2025-01-30

This migration adds:
- date_format column to invoice_pdf_templates table
- date_format column to quote_pdf_templates table
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '109_add_pdf_template_date_format'
down_revision = '108_add_decorative_images'
branch_labels = None
depends_on = None


def upgrade():
    """Add date_format columns to PDF template tables"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    
    # Add date_format to invoice_pdf_templates
    if 'invoice_pdf_templates' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('invoice_pdf_templates')]
        if 'date_format' not in existing_columns:
            op.add_column('invoice_pdf_templates', 
                         sa.Column('date_format', sa.String(50), nullable=False, server_default='%d.%m.%Y'))
    
    # Add date_format to quote_pdf_templates
    if 'quote_pdf_templates' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('quote_pdf_templates')]
        if 'date_format' not in existing_columns:
            op.add_column('quote_pdf_templates', 
                         sa.Column('date_format', sa.String(50), nullable=False, server_default='%d.%m.%Y'))


def downgrade():
    """Remove date_format columns from PDF template tables"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    
    # Remove date_format from invoice_pdf_templates
    if 'invoice_pdf_templates' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('invoice_pdf_templates')]
        if 'date_format' in existing_columns:
            op.drop_column('invoice_pdf_templates', 'date_format')
    
    # Remove date_format from quote_pdf_templates
    if 'quote_pdf_templates' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('quote_pdf_templates')]
        if 'date_format' in existing_columns:
            op.drop_column('quote_pdf_templates', 'date_format')
