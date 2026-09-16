"""Add shared report links table.

Revision ID: 190_add_shared_report_links
Revises: 189_add_recurring_project_costs
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "190_add_shared_report_links"
down_revision = "189_add_recurring_project_costs"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if "shared_report_links" in inspector.get_table_names():
        return

    op.create_table(
        "shared_report_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("token", sa.String(length=36), nullable=False),
        sa.Column("saved_view_id", sa.Integer(), sa.ForeignKey("saved_report_views.id", ondelete="CASCADE"), nullable=False),
        sa.Column("report_name", sa.String(length=120), nullable=True),
        sa.Column("report_config_snapshot", sa.Text(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_accessed_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_shared_report_links_token", "shared_report_links", ["token"], unique=True)
    op.create_index("ix_shared_report_links_saved_view_id", "shared_report_links", ["saved_view_id"])
    op.create_index("ix_shared_report_links_created_by_id", "shared_report_links", ["created_by_id"])
    op.create_index("ix_shared_report_links_expires_at", "shared_report_links", ["expires_at"])
    op.create_index("ix_shared_report_links_is_active", "shared_report_links", ["is_active"])


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if "shared_report_links" not in inspector.get_table_names():
        return
    op.drop_index("ix_shared_report_links_is_active", table_name="shared_report_links")
    op.drop_index("ix_shared_report_links_expires_at", table_name="shared_report_links")
    op.drop_index("ix_shared_report_links_created_by_id", table_name="shared_report_links")
    op.drop_index("ix_shared_report_links_saved_view_id", table_name="shared_report_links")
    op.drop_index("ix_shared_report_links_token", table_name="shared_report_links")
    op.drop_table("shared_report_links")
