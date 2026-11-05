"""add missing columns for settings and time_entries

Revision ID: 005
Revises: 004
Create Date: 2025-09-08 16:30:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Existing columns per table
    settings_cols = {c["name"] for c in inspector.get_columns("settings")}
    time_entries_cols = {c["name"] for c in inspector.get_columns("time_entries")}

    # Add columns to settings if missing
    to_add_settings = []
    if "backup_retention_days" not in settings_cols:
        to_add_settings.append(sa.Column("backup_retention_days", sa.Integer(), nullable=False, server_default="30"))
    if "backup_time" not in settings_cols:
        to_add_settings.append(sa.Column("backup_time", sa.String(length=5), nullable=False, server_default="02:00"))
    if "export_delimiter" not in settings_cols:
        to_add_settings.append(sa.Column("export_delimiter", sa.String(length=1), nullable=False, server_default=","))

    if to_add_settings:
        with op.batch_alter_table("settings") as batch_op:
            for col in to_add_settings:
                batch_op.add_column(col)

    # Add column to time_entries if missing
    if "duration_seconds" not in time_entries_cols:
        with op.batch_alter_table("time_entries") as batch_op:
            batch_op.add_column(sa.Column("duration_seconds", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("time_entries") as batch_op:
        batch_op.drop_column("duration_seconds")

    with op.batch_alter_table("settings") as batch_op:
        batch_op.drop_column("export_delimiter")
        batch_op.drop_column("backup_time")
        batch_op.drop_column("backup_retention_days")
