"""Add Peppol inbound documents table and inbox setting.

Revision ID: 208_add_peppol_inbound_documents
Revises: 207_invoice_item_time_entry_ids
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "208_add_peppol_inbound_documents"
down_revision = "207_invoice_item_time_entry_ids"
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    try:
        return table_name in inspector.get_table_names()
    except Exception:
        return False


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    try:
        return column_name in {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    if not _has_column(inspector, "settings", "peppol_inbox_enabled"):
        op.add_column(
            "settings",
            sa.Column("peppol_inbox_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        )

    if not _has_table(inspector, "peppol_inbound_documents"):
        op.create_table(
            "peppol_inbound_documents",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("external_id", sa.String(length=64), nullable=False),
            sa.Column("provider", sa.String(length=50), nullable=False),
            sa.Column("direction", sa.String(length=20), nullable=False),
            sa.Column("partner_peppol_id", sa.String(length=120), nullable=True),
            sa.Column("owner_peppol_id", sa.String(length=120), nullable=True),
            sa.Column("document_type", sa.String(length=40), nullable=True),
            sa.Column("document_number", sa.String(length=100), nullable=True),
            sa.Column("issue_date", sa.Date(), nullable=True),
            sa.Column("currency", sa.String(length=3), nullable=True),
            sa.Column("total_amount", sa.Numeric(12, 2), nullable=True),
            sa.Column("ubl_xml", sa.Text(), nullable=True),
            sa.Column("ubl_sha256", sa.String(length=64), nullable=True),
            sa.Column("processed_status", sa.String(length=100), nullable=True),
            sa.Column("raw_payload", sa.JSON(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("matched_client_id", sa.Integer(), sa.ForeignKey("clients.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_peppol_inbound_documents_external_id", "peppol_inbound_documents", ["external_id"], unique=True)
        op.create_index("ix_peppol_inbound_documents_partner_peppol_id", "peppol_inbound_documents", ["partner_peppol_id"])
        op.create_index("ix_peppol_inbound_documents_document_number", "peppol_inbound_documents", ["document_number"])
        op.create_index("ix_peppol_inbound_documents_status", "peppol_inbound_documents", ["status"])
        op.create_index("ix_peppol_inbound_documents_matched_client_id", "peppol_inbound_documents", ["matched_client_id"])


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    if _has_table(inspector, "peppol_inbound_documents"):
        op.drop_table("peppol_inbound_documents")

    if _has_column(inspector, "settings", "peppol_inbox_enabled"):
        op.drop_column("settings", "peppol_inbox_enabled")
