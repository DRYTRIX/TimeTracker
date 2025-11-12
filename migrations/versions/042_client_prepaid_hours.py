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
    with op.batch_alter_table('clients', schema=None) as batch_op:
        batch_op.add_column(sa.Column('prepaid_hours_monthly', sa.Numeric(7, 2), nullable=True))
        batch_op.add_column(sa.Column('prepaid_reset_day', sa.Integer(), nullable=False, server_default='1'))

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
    op.create_index(
        'ix_client_prepaid_consumptions_client_month',
        'client_prepaid_consumptions',
        ['client_id', 'allocation_month'],
        unique=False
    )
    op.create_index(
        'ix_client_prepaid_consumptions_invoice_id',
        'client_prepaid_consumptions',
        ['invoice_id'],
        unique=False
    )

    # Remove server default now that existing rows are backfilled
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

