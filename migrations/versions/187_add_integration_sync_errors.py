"""Add integration_sync_errors dead-letter table.

Revision ID: 187_add_integration_sync_errors
Revises: 186_add_payroll_export_templates
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "187_add_integration_sync_errors"
down_revision = "186_add_payroll_export_templates"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if "integration_sync_errors" not in inspector.get_table_names():
        op.create_table(
            "integration_sync_errors",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("connector", sa.String(length=50), nullable=False),
            sa.Column("entity_type", sa.String(length=50), nullable=False),
            sa.Column("entity_id", sa.Integer(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=False),
            sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("last_retry_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_integration_sync_errors_connector", "integration_sync_errors", ["connector"])
        op.create_index("ix_integration_sync_errors_entity_type", "integration_sync_errors", ["entity_type"])
        op.create_index("ix_integration_sync_errors_resolved", "integration_sync_errors", ["resolved"])


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if "integration_sync_errors" in inspector.get_table_names():
        op.drop_table("integration_sync_errors")
