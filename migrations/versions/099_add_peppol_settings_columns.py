"""Add Peppol settings fields

Revision ID: 099_add_peppol_settings_columns
Revises: 098_add_invoice_peppol_transmissions
Create Date: 2026-01-03
"""

from alembic import op
import sqlalchemy as sa


revision = "099_add_peppol_settings_columns"
down_revision = "098_add_invoice_peppol_transmissions"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("settings", sa.Column("peppol_enabled", sa.Boolean(), nullable=True))
    op.add_column("settings", sa.Column("peppol_sender_endpoint_id", sa.String(length=100), nullable=True, server_default=""))
    op.add_column("settings", sa.Column("peppol_sender_scheme_id", sa.String(length=20), nullable=True, server_default=""))
    op.add_column("settings", sa.Column("peppol_sender_country", sa.String(length=2), nullable=True, server_default=""))
    op.add_column("settings", sa.Column("peppol_access_point_url", sa.String(length=500), nullable=True, server_default=""))
    op.add_column("settings", sa.Column("peppol_access_point_token", sa.String(length=255), nullable=True, server_default=""))
    op.add_column("settings", sa.Column("peppol_access_point_timeout", sa.Integer(), nullable=True, server_default="30"))
    op.add_column("settings", sa.Column("peppol_provider", sa.String(length=50), nullable=True, server_default="generic"))


def downgrade():
    op.drop_column("settings", "peppol_provider")
    op.drop_column("settings", "peppol_access_point_timeout")
    op.drop_column("settings", "peppol_access_point_token")
    op.drop_column("settings", "peppol_access_point_url")
    op.drop_column("settings", "peppol_sender_country")
    op.drop_column("settings", "peppol_sender_scheme_id")
    op.drop_column("settings", "peppol_sender_endpoint_id")
    op.drop_column("settings", "peppol_enabled")

