"""add missing invoice and settings columns (idempotent)

Revision ID: 007
Revises: 006
Create Date: 2025-09-08 16:48:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    table_names = set(inspector.get_table_names())

    # Settings table columns
    if "settings" in table_names:
        settings_cols = {c["name"] for c in inspector.get_columns("settings")}
        add_settings_cols = []
        if "company_tax_id" not in settings_cols:
            add_settings_cols.append(
                sa.Column("company_tax_id", sa.String(length=100), nullable=True, server_default="")
            )
        if "company_bank_info" not in settings_cols:
            add_settings_cols.append(sa.Column("company_bank_info", sa.Text(), nullable=True, server_default=""))
        if add_settings_cols:
            with op.batch_alter_table("settings") as batch_op:
                for col in add_settings_cols:
                    batch_op.add_column(col)

    # Invoices table columns
    if "invoices" in table_names:
        invoices_cols = {c["name"] for c in inspector.get_columns("invoices")}
        add_invoice_cols = []
        if "client_name" not in invoices_cols:
            # Non-nullable in model; provide server_default for backfill
            add_invoice_cols.append(sa.Column("client_name", sa.String(length=200), nullable=False, server_default=""))
        if "client_email" not in invoices_cols:
            add_invoice_cols.append(sa.Column("client_email", sa.String(length=200), nullable=True))
        if "client_address" not in invoices_cols:
            add_invoice_cols.append(sa.Column("client_address", sa.Text(), nullable=True))
        if add_invoice_cols:
            with op.batch_alter_table("invoices") as batch_op:
                for col in add_invoice_cols:
                    batch_op.add_column(col)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "invoices" in table_names:
        with op.batch_alter_table("invoices") as batch_op:
            # Drops are safe even if column absent on some backends will raise; check first
            invoices_cols = {c["name"] for c in inspector.get_columns("invoices")}
            if "client_address" in invoices_cols:
                batch_op.drop_column("client_address")
            if "client_email" in invoices_cols:
                batch_op.drop_column("client_email")
            if "client_name" in invoices_cols:
                batch_op.drop_column("client_name")

    if "settings" in table_names:
        with op.batch_alter_table("settings") as batch_op:
            settings_cols = {c["name"] for c in inspector.get_columns("settings")}
            if "company_bank_info" in settings_cols:
                batch_op.drop_column("company_bank_info")
            if "company_tax_id" in settings_cols:
                batch_op.drop_column("company_tax_id")
