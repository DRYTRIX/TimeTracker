"""Add AI routing strategy setting for OrcaRouter.

Revision ID: 192_add_ai_routing_strategy
Revises: 191_add_geofences
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "192_add_ai_routing_strategy"
down_revision = "191_add_geofences"
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
    if "settings" not in inspector.get_table_names():
        return
    if not _has_column(inspector, "settings", "ai_routing_strategy"):
        op.add_column("settings", sa.Column("ai_routing_strategy", sa.String(length=20), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if "settings" not in inspector.get_table_names():
        return
    if _has_column(inspector, "settings", "ai_routing_strategy"):
        op.drop_column("settings", "ai_routing_strategy")
