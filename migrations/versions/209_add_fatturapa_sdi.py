"""Add FatturaPA / SDI fields and invoice_sdi_transmissions table.

Adds Italian e-invoicing company/client/invoice columns and transmission audit
table for FatturaPA XML export and SDI intermediary sending.

Revision ID: 209_add_fatturapa_sdi
Revises: 208_add_peppol_inbound_documents
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "209_add_fatturapa_sdi"
down_revision = "208_add_peppol_inbound_documents"
branch_labels = None
depends_on = None


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

    # Settings: Italian company + SDI transport
    _add_column_if_missing(
        inspector, "settings", sa.Column("company_codice_fiscale", sa.String(length=16), nullable=True)
    )
    _add_column_if_missing(
        inspector,
        "settings",
        sa.Column("company_regime_fiscale", sa.String(length=4), nullable=True, server_default="RF01"),
    )
    _add_column_if_missing(inspector, "settings", sa.Column("company_provincia", sa.String(length=2), nullable=True))
    _add_column_if_missing(
        inspector, "settings", sa.Column("sdi_enabled", sa.Boolean(), nullable=False, server_default=sa.false())
    )
    _add_column_if_missing(inspector, "settings", sa.Column("sdi_transport_url", sa.String(length=500), nullable=True))
    _add_column_if_missing(inspector, "settings", sa.Column("sdi_transport_token", sa.String(length=255), nullable=True))
    _add_column_if_missing(inspector, "settings", sa.Column("sdi_transmitter_id", sa.String(length=16), nullable=True))
    _add_column_if_missing(
        inspector, "settings", sa.Column("sdi_timeout", sa.Integer(), nullable=True, server_default="30")
    )

    # Clients: FatturaPA recipient fields
    inspector = inspect(bind)
    _add_column_if_missing(
        inspector, "clients", sa.Column("sdi_codice_destinatario", sa.String(length=7), nullable=True)
    )
    _add_column_if_missing(inspector, "clients", sa.Column("pec_email", sa.String(length=200), nullable=True))
    _add_column_if_missing(inspector, "clients", sa.Column("codice_fiscale", sa.String(length=16), nullable=True))
    _add_column_if_missing(inspector, "clients", sa.Column("provincia", sa.String(length=2), nullable=True))

    # Invoices: PA procurement codes
    inspector = inspect(bind)
    _add_column_if_missing(inspector, "invoices", sa.Column("cig", sa.String(length=15), nullable=True))
    _add_column_if_missing(inspector, "invoices", sa.Column("cup", sa.String(length=15), nullable=True))

    # Transmission audit table
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()
    if "invoice_sdi_transmissions" not in existing_tables:
        op.create_table(
            "invoice_sdi_transmissions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=False),
            sa.Column("filename", sa.String(length=100), nullable=True),
            sa.Column("progressivo", sa.String(length=10), nullable=True),
            sa.Column("formato", sa.String(length=5), nullable=True),
            sa.Column("xml", sa.Text(), nullable=True),
            sa.Column("xml_sha256", sa.String(length=64), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
            sa.Column("sdi_identifier", sa.String(length=100), nullable=True),
            sa.Column("message_id", sa.String(length=200), nullable=True),
            sa.Column("notifications", sa.JSON(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("sent_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index(
            "ix_invoice_sdi_transmissions_invoice_id",
            "invoice_sdi_transmissions",
            ["invoice_id"],
            unique=False,
        )
        op.create_index(
            "ix_invoice_sdi_transmissions_status",
            "invoice_sdi_transmissions",
            ["status"],
            unique=False,
        )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    if "invoice_sdi_transmissions" in inspector.get_table_names():
        try:
            op.drop_index("ix_invoice_sdi_transmissions_status", table_name="invoice_sdi_transmissions")
        except Exception:
            pass
        try:
            op.drop_index("ix_invoice_sdi_transmissions_invoice_id", table_name="invoice_sdi_transmissions")
        except Exception:
            pass
        op.drop_table("invoice_sdi_transmissions")

    inspector = inspect(bind)
    for col in ("cup", "cig"):
        if _has_column(inspector, "invoices", col):
            op.drop_column("invoices", col)

    inspector = inspect(bind)
    for col in ("provincia", "codice_fiscale", "pec_email", "sdi_codice_destinatario"):
        if _has_column(inspector, "clients", col):
            op.drop_column("clients", col)

    inspector = inspect(bind)
    for col in (
        "sdi_timeout",
        "sdi_transmitter_id",
        "sdi_transport_token",
        "sdi_transport_url",
        "sdi_enabled",
        "company_provincia",
        "company_regime_fiscale",
        "company_codice_fiscale",
    ):
        if _has_column(inspector, "settings", col):
            op.drop_column("settings", col)
