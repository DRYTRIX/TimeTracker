"""Add date_format and time_format to settings

Revision ID: 119_add_settings_date_time_format
Revises: 118_add_locked_client_id
Create Date: 2026-02-06

Adds settings.date_format and settings.time_format columns so admins can
configure the system-wide default date/time display format.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "119_add_settings_date_time_format"
down_revision = "118_add_locked_client_id"
branch_labels = None
depends_on = None


def upgrade():
    """Add date_format and time_format columns to settings table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "settings" not in inspector.get_table_names():
        return

    settings_cols = {c["name"] for c in inspector.get_columns("settings")}

    if "date_format" not in settings_cols:
        op.add_column(
            "settings",
            sa.Column(
                "date_format",
                sa.String(20),
                nullable=False,
                server_default="YYYY-MM-DD",
            ),
        )

    if "time_format" not in settings_cols:
        op.add_column(
            "settings",
            sa.Column(
                "time_format",
                sa.String(10),
                nullable=False,
                server_default="24h",
            ),
        )


def downgrade():
    """Remove date_format and time_format from settings table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    is_sqlite = bind.dialect.name == "sqlite"

    if "settings" not in inspector.get_table_names():
        return

    settings_cols = {c["name"] for c in inspector.get_columns("settings")}

    cols_to_drop = [c for c in ("date_format", "time_format") if c in settings_cols]
    if not cols_to_drop:
        return

    if is_sqlite:
        with op.batch_alter_table("settings", schema=None) as batch_op:
            for col in cols_to_drop:
                batch_op.drop_column(col)
    else:
        for col in cols_to_drop:
            op.drop_column("settings", col)
