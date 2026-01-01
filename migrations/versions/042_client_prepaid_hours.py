"""Add client prepaid hours support and consumption ledger

Revision ID: 042_client_prepaid_hours
Revises: 041_add_invoice_pdf_templates
Create Date: 2025-11-11

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '042_client_prepaid_hours'
down_revision = '041_add_invoice_pdf_templates'
branch_labels = None
depends_on = None


def upgrade():
    """Add prepaid hours configuration and ledger tracking."""
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Add columns to clients table (idempotent)
    if 'clients' in existing_tables:
        clients_columns = [col['name'] for col in inspector.get_columns('clients')]
        with op.batch_alter_table('clients', schema=None) as batch_op:
            if 'prepaid_hours_monthly' not in clients_columns:
                batch_op.add_column(sa.Column('prepaid_hours_monthly', sa.Numeric(7, 2), nullable=True))
            if 'prepaid_reset_day' not in clients_columns:
                batch_op.add_column(sa.Column('prepaid_reset_day', sa.Integer(), nullable=False, server_default='1'))

    # Create table (idempotent)
    if 'client_prepaid_consumptions' not in existing_tables:
        op.create_table(
        'client_prepaid_consumptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('time_entry_id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=True),
        sa.Column('allocation_month', sa.Date(), nullable=False),
        sa.Column('seconds_consumed', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['time_entry_id'], ['time_entries.id'], ),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
        sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('time_entry_id', name='uq_client_prepaid_consumptions_time_entry_id')
        )
        
        # Create indexes (idempotent)
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('client_prepaid_consumptions')] if 'client_prepaid_consumptions' in inspector.get_table_names() else []
        
        if 'ix_client_prepaid_consumptions_client_month' not in existing_indexes:
            op.create_index(
                'ix_client_prepaid_consumptions_client_month',
                'client_prepaid_consumptions',
                ['client_id', 'allocation_month'],
                unique=False
            )
        if 'ix_client_prepaid_consumptions_invoice_id' not in existing_indexes:
            op.create_index(
                'ix_client_prepaid_consumptions_invoice_id',
                'client_prepaid_consumptions',
                ['invoice_id'],
                unique=False
            )

    # Remove server default now that existing rows are backfilled (only if column exists)
    if 'clients' in existing_tables:
        clients_columns = [col['name'] for col in inspector.get_columns('clients')]
        if 'prepaid_reset_day' in clients_columns:
            # Check if it has a server default
            prepaid_col = next((col for col in inspector.get_columns('clients') if col['name'] == 'prepaid_reset_day'), None)
            if prepaid_col and prepaid_col.get('default'):
                with op.batch_alter_table('clients', schema=None) as batch_op:
                    batch_op.alter_column('prepaid_reset_day', server_default=None)


def downgrade():
    """Revert prepaid hours schema changes."""
    op.drop_index('ix_client_prepaid_consumptions_invoice_id', table_name='client_prepaid_consumptions')
    op.drop_index('ix_client_prepaid_consumptions_client_month', table_name='client_prepaid_consumptions')
    op.drop_table('client_prepaid_consumptions')

    with op.batch_alter_table('clients', schema=None) as batch_op:
        batch_op.drop_column('prepaid_reset_day')
        batch_op.drop_column('prepaid_hours_monthly')

