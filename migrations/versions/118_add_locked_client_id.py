"""Add locked_client_id to settings

Revision ID: 118_add_locked_client_id
Revises: 117_add_user_calendar_type_colors
Create Date: 2026-02-02

Adds settings.locked_client_id (nullable int) to allow locking the app to a single client.
"""
from alembic import op
import sqlalchemy as sa


revision = "118_add_locked_client_id"
down_revision = "117_add_user_calendar_type_colors"
branch_labels = None
depends_on = None


def upgrade():
    """Add locked_client_id (nullable int) to settings table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "settings" not in inspector.get_table_names():
        return

    settings_cols = {c["name"] for c in inspector.get_columns("settings")}
    if "locked_client_id" in settings_cols:
        return

    op.add_column(
        "settings",
        sa.Column("locked_client_id", sa.Integer(), nullable=True),
    )


def downgrade():
    """Remove locked_client_id from settings table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    is_sqlite = bind.dialect.name == "sqlite"

    if "settings" not in inspector.get_table_names():
        return

    settings_cols = {c["name"] for c in inspector.get_columns("settings")}
    if "locked_client_id" not in settings_cols:
        return

    if is_sqlite:
        with op.batch_alter_table("settings", schema=None) as batch_op:
            batch_op.drop_column("locked_client_id")
    else:
        op.drop_column("settings", "locked_client_id")

