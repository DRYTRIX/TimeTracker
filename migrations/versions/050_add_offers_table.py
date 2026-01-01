"""Add offers table and link to projects and invoices

Revision ID: 050
Revises: 049
Create Date: 2025-01-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '050'
down_revision = '049'
branch_labels = None
depends_on = None


def upgrade():
    """Add offers table and foreign keys to projects and invoices"""
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    is_sqlite = conn.dialect.name == 'sqlite'
    existing_tables = inspector.get_table_names()
    
    # Create offers table (idempotent)
    if 'offers' not in existing_tables:
        op.create_table('offers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('offer_number', sa.String(length=50), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('total_amount', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('hourly_rate', sa.Numeric(precision=9, scale=2), nullable=True),
        sa.Column('estimated_hours', sa.Float(), nullable=True),
        sa.Column('tax_rate', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0'),
        sa.Column('currency_code', sa.String(length=3), nullable=False, server_default='EUR'),
        sa.Column('valid_until', sa.Date(), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('accepted_at', sa.DateTime(), nullable=True),
        sa.Column('rejected_at', sa.DateTime(), nullable=True),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('accepted_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('terms', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['accepted_by'], ['users.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Create indexes (idempotent)
        offers_indexes = [idx['name'] for idx in inspector.get_indexes('offers')] if 'offers' in inspector.get_table_names() else []
        
        if 'ix_offers_offer_number' not in offers_indexes:
            op.create_index('ix_offers_offer_number', 'offers', ['offer_number'], unique=True)
        if 'ix_offers_client_id' not in offers_indexes:
            op.create_index('ix_offers_client_id', 'offers', ['client_id'])
        if 'ix_offers_project_id' not in offers_indexes:
            op.create_index('ix_offers_project_id', 'offers', ['project_id'])
        if 'ix_offers_status' not in offers_indexes:
            op.create_index('ix_offers_status', 'offers', ['status'])
    
    # Add offer_id to projects table (idempotent)
    if 'projects' in existing_tables:
        projects_columns = [col['name'] for col in inspector.get_columns('projects')]
        projects_indexes = [idx['name'] for idx in inspector.get_indexes('projects')]
        projects_fks = [fk['name'] for fk in inspector.get_foreign_keys('projects')]
        
        if 'offer_id' not in projects_columns:
            op.add_column('projects',
                sa.Column('offer_id', sa.Integer(), nullable=True)
            )
        
        if 'offer_id' in projects_columns:
            if 'ix_projects_offer_id' not in projects_indexes:
                op.create_index('ix_projects_offer_id', 'projects', ['offer_id'])
            
            if 'fk_projects_offer_id' not in projects_fks:
                if is_sqlite:
                    with op.batch_alter_table('projects', schema=None) as batch_op:
                        batch_op.create_foreign_key('fk_projects_offer_id', 'offers', ['offer_id'], ['id'])
                else:
                    op.create_foreign_key('fk_projects_offer_id', 'projects', 'offers', ['offer_id'], ['id'], ondelete='SET NULL')
    
    # Add offer_id to invoices table (idempotent)
    if 'invoices' in existing_tables:
        invoices_columns = [col['name'] for col in inspector.get_columns('invoices')]
        invoices_indexes = [idx['name'] for idx in inspector.get_indexes('invoices')]
        invoices_fks = [fk['name'] for fk in inspector.get_foreign_keys('invoices')]
        
        if 'offer_id' not in invoices_columns:
            op.add_column('invoices',
                sa.Column('offer_id', sa.Integer(), nullable=True)
            )
        
        if 'offer_id' in invoices_columns:
            if 'ix_invoices_offer_id' not in invoices_indexes:
                op.create_index('ix_invoices_offer_id', 'invoices', ['offer_id'])
            
            if 'fk_invoices_offer_id' not in invoices_fks:
                if is_sqlite:
                    with op.batch_alter_table('invoices', schema=None) as batch_op:
                        batch_op.create_foreign_key('fk_invoices_offer_id', 'offers', ['offer_id'], ['id'])
                else:
                    op.create_foreign_key('fk_invoices_offer_id', 'invoices', 'offers', ['offer_id'], ['id'], ondelete='SET NULL')


def downgrade():
    """Remove offers table and foreign keys from projects and invoices"""
    
    # Remove foreign keys and columns from invoices
    op.drop_index('ix_invoices_offer_id', 'invoices')
    op.drop_constraint('fk_invoices_offer_id', 'invoices', type_='foreignkey')
    op.drop_column('invoices', 'offer_id')
    
    # Remove foreign keys and columns from projects
    op.drop_index('ix_projects_offer_id', 'projects')
    op.drop_constraint('fk_projects_offer_id', 'projects', type_='foreignkey')
    op.drop_column('projects', 'offer_id')
    
    # Drop offers table
    op.drop_index('ix_offers_status', 'offers')
    op.drop_index('ix_offers_project_id', 'offers')
    op.drop_index('ix_offers_client_id', 'offers')
    op.drop_index('ix_offers_offer_number', 'offers')
    op.drop_table('offers')

