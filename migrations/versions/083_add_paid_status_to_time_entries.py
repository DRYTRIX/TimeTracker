"""Add paid status and invoice number to time entries

Revision ID: 083_add_paid_status_time_entries
Revises: 082_add_global_integrations
Create Date: 2025-01-27 12:00:00.000000

This migration adds:
- paid column (Boolean) to mark hours as paid
- invoice_number column (String) to store internal invoice number reference
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '083_add_paid_status_time_entries'
down_revision = '082_add_global_integrations'
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    try:
        return column_name in [col['name'] for col in inspector.get_columns(table_name)]
    except Exception:
        return False


def upgrade():
    """Add paid and invoice_number columns to time_entries"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if 'time_entries' not in inspector.get_table_names():
        return

    # Add paid column if it doesn't exist
    if not _has_column(inspector, 'time_entries', 'paid'):
        op.add_column('time_entries', sa.Column('paid', sa.Boolean(), nullable=False, server_default='false'))

    # Add invoice_number column if it doesn't exist
    if not _has_column(inspector, 'time_entries', 'invoice_number'):
        op.add_column('time_entries', sa.Column('invoice_number', sa.String(100), nullable=True))

    # Add index on paid status for faster queries
    try:
        op.create_index('idx_time_entries_paid', 'time_entries', ['paid'], unique=False)
    except Exception:
        pass  # Index might already exist


def downgrade():
    """Remove paid and invoice_number columns from time_entries"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if 'time_entries' not in inspector.get_table_names():
        return

    # Remove index
    try:
        op.drop_index('idx_time_entries_paid', table_name='time_entries')
    except Exception:
        pass

    # Remove invoice_number column
    if _has_column(inspector, 'time_entries', 'invoice_number'):
        op.drop_column('time_entries', 'invoice_number')

    # Remove paid column
    if _has_column(inspector, 'time_entries', 'paid'):
        op.drop_column('time_entries', 'paid')
