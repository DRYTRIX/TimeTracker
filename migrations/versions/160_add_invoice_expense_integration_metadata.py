"""Add integration_metadata JSON to invoices and expenses.

Revision ID: 160_add_invoice_expense_integration_metadata
Revises: 159_add_quote_number_settings
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "160_add_invoice_expense_integration_metadata"
down_revision = "159_add_quote_number_settings"
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    try:
        return column_name in {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "invoices" in tables and not _has_column(inspector, "invoices", "integration_metadata"):
        op.add_column("invoices", sa.Column("integration_metadata", sa.JSON(), nullable=True))

    if "expenses" in tables and not _has_column(inspector, "expenses", "integration_metadata"):
        op.add_column("expenses", sa.Column("integration_metadata", sa.JSON(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "invoices" in tables and _has_column(inspector, "invoices", "integration_metadata"):
        op.drop_column("invoices", "integration_metadata")
    if "expenses" in tables and _has_column(inspector, "expenses", "integration_metadata"):
        op.drop_column("expenses", "integration_metadata")
