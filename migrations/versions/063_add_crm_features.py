"""Add CRM features - contacts, deals, leads, communications

Revision ID: 063
Revises: 062
Create Date: 2025-01-27

This migration adds comprehensive CRM functionality:
- Multiple contacts per client
- Sales pipeline/deal tracking
- Lead management
- Communication history
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '063'
down_revision = '062'
branch_labels = None
depends_on = None


def upgrade():
    """Add CRM tables"""
    
    # Contacts table - Multiple contacts per client
    op.create_table(
        'contacts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=200), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('mobile', sa.String(length=50), nullable=True),
        sa.Column('title', sa.String(length=100), nullable=True),
        sa.Column('department', sa.String(length=100), nullable=True),
        sa.Column('role', sa.String(length=50), nullable=True, server_default='contact'),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('tags', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_contacts_client_id'), 'contacts', ['client_id'], unique=False)
    op.create_index(op.f('ix_contacts_email'), 'contacts', ['email'], unique=False)
    
    # Contact communications table (created before deals, FK added later)
    op.create_table(
        'contact_communications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('contact_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('subject', sa.String(length=500), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('direction', sa.String(length=20), nullable=False, server_default='outbound'),
        sa.Column('communication_date', sa.DateTime(), nullable=False),
        sa.Column('follow_up_date', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('related_project_id', sa.Integer(), nullable=True),
        sa.Column('related_quote_id', sa.Integer(), nullable=True),
        sa.Column('related_deal_id', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['related_project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['related_quote_id'], ['quotes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_contact_communications_contact_id'), 'contact_communications', ['contact_id'], unique=False)
    op.create_index(op.f('ix_contact_communications_communication_date'), 'contact_communications', ['communication_date'], unique=False)
    op.create_index(op.f('ix_contact_communications_related_project_id'), 'contact_communications', ['related_project_id'], unique=False)
    op.create_index(op.f('ix_contact_communications_related_quote_id'), 'contact_communications', ['related_quote_id'], unique=False)
    op.create_index(op.f('ix_contact_communications_related_deal_id'), 'contact_communications', ['related_deal_id'], unique=False)
    
    # Leads table
    op.create_table(
        'leads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('company_name', sa.String(length=200), nullable=True),
        sa.Column('email', sa.String(length=200), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('title', sa.String(length=100), nullable=True),
        sa.Column('source', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='new'),
        sa.Column('score', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('estimated_value', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('currency_code', sa.String(length=3), nullable=False, server_default='EUR'),
        sa.Column('converted_to_client_id', sa.Integer(), nullable=True),
        sa.Column('converted_to_deal_id', sa.Integer(), nullable=True),
        sa.Column('converted_at', sa.DateTime(), nullable=True),
        sa.Column('converted_by', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('tags', sa.String(length=500), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['converted_to_client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['converted_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_leads_email'), 'leads', ['email'], unique=False)
    op.create_index(op.f('ix_leads_status'), 'leads', ['status'], unique=False)
    op.create_index(op.f('ix_leads_converted_to_client_id'), 'leads', ['converted_to_client_id'], unique=False)
    op.create_index(op.f('ix_leads_converted_to_deal_id'), 'leads', ['converted_to_deal_id'], unique=False)
    op.create_index(op.f('ix_leads_owner_id'), 'leads', ['owner_id'], unique=False)
    
    # Lead activities table
    op.create_table(
        'lead_activities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('lead_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('subject', sa.String(length=500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('activity_date', sa.DateTime(), nullable=False),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True, server_default='completed'),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lead_activities_lead_id'), 'lead_activities', ['lead_id'], unique=False)
    op.create_index(op.f('ix_lead_activities_activity_date'), 'lead_activities', ['activity_date'], unique=False)
    
    # Deals table
    op.create_table(
        'deals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=True),
        sa.Column('contact_id', sa.Integer(), nullable=True),
        sa.Column('lead_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('stage', sa.String(length=50), nullable=False, server_default='prospecting'),
        sa.Column('value', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('currency_code', sa.String(length=3), nullable=False, server_default='EUR'),
        sa.Column('probability', sa.Integer(), nullable=True, server_default='50'),
        sa.Column('expected_close_date', sa.Date(), nullable=True),
        sa.Column('actual_close_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='open'),
        sa.Column('loss_reason', sa.String(length=500), nullable=True),
        sa.Column('related_quote_id', sa.Integer(), nullable=True),
        sa.Column('related_project_id', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], ),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ),
        sa.ForeignKeyConstraint(['related_quote_id'], ['quotes.id'], ),
        sa.ForeignKeyConstraint(['related_project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_deals_client_id'), 'deals', ['client_id'], unique=False)
    op.create_index(op.f('ix_deals_contact_id'), 'deals', ['contact_id'], unique=False)
    op.create_index(op.f('ix_deals_lead_id'), 'deals', ['lead_id'], unique=False)
    op.create_index(op.f('ix_deals_stage'), 'deals', ['stage'], unique=False)
    op.create_index(op.f('ix_deals_expected_close_date'), 'deals', ['expected_close_date'], unique=False)
    op.create_index(op.f('ix_deals_owner_id'), 'deals', ['owner_id'], unique=False)
    op.create_index(op.f('ix_deals_related_quote_id'), 'deals', ['related_quote_id'], unique=False)
    op.create_index(op.f('ix_deals_related_project_id'), 'deals', ['related_project_id'], unique=False)
    
    # Deal activities table
    op.create_table(
        'deal_activities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('deal_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('subject', sa.String(length=500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('activity_date', sa.DateTime(), nullable=False),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True, server_default='completed'),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['deal_id'], ['deals.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_deal_activities_deal_id'), 'deal_activities', ['deal_id'], unique=False)
    op.create_index(op.f('ix_deal_activities_activity_date'), 'deal_activities', ['activity_date'], unique=False)
    
    # Add foreign key for related_deal_id in contact_communications (deferred)
    # This is done after deals table is created (idempotent)
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    is_sqlite = conn.dialect.name == 'sqlite'
    existing_tables = inspector.get_table_names()
    
    if 'contact_communications' in existing_tables and 'deals' in existing_tables:
        contact_comm_columns = [col['name'] for col in inspector.get_columns('contact_communications')]
        contact_comm_fks = [fk['name'] for fk in inspector.get_foreign_keys('contact_communications')]
        
        if 'related_deal_id' in contact_comm_columns and 'fk_contact_communications_related_deal_id' not in contact_comm_fks:
            if is_sqlite:
                with op.batch_alter_table('contact_communications', schema=None) as batch_op:
                    batch_op.create_foreign_key(
                        'fk_contact_communications_related_deal_id',
                        'deals',
                        ['related_deal_id'],
                        ['id']
                    )
            else:
                op.create_foreign_key(
                    'fk_contact_communications_related_deal_id',
                    'contact_communications',
                    'deals',
                    ['related_deal_id'],
                    ['id']
                )


def downgrade():
    """Remove CRM tables"""
    
    # Drop foreign key first
    op.drop_constraint('fk_contact_communications_related_deal_id', 'contact_communications', type_='foreignkey')
    
    # Drop tables in reverse order
    op.drop_table('deal_activities')
    op.drop_table('deals')
    op.drop_table('lead_activities')
    op.drop_table('leads')
    op.drop_table('contact_communications')
    op.drop_table('contacts')

