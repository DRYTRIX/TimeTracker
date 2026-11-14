"""Extend credit_notes and add credit_note_items.

Revision ID: 212_credit_notes_extended
Revises: 211_invoice_reminder_policies
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "212_credit_notes_extended"
down_revision = "211_invoice_reminder_policies"
branch_labels = None
depends_on = None


def _has_table(inspector, name: str) -> bool:
    try:
        return name in inspector.get_table_names()
    except Exception:
        return False


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    try:
        return column_name in {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return False


def _add_column_if_missing(inspector, table_name: str, column: sa.Column) -> None:
    if not _has_column(inspector, table_name, column.name):
        op.add_column(table_name, column)


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    _add_column_if_missing(inspector, "credit_notes", sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"))
    _add_column_if_missing(inspector, "credit_notes", sa.Column("issue_date", sa.Date(), nullable=True))
    _add_column_if_missing(inspector, "credit_notes", sa.Column("currency_code", sa.String(length=3), nullable=True))
    _add_column_if_missing(inspector, "credit_notes", sa.Column("subtotal", sa.Numeric(10, 2), nullable=True))
    _add_column_if_missing(inspector, "credit_notes", sa.Column("tax_rate", sa.Numeric(5, 2), nullable=True))
    _add_column_if_missing(inspector, "credit_notes", sa.Column("tax_amount", sa.Numeric(10, 2), nullable=True))
    _add_column_if_missing(inspector, "credit_notes", sa.Column("total_amount", sa.Numeric(10, 2), nullable=True))
    _add_column_if_missing(inspector, "credit_notes", sa.Column("vat_category", sa.String(length=5), nullable=True))
    _add_column_if_missing(inspector, "credit_notes", sa.Column("notes", sa.Text(), nullable=True))

    if not _has_table(inspector, "credit_note_items"):
        op.create_table(
            "credit_note_items",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("credit_note_id", sa.Integer(), sa.ForeignKey("credit_notes.id"), nullable=False, index=True),
            sa.Column("description", sa.String(length=500), nullable=False),
            sa.Column("quantity", sa.Numeric(10, 2), nullable=False, server_default="1"),
            sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
            sa.Column("total_amount", sa.Numeric(10, 2), nullable=False),
            sa.Column("tax_rate", sa.Numeric(5, 2), nullable=True),
            sa.Column("vat_category", sa.String(length=5), nullable=True),
            sa.Column("discount_percent", sa.Numeric(5, 2), nullable=True),
            sa.Column("discount_amount", sa.Numeric(10, 2), nullable=True),
            sa.Column("position", sa.Integer(), nullable=True, server_default="0"),
            sa.Column("invoice_item_id", sa.Integer(), sa.ForeignKey("invoice_items.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if _has_table(inspector, "credit_note_items"):
        op.drop_table("credit_note_items")
    for col in (
        "notes",
        "vat_category",
        "total_amount",
        "tax_amount",
        "tax_rate",
        "subtotal",
        "currency_code",
        "issue_date",
        "status",
    ):
        if _has_column(inspector, "credit_notes", col):
            op.drop_column("credit_notes", col)
