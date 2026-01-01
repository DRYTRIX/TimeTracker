"""Add recurring invoices and email tracking

Revision ID: 045
Revises: 044
Create Date: 2025-01-22

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '045'
down_revision = '044'
branch_labels = None
depends_on = None


def upgrade():
    """Create recurring_invoices and invoice_emails tables, add recurring_invoice_id to invoices"""
    
    # Create recurring_invoices table
    op.create_table('recurring_invoices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('frequency', sa.String(length=20), nullable=False),
        sa.Column('interval', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('next_run_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('client_name', sa.String(length=200), nullable=False),
        sa.Column('client_email', sa.String(length=200), nullable=True),
        sa.Column('client_address', sa.Text(), nullable=True),
        sa.Column('due_date_days', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('tax_rate', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0'),
        sa.Column('currency_code', sa.String(length=3), nullable=False, server_default='EUR'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('terms', sa.Text(), nullable=True),
        sa.Column('template_id', sa.Integer(), nullable=True),
        sa.Column('auto_send', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('auto_include_time_entries', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_generated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['template_id'], ['invoice_templates.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for recurring_invoices
    op.create_index('ix_recurring_invoices_project_id', 'recurring_invoices', ['project_id'])
    op.create_index('ix_recurring_invoices_client_id', 'recurring_invoices', ['client_id'])
    op.create_index('ix_recurring_invoices_next_run_date', 'recurring_invoices', ['next_run_date'])
    op.create_index('ix_recurring_invoices_is_active', 'recurring_invoices', ['is_active'])
    
    # Create invoice_emails table
    op.create_table('invoice_emails',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('recipient_email', sa.String(length=200), nullable=False),
        sa.Column('subject', sa.String(length=500), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('sent_by', sa.Integer(), nullable=False),
        sa.Column('opened_at', sa.DateTime(), nullable=True),
        sa.Column('opened_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_opened_at', sa.DateTime(), nullable=True),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='sent'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sent_by'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for invoice_emails
    op.create_index('ix_invoice_emails_invoice_id', 'invoice_emails', ['invoice_id'])
    op.create_index('ix_invoice_emails_recipient_email', 'invoice_emails', ['recipient_email'])
    op.create_index('ix_invoice_emails_status', 'invoice_emails', ['status'])
    op.create_index('ix_invoice_emails_sent_at', 'invoice_emails', ['sent_at'])
    
    # Add recurring_invoice_id to invoices table (idempotent)
    from sqlalchemy import inspect
    inspector = inspect(op.get_bind())
    existing_tables = inspector.get_table_names()
    
    if 'invoices' in existing_tables:
        invoices_columns = [col['name'] for col in inspector.get_columns('invoices')]
        invoices_indexes = [idx['name'] for idx in inspector.get_indexes('invoices')]
        invoices_fks = [fk['name'] for fk in inspector.get_foreign_keys('invoices')]
        is_sqlite = op.get_bind().dialect.name == 'sqlite'
        
        if 'recurring_invoice_id' not in invoices_columns:
            op.add_column('invoices', sa.Column('recurring_invoice_id', sa.Integer(), nullable=True))
        
        if 'ix_invoices_recurring_invoice_id' not in invoices_indexes:
            try:
                op.create_index('ix_invoices_recurring_invoice_id', 'invoices', ['recurring_invoice_id'])
            except:
                pass
        
        if 'recurring_invoice_id' in invoices_columns and 'fk_invoices_recurring_invoice_id' not in invoices_fks:
            if is_sqlite:
                with op.batch_alter_table('invoices', schema=None) as batch_op:
                    try:
                        batch_op.create_foreign_key('fk_invoices_recurring_invoice_id', 'recurring_invoices', ['recurring_invoice_id'], ['id'])
                    except:
                        pass
            else:
                try:
                    op.create_foreign_key('fk_invoices_recurring_invoice_id', 'invoices', 'recurring_invoices', ['recurring_invoice_id'], ['id'], ondelete='SET NULL')
                except:
                    pass


def downgrade():
    """Remove recurring invoices and email tracking tables"""
    
    # Remove recurring_invoice_id from invoices
    op.drop_constraint('fk_invoices_recurring_invoice_id', 'invoices', type_='foreignkey')
    op.drop_index('ix_invoices_recurring_invoice_id', table_name='invoices')
    op.drop_column('invoices', 'recurring_invoice_id')
    
    # Drop invoice_emails table
    op.drop_index('ix_invoice_emails_sent_at', table_name='invoice_emails')
    op.drop_index('ix_invoice_emails_status', table_name='invoice_emails')
    op.drop_index('ix_invoice_emails_recipient_email', table_name='invoice_emails')
    op.drop_index('ix_invoice_emails_invoice_id', table_name='invoice_emails')
    op.drop_table('invoice_emails')
    
    # Drop recurring_invoices table
    op.drop_index('ix_recurring_invoices_is_active', table_name='recurring_invoices')
    op.drop_index('ix_recurring_invoices_next_run_date', table_name='recurring_invoices')
    op.drop_index('ix_recurring_invoices_client_id', table_name='recurring_invoices')
    op.drop_index('ix_recurring_invoices_project_id', table_name='recurring_invoices')
    op.drop_table('recurring_invoices')

