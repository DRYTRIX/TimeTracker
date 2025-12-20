"""add integration external event links

Revision ID: 091_add_integration_external_event_links
Revises: 090_report_builder_iteration
Create Date: 2025-12-20
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "091_add_integration_external_event_links"
down_revision = "090_report_builder_iteration"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "integration_external_event_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("integration_id", sa.Integer(), sa.ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("time_entry_id", sa.Integer(), sa.ForeignKey("time_entries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_uid", sa.String(length=255), nullable=False),
        sa.Column("external_href", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("integration_id", "external_uid", name="uq_integration_external_uid"),
    )
    op.create_index(
        "ix_integration_external_event_links_integration_id",
        "integration_external_event_links",
        ["integration_id"],
    )
    op.create_index(
        "ix_integration_external_event_links_time_entry_id",
        "integration_external_event_links",
        ["time_entry_id"],
    )
    op.create_index(
        "ix_integration_external_event_links_external_uid",
        "integration_external_event_links",
        ["external_uid"],
    )


def downgrade():
    op.drop_index("ix_integration_external_event_links_external_uid", table_name="integration_external_event_links")
    op.drop_index("ix_integration_external_event_links_time_entry_id", table_name="integration_external_event_links")
    op.drop_index("ix_integration_external_event_links_integration_id", table_name="integration_external_event_links")
    op.drop_table("integration_external_event_links")


