"""Add crm_communication_templates table.

Revision ID: 213_crm_communication_templates
Revises: 212_credit_notes_extended
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "213_crm_communication_templates"
down_revision = "212_credit_notes_extended"
branch_labels = None
depends_on = None


def _has_table(inspector, name: str) -> bool:
    try:
        return name in inspector.get_table_names()
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if _has_table(inspector, "crm_communication_templates"):
        return
    op.create_table(
        "crm_communication_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False, server_default="email"),
        sa.Column("subject", sa.String(length=500), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("direction", sa.String(length=20), nullable=False, server_default="outbound"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_crm_communication_templates_type", "crm_communication_templates", ["type"])


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if not _has_table(inspector, "crm_communication_templates"):
        return
    op.drop_index("ix_crm_communication_templates_type", table_name="crm_communication_templates")
    op.drop_table("crm_communication_templates")
