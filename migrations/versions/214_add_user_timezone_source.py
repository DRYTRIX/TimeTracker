"""Add users.timezone_source to distinguish auto-detected vs. manually pinned timezones.

Revision ID: 214_add_user_timezone_source
Revises: 212_credit_notes_extended
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "214_add_user_timezone_source"
down_revision = "213_crm_communication_templates"
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

    if not _has_column(inspector, "users", "timezone_source"):
        op.add_column(
            "users",
            sa.Column("timezone_source", sa.String(length=10), nullable=False, server_default="auto"),
        )

    # Users who explicitly picked a timezone keep it: they pinned it manually.
    op.execute("UPDATE users SET timezone_source = 'manual' WHERE timezone IS NOT NULL")


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    if _has_column(inspector, "users", "timezone_source"):
        op.drop_column("users", "timezone_source")
