"""Add payroll_export_templates table.

Revision ID: 186_add_payroll_export_templates
Revises: 185_add_pomodoro_user_defaults
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "186_add_payroll_export_templates"
down_revision = "185_add_pomodoro_user_defaults"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if "payroll_export_templates" not in inspector.get_table_names():
        op.create_table(
            "payroll_export_templates",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=120), nullable=False, unique=True),
            sa.Column("columns", sa.JSON(), nullable=False),
            sa.Column("grouping", sa.String(length=20), nullable=False, server_default="week"),
            sa.Column("filters", sa.JSON(), nullable=True),
            sa.Column("format", sa.String(length=10), nullable=False, server_default="csv"),
            sa.Column("delimiter", sa.String(length=5), nullable=False, server_default=","),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if "payroll_export_templates" in inspector.get_table_names():
        op.drop_table("payroll_export_templates")
