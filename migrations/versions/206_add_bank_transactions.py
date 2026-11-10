"""Add bank_transactions table for payment reconciliation.

Revision ID: 206_add_bank_transactions
Revises: 205_add_user_scim_external_id
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "206_add_bank_transactions"
down_revision = "205_add_user_scim_external_id"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if "bank_transactions" not in inspector.get_table_names():
        op.create_table(
            "bank_transactions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("account_label", sa.String(length=120), nullable=True),
            sa.Column("booking_date", sa.Date(), nullable=False),
            sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
            sa.Column("currency", sa.String(length=3), nullable=False, server_default="EUR"),
            sa.Column("counterparty", sa.String(length=255), nullable=True),
            sa.Column("reference", sa.String(length=255), nullable=True),
            sa.Column("raw_payload", sa.JSON(), nullable=True),
            sa.Column("match_status", sa.String(length=20), nullable=False, server_default="pending"),
            sa.Column("matched_invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=True),
            sa.Column("matched_payment_id", sa.Integer(), sa.ForeignKey("payments.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_bank_transactions_booking_date", "bank_transactions", ["booking_date"])
        op.create_index("ix_bank_transactions_match_status", "bank_transactions", ["match_status"])
        op.create_index("ix_bank_transactions_matched_invoice_id", "bank_transactions", ["matched_invoice_id"])
        op.create_index("ix_bank_transactions_matched_payment_id", "bank_transactions", ["matched_payment_id"])


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = inspector.get_table_names()
    if "bank_transactions" in tables:
        existing_indexes = {ix["name"] for ix in inspector.get_indexes("bank_transactions")}
        for name in (
            "ix_bank_transactions_matched_payment_id",
            "ix_bank_transactions_matched_invoice_id",
            "ix_bank_transactions_match_status",
            "ix_bank_transactions_booking_date",
        ):
            if name in existing_indexes:
                op.drop_index(name, table_name="bank_transactions")
        op.drop_table("bank_transactions")
