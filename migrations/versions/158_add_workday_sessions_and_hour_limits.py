"""Add workday sessions, working time violations, and hour limit settings.

Revision ID: 158_add_workday_sessions_and_hour_limits
Revises: 157_add_project_client_created_by
Create Date: 2026-05-25
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "158_add_workday_sessions_and_hour_limits"
down_revision = "157_add_project_client_created_by"
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    try:
        return column_name in {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return False


def _has_table(inspector, table_name: str) -> bool:
    try:
        return table_name in inspector.get_table_names()
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    if not _has_table(inspector, "workday_sessions"):
        op.create_table(
            "workday_sessions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("start_time", sa.DateTime(), nullable=False),
            sa.Column("end_time", sa.DateTime(), nullable=True),
            sa.Column("duration_seconds", sa.Integer(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("auto_closed", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("source", sa.String(length=20), nullable=False, server_default="manual"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_workday_sessions_user_id", "workday_sessions", ["user_id"])
        op.create_index("ix_workday_sessions_start_time", "workday_sessions", ["start_time"])
        op.create_index("ix_workday_sessions_end_time", "workday_sessions", ["end_time"])

    if not _has_table(inspector, "working_time_violations"):
        op.create_table(
            "working_time_violations",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("period_type", sa.String(length=10), nullable=False),
            sa.Column("period_start", sa.Date(), nullable=False),
            sa.Column("period_end", sa.Date(), nullable=False),
            sa.Column("limit_hours", sa.Float(), nullable=False),
            sa.Column("actual_hours", sa.Float(), nullable=False),
            sa.Column("hours_over", sa.Float(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
            sa.Column("justification", sa.Text(), nullable=True),
            sa.Column("justification_submitted_at", sa.DateTime(), nullable=True),
            sa.Column("acknowledged_by_user_id", sa.Integer(), nullable=True),
            sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
            sa.Column("notified_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["acknowledged_by_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "period_type", "period_start", name="uq_working_time_violation_period"),
        )
        op.create_index("ix_working_time_violations_user_id", "working_time_violations", ["user_id"])
        op.create_index("ix_working_time_violations_period_start", "working_time_violations", ["period_start"])

    if "settings" in inspector.get_table_names():
        if not _has_column(inspector, "settings", "daily_hour_limit"):
            op.add_column("settings", sa.Column("daily_hour_limit", sa.Float(), nullable=False, server_default="10"))
        if not _has_column(inspector, "settings", "weekly_hour_limit"):
            op.add_column("settings", sa.Column("weekly_hour_limit", sa.Float(), nullable=False, server_default="48"))
        if not _has_column(inspector, "settings", "hour_limit_enforcement"):
            op.add_column(
                "settings",
                sa.Column("hour_limit_enforcement", sa.String(length=20), nullable=False, server_default="soft_email"),
            )
        if not _has_column(inspector, "settings", "hour_limit_email_enabled"):
            op.add_column(
                "settings",
                sa.Column("hour_limit_email_enabled", sa.Boolean(), nullable=False, server_default="1"),
            )
        if not _has_column(inspector, "settings", "hour_limits_enabled"):
            op.add_column(
                "settings",
                sa.Column("hour_limits_enabled", sa.Boolean(), nullable=False, server_default="1"),
            )

    if "users" in inspector.get_table_names():
        if not _has_column(inspector, "users", "daily_hour_limit_override"):
            op.add_column("users", sa.Column("daily_hour_limit_override", sa.Float(), nullable=True))
        if not _has_column(inspector, "users", "weekly_hour_limit_override"):
            op.add_column("users", sa.Column("weekly_hour_limit_override", sa.Float(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    for col in ("daily_hour_limit_override", "weekly_hour_limit_override"):
        if "users" in inspector.get_table_names() and _has_column(inspector, "users", col):
            op.drop_column("users", col)

    for col in ("hour_limits_enabled", "hour_limit_email_enabled", "hour_limit_enforcement", "weekly_hour_limit", "daily_hour_limit"):
        if "settings" in inspector.get_table_names() and _has_column(inspector, "settings", col):
            op.drop_column("settings", col)

    if _has_table(inspector, "working_time_violations"):
        op.drop_table("working_time_violations")
    if _has_table(inspector, "workday_sessions"):
        op.drop_table("workday_sessions")
