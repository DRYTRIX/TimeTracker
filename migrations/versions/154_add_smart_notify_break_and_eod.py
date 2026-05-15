"""Smart notifications: break reminder + end-of-day reminder preferences.

Adds four columns to the users table and widens the local_date column on
user_smart_notification_dismissals so that internal bucket markers (used to
fire the break reminder once per interval) fit alongside regular YYYY-MM-DD
dismissals.

Revision ID: 154_add_smart_notify_break_and_eod
Revises: 153_add_user_auth_provider
Create Date: 2026-05-15
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "154_add_smart_notify_break_and_eod"
down_revision = "153_add_user_auth_provider"
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    try:
        return column_name in {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return False


def _column_length(inspector, table_name: str, column_name: str):
    try:
        for c in inspector.get_columns(table_name):
            if c["name"] == column_name:
                t = c.get("type")
                return getattr(t, "length", None)
    except Exception:
        return None
    return None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    if "users" in inspector.get_table_names():
        if not _has_column(inspector, "users", "smart_notify_break_reminder"):
            op.add_column(
                "users",
                sa.Column("smart_notify_break_reminder", sa.Boolean(), nullable=False, server_default="0"),
            )
        if not _has_column(inspector, "users", "smart_notify_break_interval_minutes"):
            op.add_column(
                "users",
                sa.Column(
                    "smart_notify_break_interval_minutes",
                    sa.Integer(),
                    nullable=False,
                    server_default="60",
                ),
            )
        if not _has_column(inspector, "users", "smart_notify_end_of_day"):
            op.add_column(
                "users",
                sa.Column("smart_notify_end_of_day", sa.Boolean(), nullable=False, server_default="0"),
            )
        if not _has_column(inspector, "users", "smart_notify_end_of_day_time"):
            op.add_column(
                "users",
                sa.Column("smart_notify_end_of_day_time", sa.String(length=5), nullable=True),
            )

        # Drop the server_defaults now that existing rows are backfilled
        for col in (
            "smart_notify_break_reminder",
            "smart_notify_break_interval_minutes",
            "smart_notify_end_of_day",
        ):
            try:
                op.alter_column("users", col, server_default=None)
            except Exception:
                pass

    # Widen local_date on user_smart_notification_dismissals to fit bucket markers
    # like "break_<timer_id>_<bucket>" used by KIND_BREAK_REMINDER.
    if "user_smart_notification_dismissals" in inspector.get_table_names():
        current_len = _column_length(inspector, "user_smart_notification_dismissals", "local_date")
        if current_len is None or current_len < 64:
            try:
                op.alter_column(
                    "user_smart_notification_dismissals",
                    "local_date",
                    existing_type=sa.String(length=current_len or 10),
                    type_=sa.String(length=64),
                    existing_nullable=False,
                )
            except Exception:
                # SQLite or other backends may not support alter; recreate as fallback
                with op.batch_alter_table("user_smart_notification_dismissals") as batch_op:
                    batch_op.alter_column(
                        "local_date",
                        existing_type=sa.String(length=current_len or 10),
                        type_=sa.String(length=64),
                        existing_nullable=False,
                    )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    if "user_smart_notification_dismissals" in inspector.get_table_names():
        current_len = _column_length(inspector, "user_smart_notification_dismissals", "local_date")
        if current_len and current_len > 10:
            try:
                op.alter_column(
                    "user_smart_notification_dismissals",
                    "local_date",
                    existing_type=sa.String(length=current_len),
                    type_=sa.String(length=10),
                    existing_nullable=False,
                )
            except Exception:
                with op.batch_alter_table("user_smart_notification_dismissals") as batch_op:
                    batch_op.alter_column(
                        "local_date",
                        existing_type=sa.String(length=current_len),
                        type_=sa.String(length=10),
                        existing_nullable=False,
                    )

    if "users" not in inspector.get_table_names():
        return
    for name in (
        "smart_notify_end_of_day_time",
        "smart_notify_end_of_day",
        "smart_notify_break_interval_minutes",
        "smart_notify_break_reminder",
    ):
        if _has_column(inspector, "users", name):
            op.drop_column("users", name)
