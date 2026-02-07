"""User nullable date_format and time_format (use system default)

Revision ID: 120_user_nullable_date_time_format
Revises: 119_add_settings_date_time_format
Create Date: 2026-02-07

Makes users.date_format and users.time_format nullable so users can choose
"Use system default"; when null, resolution uses system settings.
"""
from alembic import op
import sqlalchemy as sa


revision = "120_user_nullable_date_time_format"
down_revision = "119_add_settings_date_time_format"
branch_labels = None
depends_on = None


def upgrade():
    """Allow users.date_format and users.time_format to be NULL."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "users" not in inspector.get_table_names():
        return

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column(
            "date_format",
            existing_type=sa.String(20),
            nullable=True,
        )
        batch_op.alter_column(
            "time_format",
            existing_type=sa.String(10),
            nullable=True,
        )


def downgrade():
    """Restore non-null with server default for users.date_format and time_format."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "users" not in inspector.get_table_names():
        return

    # Set NULLs to default before making column non-null
    op.execute(sa.text("UPDATE users SET date_format = 'YYYY-MM-DD' WHERE date_format IS NULL"))
    op.execute(sa.text("UPDATE users SET time_format = '24h' WHERE time_format IS NULL"))

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column(
            "date_format",
            existing_type=sa.String(20),
            nullable=False,
            server_default="YYYY-MM-DD",
        )
        batch_op.alter_column(
            "time_format",
            existing_type=sa.String(10),
            nullable=False,
            server_default="24h",
        )
