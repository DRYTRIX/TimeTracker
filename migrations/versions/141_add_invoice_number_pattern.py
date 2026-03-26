"""Add invoice_number_pattern setting

Revision ID: 141_add_invoice_number_pattern
Revises: 140_client_portal_dashboard_prefs
Create Date: 2026-03-26
"""

from alembic import op
import sqlalchemy as sa


revision = "141_add_invoice_number_pattern"
down_revision = "140_client_portal_dashboard_prefs"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("settings")} if "settings" in inspector.get_table_names() else set()
    if "invoice_number_pattern" not in columns:
        op.add_column(
            "settings",
            sa.Column(
                "invoice_number_pattern",
                sa.String(length=120),
                nullable=False,
                server_default="{PREFIX}-{YYYY}{MM}{DD}-{SEQ}",
            ),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("settings")} if "settings" in inspector.get_table_names() else set()
    if "invoice_number_pattern" in columns:
        op.drop_column("settings", "invoice_number_pattern")
