"""Add invoice_pdf_templates table for storing templates by size

Revision ID: 041_add_invoice_pdf_templates
Revises: 040_import_export
Create Date: 2025-11-01

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '041_add_invoice_pdf_templates'
down_revision = '040_import_export'
branch_labels = None
depends_on = None


def upgrade():
    """Create invoice_pdf_templates table (idempotent)"""
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    if 'invoice_pdf_templates' not in existing_tables:
        op.create_table(
            'invoice_pdf_templates',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('page_size', sa.String(length=20), nullable=False),  # A4, Letter, A3, Legal, etc.
            sa.Column('template_html', sa.Text(), nullable=True),
            sa.Column('template_css', sa.Text(), nullable=True),
            sa.Column('design_json', sa.Text(), nullable=True),  # Konva.js design state
            sa.Column('is_default', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('page_size', name='uq_invoice_pdf_templates_page_size')
        )
        
        # Create indexes for better query performance
        with op.batch_alter_table('invoice_pdf_templates', schema=None) as batch_op:
            batch_op.create_index('ix_invoice_pdf_templates_page_size', ['page_size'])
            batch_op.create_index('ix_invoice_pdf_templates_is_default', ['is_default'])
        
        # Migrate existing template from Settings to invoice_pdf_templates
        # Get existing template from settings table
        result = conn.execute(sa.text("""
            SELECT invoice_pdf_template_html, invoice_pdf_template_css, invoice_pdf_design_json
            FROM settings
            LIMIT 1
        """))
        row = result.fetchone()
        
        if row:
            template_html = row[0] or ''
            template_css = row[1] or ''
            design_json = row[2] or ''
        else:
            template_html = ''
            template_css = ''
            design_json = ''
        
        # Insert A4 template (default)
        conn.execute(sa.text("""
            INSERT INTO invoice_pdf_templates (page_size, template_html, template_css, design_json, is_default)
            VALUES ('A4', :html, :css, :json, TRUE)
        """), {'html': template_html, 'css': template_css, 'json': design_json})
        
        # Create default templates for common sizes
        # Check if they exist first to avoid conflicts
        sizes = ['Letter', 'A3', 'Legal', 'A5']
        for size in sizes:
            # Check if template exists for this size
            result = conn.execute(sa.text("""
                SELECT COUNT(*) FROM invoice_pdf_templates WHERE page_size = :size
            """), {'size': size})
            count = result.fetchone()[0]
            
            if count == 0:
                conn.execute(sa.text("""
                    INSERT INTO invoice_pdf_templates (page_size, template_html, template_css, design_json, is_default)
                    VALUES (:size, '', '', '', TRUE)
                """), {'size': size})


def downgrade():
    """Drop invoice_pdf_templates table and optionally restore to Settings"""
    # Optionally migrate back to Settings before dropping
    # For now, just drop the table
    op.drop_table('invoice_pdf_templates')

