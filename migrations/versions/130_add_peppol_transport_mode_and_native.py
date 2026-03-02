"""Add Peppol transport mode and native settings

Revision ID: 130_add_peppol_transport_mode_and_native
Revises: 129_merge_118_128_heads
Create Date: 2026-03-02

Adds peppol_transport_mode (generic|native), peppol_sml_url,
peppol_native_cert_path, peppol_native_key_path for native PEPPOL stack.
"""

from alembic import op
import sqlalchemy as sa


revision = "130_add_peppol_transport_mode_and_native"
down_revision = "129_merge_118_128_heads"
branch_labels = None
depends_on = None


def upgrade():
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)
    if "settings" not in inspector.get_table_names():
        return
    settings_columns = {c["name"] for c in inspector.get_columns("settings")}

    columns_to_add = [
        ("peppol_transport_mode", sa.Column("peppol_transport_mode", sa.String(20), nullable=True, server_default="generic")),
        ("peppol_sml_url", sa.Column("peppol_sml_url", sa.String(500), nullable=True, server_default="")),
        ("peppol_native_cert_path", sa.Column("peppol_native_cert_path", sa.String(500), nullable=True, server_default="")),
        ("peppol_native_key_path", sa.Column("peppol_native_key_path", sa.String(500), nullable=True, server_default="")),
        ("invoices_pdfa3_compliant", sa.Column("invoices_pdfa3_compliant", sa.Boolean(), nullable=False, server_default="0")),
        ("invoices_validate_export", sa.Column("invoices_validate_export", sa.Boolean(), nullable=False, server_default="0")),
        ("invoices_verapdf_path", sa.Column("invoices_verapdf_path", sa.String(500), nullable=True, server_default="")),
    ]
    for col_name, col_def in columns_to_add:
        if col_name not in settings_columns:
            op.add_column("settings", col_def)


def downgrade():
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)
    if "settings" not in inspector.get_table_names():
        return
    settings_columns = {c["name"] for c in inspector.get_columns("settings")}
    for col_name in ("invoices_verapdf_path", "invoices_validate_export", "invoices_pdfa3_compliant", "peppol_native_key_path", "peppol_native_cert_path", "peppol_sml_url", "peppol_transport_mode"):
        if col_name in settings_columns:
            op.drop_column("settings", col_name)
