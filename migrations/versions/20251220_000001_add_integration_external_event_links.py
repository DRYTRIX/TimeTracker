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


def _has_table(inspector, name: str) -> bool:
    """Check if a table exists"""
    try:
        return name in inspector.get_table_names()
    except Exception:
        return False


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    """Check if an index exists on a table"""
    try:
        # First check if table exists
        if table_name not in inspector.get_table_names():
            return False
        indexes = inspector.get_indexes(table_name)
        return any(idx['name'] == index_name for idx in indexes)
    except Exception:
        return False


def upgrade():
    # Import for checking table existence
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Create table only if it doesn't exist
    if not _has_table(inspector, "integration_external_event_links"):
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
    else:
        print("[Migration 091] ⚠ Table integration_external_event_links already exists, skipping creation")
    
    # Create indexes only if they don't exist
    table_name = "integration_external_event_links"
    
    if not _has_index(inspector, table_name, "ix_integration_external_event_links_integration_id"):
        op.create_index(
            "ix_integration_external_event_links_integration_id",
            table_name,
            ["integration_id"],
        )
    
    if not _has_index(inspector, table_name, "ix_integration_external_event_links_time_entry_id"):
        op.create_index(
            "ix_integration_external_event_links_time_entry_id",
            table_name,
            ["time_entry_id"],
        )
    
    if not _has_index(inspector, table_name, "ix_integration_external_event_links_external_uid"):
        op.create_index(
            "ix_integration_external_event_links_external_uid",
            table_name,
            ["external_uid"],
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    table_name = "integration_external_event_links"
    
    # Drop indexes only if they exist
    if _has_index(inspector, table_name, "ix_integration_external_event_links_external_uid"):
        op.drop_index("ix_integration_external_event_links_external_uid", table_name=table_name)
    
    if _has_index(inspector, table_name, "ix_integration_external_event_links_time_entry_id"):
        op.drop_index("ix_integration_external_event_links_time_entry_id", table_name=table_name)
    
    if _has_index(inspector, table_name, "ix_integration_external_event_links_integration_id"):
        op.drop_index("ix_integration_external_event_links_integration_id", table_name=table_name)
    
    # Drop table only if it exists
    if _has_table(inspector, table_name):
        op.drop_table(table_name)


