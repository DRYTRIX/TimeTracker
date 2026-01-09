"""Add template_json column for ReportLab template storage

Revision ID: 106_add_reportlab_template_json
Revises: 105_fix_client_notifications_cascade_delete
Create Date: 2026-01-08

This migration adds template_json columns to invoice_pdf_templates and quote_pdf_templates
tables to support ReportLab-based PDF template storage (new format).
Existing template_html, template_css, and design_json columns are preserved for backward compatibility.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '106_add_reportlab_template_json'
down_revision = '105_fix_client_notifications_cascade_delete'
branch_labels = None
depends_on = None


def _has_table(inspector, name: str) -> bool:
    """Check if a table exists"""
    try:
        return name in inspector.get_table_names()
    except Exception:
        return False


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    try:
        columns = {c['name'] for c in inspector.get_columns(table_name)}
        return column_name in columns
    except Exception:
        return False


def upgrade():
    """Add template_json columns to invoice_pdf_templates and quote_pdf_templates tables"""
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Add template_json to invoice_pdf_templates
    if _has_table(inspector, 'invoice_pdf_templates'):
        if not _has_column(inspector, 'invoice_pdf_templates', 'template_json'):
            op.add_column('invoice_pdf_templates', sa.Column('template_json', sa.Text(), nullable=True))
            print("Added template_json column to invoice_pdf_templates")
        else:
            print("template_json column already exists in invoice_pdf_templates")
    else:
        print("invoice_pdf_templates table does not exist, skipping")
    
    # Add template_json to quote_pdf_templates
    if _has_table(inspector, 'quote_pdf_templates'):
        if not _has_column(inspector, 'quote_pdf_templates', 'template_json'):
            op.add_column('quote_pdf_templates', sa.Column('template_json', sa.Text(), nullable=True))
            print("Added template_json column to quote_pdf_templates")
        else:
            print("template_json column already exists in quote_pdf_templates")
    else:
        print("quote_pdf_templates table does not exist, skipping")


def downgrade():
    """Remove template_json columns from invoice_pdf_templates and quote_pdf_templates tables"""
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Remove template_json from invoice_pdf_templates
    if _has_table(inspector, 'invoice_pdf_templates'):
        if _has_column(inspector, 'invoice_pdf_templates', 'template_json'):
            try:
                op.drop_column('invoice_pdf_templates', 'template_json')
            except Exception as e:
                print(f"Warning: Could not drop template_json from invoice_pdf_templates: {e}")
    
    # Remove template_json from quote_pdf_templates
    if _has_table(inspector, 'quote_pdf_templates'):
        if _has_column(inspector, 'quote_pdf_templates', 'template_json'):
            try:
                op.drop_column('quote_pdf_templates', 'template_json')
            except Exception as e:
                print(f"Warning: Could not drop template_json from quote_pdf_templates: {e}")
