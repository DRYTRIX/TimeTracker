"""Add billing entities (our legal entities), payment accounts and the invoice seller link.

Revision ID: 215_add_billing_entities
Revises: 214_add_user_timezone_source
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "215_add_billing_entities"
down_revision = "214_add_user_timezone_source"
branch_labels = None
depends_on = None


def _has_table(inspector, name):
    return name in inspector.get_table_names()


def _has_column(inspector, table_name, column_name):
    try:
        return column_name in {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    if not _has_table(inspector, "billing_entities"):
        op.create_table(
            "billing_entities",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("short_name", sa.String(length=200), nullable=False),
            sa.Column("legal_name", sa.String(length=255), nullable=False),
            sa.Column("country", sa.String(length=2), nullable=True),
            sa.Column("registration_number", sa.String(length=100), nullable=True),
            sa.Column("vat_number", sa.String(length=100), nullable=True),
            sa.Column("address", sa.Text(), nullable=True),
            sa.Column("email", sa.String(length=200), nullable=True),
            sa.Column("phone", sa.String(length=50), nullable=True),
            sa.Column("website", sa.String(length=200), nullable=True),
            sa.Column("number_format", sa.String(length=120), nullable=True),
            sa.Column("number_counter", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("default_vat_category", sa.String(length=5), nullable=True),
            sa.Column("default_tax_rate", sa.Numeric(5, 2), nullable=True),
            sa.Column("default_vat_exemption_code", sa.String(length=50), nullable=True),
            sa.Column("default_vat_exemption_reason", sa.Text(), nullable=True),
            sa.Column("default_terms", sa.Text(), nullable=True),
            sa.Column("default_notes", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_billing_entities_short_name", "billing_entities", ["short_name"])
        op.create_index("ix_billing_entities_status", "billing_entities", ["status"])

    if not _has_table(inspector, "payment_accounts"):
        op.create_table(
            "payment_accounts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "billing_entity_id",
                sa.Integer(),
                sa.ForeignKey("billing_entities.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("currency", sa.String(length=3), nullable=False),
            sa.Column("iban", sa.String(length=64), nullable=False),
            sa.Column("bank_name", sa.String(length=120), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
            sa.Column("details_text", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("iban", "currency", name="uq_payment_accounts_iban_currency"),
        )
        op.create_index("ix_payment_accounts_billing_entity_id", "payment_accounts", ["billing_entity_id"])
        op.create_index("ix_payment_accounts_status", "payment_accounts", ["status"])

    inspector = inspect(bind)
    with op.batch_alter_table("invoices") as batch:
        if not _has_column(inspector, "invoices", "billing_entity_id"):
            batch.add_column(sa.Column("billing_entity_id", sa.Integer(), nullable=True))
            batch.create_foreign_key(
                "fk_invoices_billing_entity_id", "billing_entities", ["billing_entity_id"], ["id"], ondelete="SET NULL"
            )
            batch.create_index("ix_invoices_billing_entity_id", ["billing_entity_id"])
        if not _has_column(inspector, "invoices", "payment_account_id"):
            batch.add_column(sa.Column("payment_account_id", sa.Integer(), nullable=True))
            batch.create_foreign_key(
                "fk_invoices_payment_account_id",
                "payment_accounts",
                ["payment_account_id"],
                ["id"],
                ondelete="SET NULL",
            )
            batch.create_index("ix_invoices_payment_account_id", ["payment_account_id"])
        if not _has_column(inspector, "invoices", "seller_snapshot"):
            batch.add_column(sa.Column("seller_snapshot", sa.JSON(), nullable=True))
        if not _has_column(inspector, "invoices", "payment_details_text"):
            batch.add_column(sa.Column("payment_details_text", sa.Text(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    with op.batch_alter_table("invoices") as batch:
        if _has_column(inspector, "invoices", "payment_details_text"):
            batch.drop_column("payment_details_text")
        if _has_column(inspector, "invoices", "seller_snapshot"):
            batch.drop_column("seller_snapshot")
        if _has_column(inspector, "invoices", "payment_account_id"):
            batch.drop_index("ix_invoices_payment_account_id")
            batch.drop_constraint("fk_invoices_payment_account_id", type_="foreignkey")
            batch.drop_column("payment_account_id")
        if _has_column(inspector, "invoices", "billing_entity_id"):
            batch.drop_index("ix_invoices_billing_entity_id")
            batch.drop_constraint("fk_invoices_billing_entity_id", type_="foreignkey")
            batch.drop_column("billing_entity_id")

    inspector = inspect(bind)
    for table in ("payment_accounts", "billing_entities"):
        if _has_table(inspector, table):
            op.drop_table(table)
