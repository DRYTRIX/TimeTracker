"""Rename offers to quotes and add line items, PDF templates, and client portal visibility

Revision ID: 051
Revises: 050
Create Date: 2025-11-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '051'
down_revision = '050'
branch_labels = None
depends_on = None


def upgrade():
    """Rename offers to quotes and add new features"""
    
    # Drop indexes on offers table before renaming
    op.drop_index('ix_offers_offer_number', 'offers')
    op.drop_index('ix_offers_client_id', 'offers')
    op.drop_index('ix_offers_project_id', 'offers')
    op.drop_index('ix_offers_status', 'offers')
    
    # Rename offers table to quotes
    op.rename_table('offers', 'quotes')
    
    # Rename columns in quotes table
    op.alter_column('quotes', 'offer_number', new_column_name='quote_number', existing_type=sa.String(length=50), existing_nullable=False)
    
    # Add new columns to quotes table
    op.add_column('quotes',
        sa.Column('subtotal', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0')
    )
    op.add_column('quotes',
        sa.Column('tax_amount', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0')
    )
    op.add_column('quotes',
        sa.Column('visible_to_client', sa.Boolean(), nullable=False, server_default='false')
    )
    op.add_column('quotes',
        sa.Column('template_id', sa.Integer(), nullable=True)
    )
    
    # Create quote_items table
    op.create_table('quote_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('quote_id', sa.Integer(), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=10, scale=2), nullable=False, server_default='1'),
        sa.Column('unit_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('total_amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('unit', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['quote_id'], ['quotes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_quote_items_quote_id', 'quote_items', ['quote_id'])
    
    # Create quote_pdf_templates table
    op.create_table('quote_pdf_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('page_size', sa.String(length=20), nullable=False),
        sa.Column('template_html', sa.Text(), nullable=True),
        sa.Column('template_css', sa.Text(), nullable=True),
        sa.Column('design_json', sa.Text(), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('page_size')
    )
    
    # Recreate indexes in quotes table with new names
    op.create_index('ix_quotes_quote_number', 'quotes', ['quote_number'], unique=True)
    op.create_index('ix_quotes_client_id', 'quotes', ['client_id'])
    op.create_index('ix_quotes_project_id', 'quotes', ['project_id'])
    op.create_index('ix_quotes_status', 'quotes', ['status'])
    op.create_index('ix_quotes_template_id', 'quotes', ['template_id'])
    
    # Update foreign key constraints
    op.drop_constraint('offers_client_id_fkey', 'quotes', type_='foreignkey')
    op.create_foreign_key('fk_quotes_client_id', 'quotes', 'clients', ['client_id'], ['id'], ondelete='CASCADE')
    
    op.drop_constraint('offers_project_id_fkey', 'quotes', type_='foreignkey')
    op.create_foreign_key('fk_quotes_project_id', 'quotes', 'projects', ['project_id'], ['id'], ondelete='SET NULL')
    
    op.drop_constraint('offers_created_by_fkey', 'quotes', type_='foreignkey')
    op.create_foreign_key('fk_quotes_created_by', 'quotes', 'users', ['created_by'], ['id'], ondelete='CASCADE')
    
    op.drop_constraint('offers_accepted_by_fkey', 'quotes', type_='foreignkey')
    op.create_foreign_key('fk_quotes_accepted_by', 'quotes', 'users', ['accepted_by'], ['id'], ondelete='SET NULL')
    
    # Add foreign key for template_id
    op.create_foreign_key('fk_quotes_template_id', 'quotes', 'quote_pdf_templates', ['template_id'], ['id'], ondelete='SET NULL')
    
    # Update projects table - rename offer_id to quote_id
    op.alter_column('projects', 'offer_id', new_column_name='quote_id', existing_type=sa.Integer(), existing_nullable=True)
    op.drop_index('ix_projects_offer_id', 'projects')
    op.create_index('ix_projects_quote_id', 'projects', ['quote_id'])
    op.drop_constraint('fk_projects_offer_id', 'projects', type_='foreignkey')
    op.create_foreign_key('fk_projects_quote_id', 'projects', 'quotes', ['quote_id'], ['id'], ondelete='SET NULL')
    
    # Update invoices table - rename offer_id to quote_id
    op.alter_column('invoices', 'offer_id', new_column_name='quote_id', existing_type=sa.Integer(), existing_nullable=True)
    op.drop_index('ix_invoices_offer_id', 'invoices')
    op.create_index('ix_invoices_quote_id', 'invoices', ['quote_id'])
    op.drop_constraint('fk_invoices_offer_id', 'invoices', type_='foreignkey')
    op.create_foreign_key('fk_invoices_quote_id', 'invoices', 'quotes', ['quote_id'], ['id'], ondelete='SET NULL')


def downgrade():
    """Revert changes - rename quotes back to offers"""
    
    # Remove foreign keys
    op.drop_constraint('fk_invoices_quote_id', 'invoices', type_='foreignkey')
    op.drop_index('ix_invoices_quote_id', 'invoices')
    op.alter_column('invoices', 'quote_id', new_column_name='offer_id', existing_type=sa.Integer(), existing_nullable=True)
    op.create_index('ix_invoices_offer_id', 'invoices', ['offer_id'])
    op.create_foreign_key('fk_invoices_offer_id', 'invoices', 'offers', ['offer_id'], ['id'], ondelete='SET NULL')
    
    op.drop_constraint('fk_projects_quote_id', 'projects', type_='foreignkey')
    op.drop_index('ix_projects_quote_id', 'projects')
    op.alter_column('projects', 'quote_id', new_column_name='offer_id', existing_type=sa.Integer(), existing_nullable=True)
    op.create_index('ix_projects_offer_id', 'projects', ['offer_id'])
    op.create_foreign_key('fk_projects_offer_id', 'projects', 'offers', ['offer_id'], ['id'], ondelete='SET NULL')
    
    # Drop quote_pdf_templates table
    op.drop_table('quote_pdf_templates')
    
    # Drop quote_items table
    op.drop_index('ix_quote_items_quote_id', 'quote_items')
    op.drop_table('quote_items')
    
    # Remove new columns from quotes
    op.drop_column('quotes', 'template_id')
    op.drop_column('quotes', 'visible_to_client')
    op.drop_column('quotes', 'tax_amount')
    op.drop_column('quotes', 'subtotal')
    
    # Rename columns back
    op.alter_column('quotes', 'quote_number', new_column_name='offer_number', existing_type=sa.String(length=50), existing_nullable=False)
    
    # Rename table back
    op.rename_table('quotes', 'offers')
    
    # Restore indexes
    op.drop_index('ix_quotes_template_id', 'offers')
    op.drop_index('ix_quotes_status', 'offers')
    op.create_index('ix_offers_status', 'offers', ['status'])
    op.drop_index('ix_quotes_project_id', 'offers')
    op.create_index('ix_offers_project_id', 'offers', ['project_id'])
    op.drop_index('ix_quotes_client_id', 'offers')
    op.create_index('ix_offers_client_id', 'offers', ['client_id'])
    op.drop_index('ix_quotes_quote_number', 'offers')
    op.create_index('ix_offers_offer_number', 'offers', ['offer_number'], unique=True)
    
    # Restore foreign keys
    op.drop_constraint('fk_quotes_accepted_by', 'offers', type_='foreignkey')
    op.create_foreign_key('offers_accepted_by_fkey', 'offers', 'users', ['accepted_by'], ['id'], ondelete='SET NULL')
    
    op.drop_constraint('fk_quotes_created_by', 'offers', type_='foreignkey')
    op.create_foreign_key('offers_created_by_fkey', 'offers', 'users', ['created_by'], ['id'], ondelete='CASCADE')
    
    op.drop_constraint('fk_quotes_project_id', 'offers', type_='foreignkey')
    op.create_foreign_key('offers_project_id_fkey', 'offers', 'projects', ['project_id'], ['id'], ondelete='SET NULL')
    
    op.drop_constraint('fk_quotes_client_id', 'offers', type_='foreignkey')
    op.create_foreign_key('offers_client_id_fkey', 'offers', 'clients', ['client_id'], ['id'], ondelete='CASCADE')

