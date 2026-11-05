"""align invoices and settings columns with models (idempotent)

Revision ID: 008
Revises: 007
Create Date: 2025-09-08 16:52:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    table_names = set(inspector.get_table_names())

    # Settings: add invoice-related columns if missing
    if "settings" in table_names:
        settings_cols = {c["name"] for c in inspector.get_columns("settings")}
        to_add_settings = []
        if "invoice_prefix" not in settings_cols:
            to_add_settings.append(
                sa.Column("invoice_prefix", sa.String(length=10), nullable=False, server_default="INV")
            )
        if "invoice_start_number" not in settings_cols:
            to_add_settings.append(
                sa.Column("invoice_start_number", sa.Integer(), nullable=False, server_default="1000")
            )
        if "invoice_terms" not in settings_cols:
            to_add_settings.append(
                sa.Column(
                    "invoice_terms",
                    sa.Text(),
                    nullable=False,
                    server_default="Payment is due within 30 days of invoice date.",
                )
            )
        if "invoice_notes" not in settings_cols:
            to_add_settings.append(
                sa.Column("invoice_notes", sa.Text(), nullable=False, server_default="Thank you for your business!")
            )

        if to_add_settings:
            with op.batch_alter_table("settings") as batch_op:
                for col in to_add_settings:
                    batch_op.add_column(col)

    # Invoices: add total_amount if missing
    if "invoices" in table_names:
        invoices_cols = {c["name"] for c in inspector.get_columns("invoices")}
        added_invoice_cols = []
        if "total_amount" not in invoices_cols:
            with op.batch_alter_table("invoices") as batch_op:
                batch_op.add_column(sa.Column("total_amount", sa.Numeric(10, 2), nullable=False, server_default="0"))
            added_invoice_cols.append("total_amount")

        # Backfill total_amount from legacy 'total' if present
        invoices_cols_after = {c["name"] for c in inspector.get_columns("invoices")}
        if "total_amount" in invoices_cols_after and "total" in invoices_cols_after:
            op.execute("UPDATE invoices SET total_amount = COALESCE(total, 0) WHERE total_amount IS NULL")

    # Invoice items: add total_amount and time_entry_ids if missing
    if "invoice_items" in table_names:
        items_cols = {c["name"] for c in inspector.get_columns("invoice_items")}
        with op.batch_alter_table("invoice_items") as batch_op:
            if "total_amount" not in items_cols:
                batch_op.add_column(sa.Column("total_amount", sa.Numeric(10, 2), nullable=False, server_default="0"))
            if "time_entry_ids" not in items_cols:
                batch_op.add_column(sa.Column("time_entry_ids", sa.String(length=500), nullable=True))

        # Backfill total_amount from legacy 'total' if present
        items_cols_after = {c["name"] for c in inspector.get_columns("invoice_items")}
        if "total_amount" in items_cols_after and "total" in items_cols_after:
            op.execute("UPDATE invoice_items SET total_amount = COALESCE(total, 0) WHERE total_amount IS NULL")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "invoice_items" in table_names:
        with op.batch_alter_table("invoice_items") as batch_op:
            items_cols = {c["name"] for c in inspector.get_columns("invoice_items")}
            if "time_entry_ids" in items_cols:
                batch_op.drop_column("time_entry_ids")
            if "total_amount" in items_cols:
                batch_op.drop_column("total_amount")

    if "invoices" in table_names:
        with op.batch_alter_table("invoices") as batch_op:
            invoices_cols = {c["name"] for c in inspector.get_columns("invoices")}
            if "total_amount" in invoices_cols:
                batch_op.drop_column("total_amount")

    if "settings" in table_names:
        with op.batch_alter_table("settings") as batch_op:
            settings_cols = {c["name"] for c in inspector.get_columns("settings")}
            for col in ["invoice_notes", "invoice_terms", "invoice_start_number", "invoice_prefix"]:
                if col in settings_cols:
                    batch_op.drop_column(col)
