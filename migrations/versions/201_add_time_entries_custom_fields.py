"""Add custom_fields JSON to time_entries.

Revision ID: 201_add_time_entries_custom_fields
Revises: 200_scrub_sensitive_audit_log_values
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "201_add_time_entries_custom_fields"
down_revision = "200_scrub_sensitive_audit_log_values"
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    try:
        return column_name in [col["name"] for col in inspector.get_columns(table_name)]
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "time_entries" not in inspector.get_table_names():
        return
    if _has_column(inspector, "time_entries", "custom_fields"):
        return
    try:
        op.add_column(
            "time_entries",
            sa.Column("custom_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        )
    except Exception:
        op.add_column("time_entries", sa.Column("custom_fields", sa.JSON(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "time_entries" not in inspector.get_table_names():
        return
    if _has_column(inspector, "time_entries", "custom_fields"):
        op.drop_column("time_entries", "custom_fields")
