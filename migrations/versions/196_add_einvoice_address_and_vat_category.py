"""Add structured e-invoice address fields and VAT category settings.

Adds company street/postcode/city/country, IBAN/BIC, default VAT category
settings; client street/postcode/city/country/vat_id; and per-invoice VAT
category overrides for Factur-X / ZUGFeRD EN 16931 compliance (Discussion #433).

Revision ID: 196_add_einvoice_address_and_vat_category
Revises: 195_add_idle_unanswered_action
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "196_add_einvoice_address_and_vat_category"
down_revision = "195_add_idle_unanswered_action"
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

    # Settings: structured company address + IBAN + default VAT category
    _add_column_if_missing(
        inspector, "settings", sa.Column("company_street", sa.String(length=255), nullable=True)
    )
    _add_column_if_missing(
        inspector, "settings", sa.Column("company_postcode", sa.String(length=32), nullable=True)
    )
    _add_column_if_missing(
        inspector, "settings", sa.Column("company_city", sa.String(length=100), nullable=True)
    )
    _add_column_if_missing(
        inspector, "settings", sa.Column("company_country", sa.String(length=2), nullable=True)
    )
    _add_column_if_missing(
        inspector, "settings", sa.Column("company_iban", sa.String(length=34), nullable=True)
    )
    _add_column_if_missing(
        inspector, "settings", sa.Column("company_bic", sa.String(length=11), nullable=True)
    )
    _add_column_if_missing(
        inspector,
        "settings",
        sa.Column(
            "invoices_default_vat_category",
            sa.String(length=5),
            nullable=False,
            server_default="S",
        ),
    )
    _add_column_if_missing(
        inspector,
        "settings",
        sa.Column("invoices_default_vat_exemption_reason", sa.Text(), nullable=True),
    )
    _add_column_if_missing(
        inspector,
        "settings",
        sa.Column("invoices_default_vat_exemption_code", sa.String(length=50), nullable=True),
    )

    # Clients: structured address + VAT ID
    inspector = inspect(bind)
    _add_column_if_missing(
        inspector, "clients", sa.Column("street", sa.String(length=255), nullable=True)
    )
    _add_column_if_missing(
        inspector, "clients", sa.Column("postcode", sa.String(length=32), nullable=True)
    )
    _add_column_if_missing(
        inspector, "clients", sa.Column("city", sa.String(length=100), nullable=True)
    )
    _add_column_if_missing(
        inspector, "clients", sa.Column("country", sa.String(length=2), nullable=True)
    )
    _add_column_if_missing(
        inspector, "clients", sa.Column("vat_id", sa.String(length=50), nullable=True)
    )

    # Invoices: per-invoice VAT category override
    inspector = inspect(bind)
    _add_column_if_missing(
        inspector, "invoices", sa.Column("vat_category", sa.String(length=5), nullable=True)
    )
    _add_column_if_missing(
        inspector, "invoices", sa.Column("vat_exemption_reason", sa.Text(), nullable=True)
    )
    _add_column_if_missing(
        inspector, "invoices", sa.Column("vat_exemption_code", sa.String(length=50), nullable=True)
    )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    for col in (
        "vat_exemption_code",
        "vat_exemption_reason",
        "vat_category",
    ):
        if _has_column(inspector, "invoices", col):
            op.drop_column("invoices", col)

    inspector = inspect(bind)
    for col in ("vat_id", "country", "city", "postcode", "street"):
        if _has_column(inspector, "clients", col):
            op.drop_column("clients", col)

    inspector = inspect(bind)
    for col in (
        "invoices_default_vat_exemption_code",
        "invoices_default_vat_exemption_reason",
        "invoices_default_vat_category",
        "company_bic",
        "company_iban",
        "company_country",
        "company_city",
        "company_postcode",
        "company_street",
    ):
        if _has_column(inspector, "settings", col):
            op.drop_column("settings", col)
