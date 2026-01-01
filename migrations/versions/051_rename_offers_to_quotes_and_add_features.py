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
    
    conn = op.get_bind()
    is_sqlite = conn.dialect.name == 'sqlite'
    from sqlalchemy import inspect
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Only proceed if offers table exists
    if 'offers' not in existing_tables and 'quotes' in existing_tables:
        # Already migrated, skip
        return
    
    if 'offers' in existing_tables:
        # Drop indexes on offers table before renaming
        try:
            op.drop_index('ix_offers_offer_number', 'offers')
        except:
            pass
        try:
            op.drop_index('ix_offers_client_id', 'offers')
        except:
            pass
        try:
            op.drop_index('ix_offers_project_id', 'offers')
        except:
            pass
        try:
            op.drop_index('ix_offers_status', 'offers')
        except:
            pass
        
        # Rename offers table to quotes
        op.rename_table('offers', 'quotes')
    
    # Rename columns in quotes table
    if 'quotes' in existing_tables:
        quotes_columns = [col['name'] for col in inspector.get_columns('quotes')]
        
        if 'offer_number' in quotes_columns and 'quote_number' not in quotes_columns:
            if is_sqlite:
                with op.batch_alter_table('quotes', schema=None) as batch_op:
                    batch_op.alter_column('offer_number', new_column_name='quote_number')
            else:
                op.alter_column('quotes', 'offer_number', new_column_name='quote_number', existing_type=sa.String(length=50), existing_nullable=False)
            # Refresh inspector after column rename
            inspector = inspect(conn)
            quotes_columns = [col['name'] for col in inspector.get_columns('quotes')]
        
        # Add new columns to quotes table (idempotent)
        if 'subtotal' not in quotes_columns:
            op.add_column('quotes',
                sa.Column('subtotal', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0')
            )
        if 'tax_amount' not in quotes_columns:
            op.add_column('quotes',
                sa.Column('tax_amount', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0')
            )
        if 'visible_to_client' not in quotes_columns:
            op.add_column('quotes',
                sa.Column('visible_to_client', sa.Boolean(), nullable=False, server_default='false')
            )
        if 'template_id' not in quotes_columns:
            op.add_column('quotes',
                sa.Column('template_id', sa.Integer(), nullable=True)
            )
        
        # Refresh columns after adding
        quotes_columns = [col['name'] for col in inspector.get_columns('quotes')]
    else:
        quotes_columns = []
    
    # Create quote_items table (idempotent)
    if 'quote_items' not in existing_tables:
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
        # Create index (idempotent)
        try:
            op.create_index('ix_quote_items_quote_id', 'quote_items', ['quote_id'])
        except:
            pass  # Index might already exist
    else:
        # Table exists, ensure index exists
        try:
            quote_items_indexes = [idx['name'] for idx in inspector.get_indexes('quote_items')]
            if 'ix_quote_items_quote_id' not in quote_items_indexes:
                op.create_index('ix_quote_items_quote_id', 'quote_items', ['quote_id'])
        except:
            pass
    
    # Create quote_pdf_templates table (idempotent)
    if 'quote_pdf_templates' not in existing_tables:
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
    
    # Recreate indexes in quotes table with new names (idempotent)
    if 'quotes' in existing_tables:
        quotes_indexes = [idx['name'] for idx in inspector.get_indexes('quotes')]
        quotes_columns = [col['name'] for col in inspector.get_columns('quotes')]
        
        # Only create index on quote_number if the column exists
        if 'quote_number' in quotes_columns and 'ix_quotes_quote_number' not in quotes_indexes:
            try:
                op.create_index('ix_quotes_quote_number', 'quotes', ['quote_number'], unique=True)
            except:
                pass
        
        if 'ix_quotes_client_id' not in quotes_indexes:
            try:
                op.create_index('ix_quotes_client_id', 'quotes', ['client_id'])
            except:
                pass
        if 'ix_quotes_project_id' not in quotes_indexes:
            try:
                op.create_index('ix_quotes_project_id', 'quotes', ['project_id'])
            except:
                pass
        if 'ix_quotes_status' not in quotes_indexes:
            try:
                op.create_index('ix_quotes_status', 'quotes', ['status'])
            except:
                pass
        if 'template_id' in quotes_columns and 'ix_quotes_template_id' not in quotes_indexes:
            try:
                op.create_index('ix_quotes_template_id', 'quotes', ['template_id'])
            except:
                pass
    
    # Update foreign key constraints (refresh inspector)
    if 'quotes' in inspector.get_table_names():
        quotes_fks = [fk['name'] for fk in inspector.get_foreign_keys('quotes')]
        quotes_columns = [col['name'] for col in inspector.get_columns('quotes')]
    else:
        quotes_fks = []
        quotes_columns = []
    
    if is_sqlite:
        with op.batch_alter_table('quotes', schema=None) as batch_op:
            # Drop old constraints if they exist
            for old_name in ['offers_client_id_fkey', 'offers_project_id_fkey', 'offers_created_by_fkey', 'offers_accepted_by_fkey']:
                if old_name in quotes_fks:
                    try:
                        batch_op.drop_constraint(old_name, type_='foreignkey')
                    except:
                        pass
            
            # Create new foreign keys
            if 'fk_quotes_client_id' not in quotes_fks:
                batch_op.create_foreign_key('fk_quotes_client_id', 'clients', ['client_id'], ['id'])
            if 'fk_quotes_project_id' not in quotes_fks:
                batch_op.create_foreign_key('fk_quotes_project_id', 'projects', ['project_id'], ['id'])
            if 'fk_quotes_created_by' not in quotes_fks:
                batch_op.create_foreign_key('fk_quotes_created_by', 'users', ['created_by'], ['id'])
            if 'fk_quotes_accepted_by' not in quotes_fks:
                batch_op.create_foreign_key('fk_quotes_accepted_by', 'users', ['accepted_by'], ['id'])
            if 'fk_quotes_template_id' not in quotes_fks and 'template_id' in quotes_columns:
                batch_op.create_foreign_key('fk_quotes_template_id', 'quote_pdf_templates', ['template_id'], ['id'])
    else:
        # PostgreSQL and other databases
        try:
            op.drop_constraint('offers_client_id_fkey', 'quotes', type_='foreignkey')
        except:
            pass
        op.create_foreign_key('fk_quotes_client_id', 'quotes', 'clients', ['client_id'], ['id'], ondelete='CASCADE')
        
        try:
            op.drop_constraint('offers_project_id_fkey', 'quotes', type_='foreignkey')
        except:
            pass
        op.create_foreign_key('fk_quotes_project_id', 'quotes', 'projects', ['project_id'], ['id'], ondelete='SET NULL')
        
        try:
            op.drop_constraint('offers_created_by_fkey', 'quotes', type_='foreignkey')
        except:
            pass
        op.create_foreign_key('fk_quotes_created_by', 'quotes', 'users', ['created_by'], ['id'], ondelete='CASCADE')
        
        try:
            op.drop_constraint('offers_accepted_by_fkey', 'quotes', type_='foreignkey')
        except:
            pass
        op.create_foreign_key('fk_quotes_accepted_by', 'quotes', 'users', ['accepted_by'], ['id'], ondelete='SET NULL')
        
        # Add foreign key for template_id
        if 'template_id' in quotes_columns:
            op.create_foreign_key('fk_quotes_template_id', 'quotes', 'quote_pdf_templates', ['template_id'], ['id'], ondelete='SET NULL')
    
    # Update projects table - rename offer_id to quote_id
    if 'projects' in inspector.get_table_names():
        projects_columns = [col['name'] for col in inspector.get_columns('projects')]
        projects_indexes = [idx['name'] for idx in inspector.get_indexes('projects')]
        projects_fks = [fk['name'] for fk in inspector.get_foreign_keys('projects')]
        
        if 'offer_id' in projects_columns and 'quote_id' not in projects_columns:
            if is_sqlite:
                with op.batch_alter_table('projects', schema=None) as batch_op:
                    batch_op.alter_column('offer_id', new_column_name='quote_id')
                    if 'fk_projects_offer_id' in projects_fks:
                        batch_op.drop_constraint('fk_projects_offer_id', type_='foreignkey')
                    batch_op.create_foreign_key('fk_projects_quote_id', 'quotes', ['quote_id'], ['id'])
            else:
                # PostgreSQL: Drop constraints and indexes BEFORE renaming
                if 'fk_projects_offer_id' in projects_fks:
                    try:
                        op.drop_constraint('fk_projects_offer_id', 'projects', type_='foreignkey')
                    except:
                        pass
                if 'ix_projects_offer_id' in projects_indexes:
                    try:
                        op.drop_index('ix_projects_offer_id', 'projects')
                    except:
                        pass
                # Now rename the column
                op.alter_column('projects', 'offer_id', new_column_name='quote_id', existing_type=sa.Integer(), existing_nullable=True)
                # Create new index and foreign key
                if 'ix_projects_quote_id' not in projects_indexes:
                    try:
                        op.create_index('ix_projects_quote_id', 'projects', ['quote_id'])
                    except:
                        pass
                if 'fk_projects_quote_id' not in projects_fks:
                    op.create_foreign_key('fk_projects_quote_id', 'projects', 'quotes', ['quote_id'], ['id'], ondelete='SET NULL')
    
    # Update invoices table - rename offer_id to quote_id
    if 'invoices' in inspector.get_table_names():
        invoices_columns = [col['name'] for col in inspector.get_columns('invoices')]
        invoices_indexes = [idx['name'] for idx in inspector.get_indexes('invoices')]
        invoices_fks = [fk['name'] for fk in inspector.get_foreign_keys('invoices')]
        
        if 'offer_id' in invoices_columns and 'quote_id' not in invoices_columns:
            if is_sqlite:
                with op.batch_alter_table('invoices', schema=None) as batch_op:
                    batch_op.alter_column('offer_id', new_column_name='quote_id')
                    if 'fk_invoices_offer_id' in invoices_fks:
                        batch_op.drop_constraint('fk_invoices_offer_id', type_='foreignkey')
                    batch_op.create_foreign_key('fk_invoices_quote_id', 'quotes', ['quote_id'], ['id'])
            else:
                # PostgreSQL: Drop constraints and indexes BEFORE renaming
                if 'fk_invoices_offer_id' in invoices_fks:
                    try:
                        op.drop_constraint('fk_invoices_offer_id', 'invoices', type_='foreignkey')
                    except:
                        pass
                if 'ix_invoices_offer_id' in invoices_indexes:
                    try:
                        op.drop_index('ix_invoices_offer_id', 'invoices')
                    except:
                        pass
                # Now rename the column
                op.alter_column('invoices', 'offer_id', new_column_name='quote_id', existing_type=sa.Integer(), existing_nullable=True)
                # Create new index and foreign key
                if 'ix_invoices_quote_id' not in invoices_indexes:
                    try:
                        op.create_index('ix_invoices_quote_id', 'invoices', ['quote_id'])
                    except:
                        pass
                if 'fk_invoices_quote_id' not in invoices_fks:
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

