"""Add ui_show_donate to users and system_instance_id to settings

Revision ID: 121_add_ui_show_donate_system_id
Revises: 120_user_nullable_date_time_format
Create Date: 2026-02-08

Allows users to hide donate UI after verifying a code; system_instance_id
is a stable per-installation ID shown in settings for code requests.
"""
from alembic import op
import sqlalchemy as sa


revision = "121_add_ui_show_donate_system_id"
down_revision = "120_user_nullable_date_time_format"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    dialect_name = getattr(bind.dialect, "name", "generic")
    bool_true = "1" if dialect_name == "sqlite" else "true"

    if "users" in table_names:
        cols = {c["name"] for c in inspector.get_columns("users")}
        if "ui_show_donate" not in cols:
            op.add_column(
                "users",
                sa.Column("ui_show_donate", sa.Boolean(), nullable=False, server_default=sa.text(bool_true)),
            )

    if "settings" in table_names:
        cols = {c["name"] for c in inspector.get_columns("settings")}
        if "system_instance_id" not in cols:
            op.add_column(
                "settings",
                sa.Column("system_instance_id", sa.String(36), nullable=True),
            )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "users" in table_names:
        cols = {c["name"] for c in inspector.get_columns("users")}
        if "ui_show_donate" in cols:
            op.drop_column("users", "ui_show_donate")

    if "settings" in table_names:
        cols = {c["name"] for c in inspector.get_columns("settings")}
        if "system_instance_id" in cols:
            op.drop_column("settings", "system_instance_id")
