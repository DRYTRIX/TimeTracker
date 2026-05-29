"""Add quote numbering settings

Revision ID: 159_add_quote_number_settings
Revises: 158_add_workday_sessions_and_hour_limits
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa


revision = "159_add_quote_number_settings"
down_revision = "158_add_workday_sessions_and_hour_limits"
branch_labels = None
depends_on = None

DEFAULT_QUOTE_PATTERN = "{PREFIX}-{YYYY}{MM}{DD}-{SEQ}"


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("settings")} if "settings" in inspector.get_table_names() else set()

    if "quote_prefix" not in columns:
        op.add_column(
            "settings",
            sa.Column("quote_prefix", sa.String(length=50), nullable=False, server_default="QUO"),
        )
    if "quote_number_pattern" not in columns:
        op.add_column(
            "settings",
            sa.Column(
                "quote_number_pattern",
                sa.String(length=120),
                nullable=False,
                server_default=DEFAULT_QUOTE_PATTERN,
            ),
        )
    if "quote_start_number" not in columns:
        op.add_column(
            "settings",
            sa.Column("quote_start_number", sa.Integer(), nullable=False, server_default="1"),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("settings")} if "settings" in inspector.get_table_names() else set()

    if "quote_start_number" in columns:
        op.drop_column("settings", "quote_start_number")
    if "quote_number_pattern" in columns:
        op.drop_column("settings", "quote_number_pattern")
    if "quote_prefix" in columns:
        op.drop_column("settings", "quote_prefix")
