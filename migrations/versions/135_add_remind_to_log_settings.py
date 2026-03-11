"""Add notification_remind_to_log and reminder_to_log_time to users

Revision ID: 135_remind_to_log
Revises: 134_overtime_weekly
Create Date: 2026-03-11

Adds user settings for optional end-of-day reminder to log time.
"""
from alembic import op
import sqlalchemy as sa


revision = "135_remind_to_log"
down_revision = "134_overtime_weekly"
branch_labels = None
depends_on = None


def upgrade():
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)
    if "users" not in inspector.get_table_names():
        return
    users_columns = {c["name"] for c in inspector.get_columns("users")}

    if "notification_remind_to_log" not in users_columns:
        op.add_column(
            "users",
            sa.Column(
                "notification_remind_to_log",
                sa.Boolean(),
                nullable=False,
                server_default="0",
            ),
        )
    if "reminder_to_log_time" not in users_columns:
        op.add_column(
            "users",
            sa.Column("reminder_to_log_time", sa.String(5), nullable=True),
        )


def downgrade():
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)
    if "users" not in inspector.get_table_names():
        return
    users_columns = {c["name"] for c in inspector.get_columns("users")}

    if "reminder_to_log_time" in users_columns:
        op.drop_column("users", "reminder_to_log_time")
    if "notification_remind_to_log" in users_columns:
        op.drop_column("users", "notification_remind_to_log")
