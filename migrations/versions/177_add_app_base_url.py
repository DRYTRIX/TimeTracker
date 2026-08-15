"""Add app_base_url for absolute email/notification links.

Revision ID: 177_add_app_base_url
Revises: 176_add_global_rounding_policy
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "177_add_app_base_url"
down_revision = "176_add_global_rounding_policy"
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
    if not _has_column(inspector, "settings", "app_base_url"):
        op.add_column(
            "settings",
            sa.Column(
                "app_base_url",
                sa.String(500),
                nullable=True,
                server_default="",
            ),
        )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if _has_column(inspector, "settings", "app_base_url"):
        op.drop_column("settings", "app_base_url")
