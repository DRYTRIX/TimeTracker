"""Add boundary rounding support and per-user minimum billable duration.

Revision ID: 175_add_rounding_boundary_and_minimum
Revises: 174_add_timer_idle_heartbeat
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "175_add_rounding_boundary_and_minimum"
down_revision = "174_add_timer_idle_heartbeat"
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
    if not _has_column(inspector, "users", "time_rounding_minimum_minutes"):
        op.add_column(
            "users",
            sa.Column(
                "time_rounding_minimum_minutes",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if _has_column(inspector, "users", "time_rounding_minimum_minutes"):
        op.drop_column("users", "time_rounding_minimum_minutes")
