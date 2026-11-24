"""How hours become invoice lines: line kind, edited flags, layout and description template.

- ``invoice_items``: ``kind`` (``time`` or ``manual``) and ``description_edited``,
  ``quantity_edited``, ``price_edited``. Lines with time links become ``time``.
- ``invoices``: ``period_start``, ``period_end``, ``hours_layout``, ``line_template``.
- ``projects``: ``last_hours_layout``, ``last_line_template``, the default for the project's next invoice.

Revision ID: 220_add_invoice_hours_layout
Revises: 219_add_invoice_time_links
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "220_add_invoice_hours_layout"
down_revision = "219_add_invoice_time_links"
branch_labels = None
depends_on = None


def _has_table(inspector, name):
    try:
        return name in inspector.get_table_names()
    except Exception:
        return False


def _columns(inspector, table_name):
    try:
        return {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return set()


def _new_columns():
    """(table, column) for every column this migration adds; fresh Column objects each call."""
    return [
        ("invoice_items", sa.Column("kind", sa.String(length=20), nullable=False, server_default="manual")),
        ("invoice_items", sa.Column("description_edited", sa.Boolean(), nullable=False, server_default=sa.false())),
        ("invoice_items", sa.Column("quantity_edited", sa.Boolean(), nullable=False, server_default=sa.false())),
        ("invoice_items", sa.Column("price_edited", sa.Boolean(), nullable=False, server_default=sa.false())),
        ("invoices", sa.Column("period_start", sa.Date(), nullable=True)),
        ("invoices", sa.Column("period_end", sa.Date(), nullable=True)),
        ("invoices", sa.Column("hours_layout", sa.String(length=20), nullable=True)),
        ("invoices", sa.Column("line_template", sa.String(length=255), nullable=True)),
        ("projects", sa.Column("last_hours_layout", sa.String(length=20), nullable=True)),
        ("projects", sa.Column("last_line_template", sa.String(length=255), nullable=True)),
    ]


def upgrade():
    # Plain ADD COLUMN (no batch copy): SQLite keeps the tables, so foreign keys pointing at them stay valid
    bind = op.get_bind()
    inspector = inspect(bind)
    for table_name, column in _new_columns():
        if column.name not in _columns(inspector, table_name):
            op.add_column(table_name, column)

    # Lines that bill time entries (any link, released ones included) are time lines
    if _has_table(inspector, "invoice_time_links"):
        bind.execute(
            sa.text(
                "UPDATE invoice_items SET kind = 'time' "
                "WHERE EXISTS (SELECT 1 FROM invoice_time_links l WHERE l.invoice_item_id = invoice_items.id)"
            )
        )


def downgrade():
    inspector = inspect(op.get_bind())
    for table_name, column in reversed(_new_columns()):
        name = column.name
        if name in _columns(inspector, table_name):
            op.drop_column(table_name, name)
