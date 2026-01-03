"""Add invoice_peppol_transmissions table

Revision ID: 098_add_invoice_peppol_transmissions
Revises: 097_add_stock_lots_for_devaluation
Create Date: 2026-01-03
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "098_add_invoice_peppol_transmissions"
down_revision = "097_add_stock_lots_for_devaluation"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "invoice_peppol_transmissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False, server_default="generic"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("sender_endpoint_id", sa.String(length=100), nullable=True),
        sa.Column("sender_scheme_id", sa.String(length=20), nullable=True),
        sa.Column("recipient_endpoint_id", sa.String(length=100), nullable=True),
        sa.Column("recipient_scheme_id", sa.String(length=20), nullable=True),
        sa.Column("document_id", sa.String(length=100), nullable=True),
        sa.Column("ubl_sha256", sa.String(length=64), nullable=True),
        sa.Column("ubl_xml", sa.Text(), nullable=True),
        sa.Column("message_id", sa.String(length=200), nullable=True),
        sa.Column("response_payload", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_invoice_peppol_transmissions_invoice_id",
        "invoice_peppol_transmissions",
        ["invoice_id"],
        unique=False,
    )
    op.create_index(
        "ix_invoice_peppol_transmissions_status",
        "invoice_peppol_transmissions",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_invoice_peppol_transmissions_created_at",
        "invoice_peppol_transmissions",
        ["created_at"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_invoice_peppol_transmissions_created_at", table_name="invoice_peppol_transmissions")
    op.drop_index("ix_invoice_peppol_transmissions_status", table_name="invoice_peppol_transmissions")
    op.drop_index("ix_invoice_peppol_transmissions_invoice_id", table_name="invoice_peppol_transmissions")
    op.drop_table("invoice_peppol_transmissions")

