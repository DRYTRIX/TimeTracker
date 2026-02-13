"""Add overtime_include_weekends to users

Revision ID: 126_add_overtime_include_weekends
Revises: 125_add_default_daily_working_hours
Create Date: 2026-02-13

User preference: when False, weekend hours are always counted as overtime.
"""
from alembic import op
import sqlalchemy as sa

revision = "126_add_overtime_include_weekends"
down_revision = "125_add_default_daily_working_hours"
branch_labels = None
depends_on = None


def upgrade():
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)
    if "users" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("users")}
    if "overtime_include_weekends" in cols:
        return
    op.add_column(
        "users",
        sa.Column("overtime_include_weekends", sa.Boolean(), nullable=False, server_default="1"),
    )


def downgrade():
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)
    if "users" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("users")}
    if "overtime_include_weekends" not in cols:
        return
    op.drop_column("users", "overtime_include_weekends")
