"""Add global rounding method, minimum duration, and enforce-all-users flag.

Revision ID: 176_add_global_rounding_policy
Revises: 175_add_rounding_boundary_and_minimum
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "176_add_global_rounding_policy"
down_revision = "175_add_rounding_boundary_and_minimum"
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
    if not _has_column(inspector, "settings", "rounding_method"):
        op.add_column(
            "settings",
            sa.Column(
                "rounding_method",
                sa.String(10),
                nullable=False,
                server_default="nearest",
            ),
        )
    if not _has_column(inspector, "settings", "rounding_minimum_minutes"):
        op.add_column(
            "settings",
            sa.Column(
                "rounding_minimum_minutes",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )
    if not _has_column(inspector, "settings", "rounding_enforce_global"):
        op.add_column(
            "settings",
            sa.Column(
                "rounding_enforce_global",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    for col in (
        "rounding_enforce_global",
        "rounding_minimum_minutes",
        "rounding_method",
    ):
        if _has_column(inspector, "settings", col):
            op.drop_column("settings", col)
