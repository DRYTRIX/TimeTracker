"""Add overtime_calculation_mode and standard_hours_per_week (Issue #551)

Revision ID: 134_overtime_weekly
Revises: 133_merge_132_129_heads
Create Date: 2026-03-09

Allows overtime to be calculated by weekly hours instead of daily hours.
"""
from alembic import op
import sqlalchemy as sa


revision = "134_overtime_weekly"
down_revision = "133_merge_132_129_heads"
branch_labels = None
depends_on = None


def upgrade():
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)
    if "users" not in inspector.get_table_names():
        return
    users_columns = {c["name"] for c in inspector.get_columns("users")}

    if "overtime_calculation_mode" not in users_columns:
        op.add_column(
            "users",
            sa.Column(
                "overtime_calculation_mode",
                sa.String(10),
                nullable=False,
                server_default="daily",
            ),
        )
    if "standard_hours_per_week" not in users_columns:
        op.add_column(
            "users",
            sa.Column("standard_hours_per_week", sa.Float(), nullable=True),
        )


def downgrade():
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)
    if "users" not in inspector.get_table_names():
        return
    users_columns = {c["name"] for c in inspector.get_columns("users")}

    if "standard_hours_per_week" in users_columns:
        op.drop_column("users", "standard_hours_per_week")
    if "overtime_calculation_mode" in users_columns:
        op.drop_column("users", "overtime_calculation_mode")
