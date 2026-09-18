"""Add client surveys and portal custom domain.

Revision ID: 193_client_surveys_and_custom_domain
Revises: 192_add_ai_routing_strategy
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "193_client_surveys_and_custom_domain"
down_revision = "192_add_ai_routing_strategy"
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    try:
        return column_name in {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "clients" in tables and not _has_column(inspector, "clients", "custom_domain"):
        op.add_column("clients", sa.Column("custom_domain", sa.String(length=255), nullable=True))
        op.create_index("ix_clients_custom_domain", "clients", ["custom_domain"], unique=True)

    if "settings" in tables and not _has_column(inspector, "settings", "portal_allowed_custom_domains"):
        op.add_column("settings", sa.Column("portal_allowed_custom_domains", sa.Boolean(), nullable=True))

    if "client_surveys" not in tables:
        op.create_table(
            "client_surveys",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
            sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True),
            sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True),
            sa.Column("trigger", sa.String(length=40), nullable=False),
            sa.Column("token", sa.String(length=64), nullable=False),
            sa.Column("nps_score", sa.Integer(), nullable=True),
            sa.Column("comment", sa.Text(), nullable=True),
            sa.Column("sent_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("responded_at", sa.DateTime(), nullable=True),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index("ix_client_surveys_client_id", "client_surveys", ["client_id"])
        op.create_index("ix_client_surveys_project_id", "client_surveys", ["project_id"])
        op.create_index("ix_client_surveys_invoice_id", "client_surveys", ["invoice_id"])
        op.create_index("ix_client_surveys_trigger", "client_surveys", ["trigger"])
        op.create_index("ix_client_surveys_token", "client_surveys", ["token"], unique=True)


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "client_surveys" in tables:
        op.drop_table("client_surveys")

    if "settings" in tables and _has_column(inspector, "settings", "portal_allowed_custom_domains"):
        op.drop_column("settings", "portal_allowed_custom_domains")

    if "clients" in tables and _has_column(inspector, "clients", "custom_domain"):
        op.drop_index("ix_clients_custom_domain", table_name="clients")
        op.drop_column("clients", "custom_domain")
