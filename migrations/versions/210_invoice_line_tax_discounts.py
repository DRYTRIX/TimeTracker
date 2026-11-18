"""Add per-line tax, discounts, and position to invoice items; add invoice-level discounts.

Revision ID: 210_invoice_line_tax_discounts
Revises: 209_add_fatturapa_sdi

Adds:
  invoice_items: tax_rate, vat_category, discount_percent, discount_amount, position
  invoices:      discount_percent, discount_amount
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "210_invoice_line_tax_discounts"
down_revision = "209_add_fatturapa_sdi"
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    try:
        return column_name in {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        # Table may not exist yet during partial upgrades.
        return False


def _add_column_if_missing(inspector, table_name: str, column: sa.Column) -> None:
    if not _has_column(inspector, table_name, column.name):
        op.add_column(table_name, column)


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    # invoice_items: per-line tax rate, VAT category, discounts, ordering
    _add_column_if_missing(
        inspector,
        "invoice_items",
        sa.Column("tax_rate", sa.Numeric(5, 2), nullable=True),
    )
    _add_column_if_missing(
        inspector,
        "invoice_items",
        sa.Column("vat_category", sa.String(length=5), nullable=True),
    )
    _add_column_if_missing(
        inspector,
        "invoice_items",
        sa.Column("discount_percent", sa.Numeric(5, 2), nullable=True, server_default="0"),
    )
    _add_column_if_missing(
        inspector,
        "invoice_items",
        sa.Column("discount_amount", sa.Numeric(10, 2), nullable=True, server_default="0"),
    )
    _add_column_if_missing(
        inspector,
        "invoice_items",
        sa.Column("position", sa.Integer(), nullable=True, server_default="0"),
    )

    # invoices: invoice-level discounts
    inspector = inspect(bind)
    _add_column_if_missing(
        inspector,
        "invoices",
        sa.Column("discount_percent", sa.Numeric(5, 2), nullable=True, server_default="0"),
    )
    _add_column_if_missing(
        inspector,
        "invoices",
        sa.Column("discount_amount", sa.Numeric(10, 2), nullable=True, server_default="0"),
    )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    for col in ("discount_percent", "discount_amount"):
        if _has_column(inspector, "invoices", col):
            op.drop_column("invoices", col)

    inspector = inspect(bind)
    for col in ("position", "discount_amount", "discount_percent", "vat_category", "tax_rate"):
        if _has_column(inspector, "invoice_items", col):
            op.drop_column("invoice_items", col)
