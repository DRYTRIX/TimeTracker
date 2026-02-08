"""Add donate_ui_hidden to settings (system-wide hide donate UI)

Revision ID: 122_add_settings_donate_ui_hidden
Revises: 121_add_ui_show_donate_system_id
Create Date: 2026-02-08

When True, donate/support UI is hidden for all users (verified in Admin).
"""
from alembic import op
import sqlalchemy as sa


revision = "122_add_settings_donate_ui_hidden"
down_revision = "121_add_ui_show_donate_system_id"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "settings" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("settings")}
    if "donate_ui_hidden" in cols:
        return
    dialect_name = getattr(bind.dialect, "name", "generic")
    bool_false = "0" if dialect_name == "sqlite" else "false"
    op.add_column(
        "settings",
        sa.Column("donate_ui_hidden", sa.Boolean(), nullable=False, server_default=sa.text(bool_false)),
    )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "settings" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("settings")}
    if "donate_ui_hidden" not in cols:
        return
    op.drop_column("settings", "donate_ui_hidden")
