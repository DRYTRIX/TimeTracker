"""Add attendance compliance tables and Belgium 2027 settings.

Revision ID: 164_add_attendance_compliance
Revises: 163_deleted_usernames_and_portal_only
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision = "164_add_attendance_compliance"
down_revision = "163_deleted_usernames_and_portal_only"
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    try:
        return table_name in inspector.get_table_names()
    except Exception:
        return False


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    try:
        return column_name in {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    if not _has_table(inspector, "daily_attendance_records"):
        op.create_table(
            "daily_attendance_records",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("work_date", sa.Date(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="present"),
            sa.Column("time_off_request_id", sa.Integer(), nullable=True),
            sa.Column("leave_type_id", sa.Integer(), nullable=True),
            sa.Column("total_work_seconds", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_break_seconds", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("locked_at", sa.DateTime(), nullable=True),
            sa.Column("locked_by", sa.Integer(), nullable=True),
            sa.Column("timesheet_period_id", sa.Integer(), nullable=True),
            sa.Column("compliance_notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["time_off_request_id"], ["time_off_requests.id"]),
            sa.ForeignKeyConstraint(["leave_type_id"], ["leave_types.id"]),
            sa.ForeignKeyConstraint(["locked_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["timesheet_period_id"], ["timesheet_periods.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "work_date", name="uq_daily_attendance_user_date"),
        )
        op.create_index("ix_daily_attendance_user_date", "daily_attendance_records", ["user_id", "work_date"])
        op.create_index("ix_daily_attendance_records_user_id", "daily_attendance_records", ["user_id"])
        op.create_index("ix_daily_attendance_records_work_date", "daily_attendance_records", ["work_date"])

    if not _has_table(inspector, "attendance_work_periods"):
        op.create_table(
            "attendance_work_periods",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("attendance_day_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("start_time", sa.DateTime(), nullable=False),
            sa.Column("end_time", sa.DateTime(), nullable=True),
            sa.Column("duration_seconds", sa.Integer(), nullable=True),
            sa.Column("source", sa.String(length=20), nullable=False, server_default="manual"),
            sa.Column("auto_closed", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("workday_session_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["attendance_day_id"], ["daily_attendance_records.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["workday_session_id"], ["workday_sessions.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_attendance_work_periods_attendance_day_id", "attendance_work_periods", ["attendance_day_id"])
        op.create_index("ix_attendance_work_periods_user_id", "attendance_work_periods", ["user_id"])
        op.create_index("ix_attendance_work_periods_start_time", "attendance_work_periods", ["start_time"])

    if not _has_table(inspector, "attendance_breaks"):
        op.create_table(
            "attendance_breaks",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("attendance_day_id", sa.Integer(), nullable=False),
            sa.Column("work_period_id", sa.Integer(), nullable=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("start_time", sa.DateTime(), nullable=False),
            sa.Column("end_time", sa.DateTime(), nullable=True),
            sa.Column("duration_seconds", sa.Integer(), nullable=True),
            sa.Column("break_type", sa.String(length=20), nullable=False, server_default="rest"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["attendance_day_id"], ["daily_attendance_records.id"]),
            sa.ForeignKeyConstraint(["work_period_id"], ["attendance_work_periods.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_attendance_breaks_attendance_day_id", "attendance_breaks", ["attendance_day_id"])
        op.create_index("ix_attendance_breaks_user_id", "attendance_breaks", ["user_id"])

    if not _has_table(inspector, "attendance_corrections"):
        op.create_table(
            "attendance_corrections",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("attendance_day_id", sa.Integer(), nullable=False),
            sa.Column("entity_type", sa.String(length=50), nullable=False),
            sa.Column("entity_id", sa.Integer(), nullable=False),
            sa.Column("original_values", sa.JSON(), nullable=True),
            sa.Column("corrected_values", sa.JSON(), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
            sa.Column("requested_by", sa.Integer(), nullable=False),
            sa.Column("reviewed_by", sa.Integer(), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(), nullable=True),
            sa.Column("review_comment", sa.Text(), nullable=True),
            sa.Column("applied_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["attendance_day_id"], ["daily_attendance_records.id"]),
            sa.ForeignKeyConstraint(["requested_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_attendance_corrections_attendance_day_id", "attendance_corrections", ["attendance_day_id"])
        op.create_index("ix_attendance_corrections_status", "attendance_corrections", ["status"])

    if "settings" in inspector.get_table_names():
        settings_cols = [
            ("compliance_enabled", sa.Boolean(), "0"),
            ("compliance_jurisdiction_preset", sa.String(30), "custom"),
            ("compliance_standard_daily_hours", sa.Float(), "8"),
            ("compliance_standard_weekly_hours", sa.Float(), "38"),
            ("compliance_break_after_hours", sa.Float(), "6"),
            ("compliance_min_break_minutes", sa.Integer(), "15"),
            ("compliance_min_daily_rest_hours", sa.Float(), "11"),
            ("compliance_attendance_retention_years", sa.Integer(), "10"),
            ("compliance_require_workday_registration", sa.Boolean(), "0"),
            ("compliance_royal_decree_config", sa.JSON(), None),
        ]
        for col_name, col_type, default in settings_cols:
            if not _has_column(inspector, "settings", col_name):
                if default is None:
                    op.add_column("settings", sa.Column(col_name, col_type, nullable=True))
                elif isinstance(default, str):
                    op.add_column(
                        "settings",
                        sa.Column(col_name, col_type, nullable=False, server_default=default),
                    )
                else:
                    op.add_column(
                        "settings",
                        sa.Column(col_name, col_type, nullable=False, server_default=str(default)),
                    )

    if "users" in inspector.get_table_names():
        user_cols = [
            ("has_other_employers", sa.Boolean(), "0"),
            ("other_employers_note", sa.Text(), None),
            ("other_employers_declared_at", sa.DateTime(), None),
            ("compliance_jurisdiction_preset", sa.String(30), None),
            ("compliance_standard_daily_hours", sa.Float(), None),
            ("compliance_standard_weekly_hours", sa.Float(), None),
        ]
        for col_name, col_type, default in user_cols:
            if not _has_column(inspector, "users", col_name):
                if default is None:
                    op.add_column("users", sa.Column(col_name, col_type, nullable=True))
                else:
                    op.add_column(
                        "users",
                        sa.Column(col_name, col_type, nullable=False, server_default=default),
                    )

    # Backfill from existing workday_sessions
    if _has_table(inspector, "workday_sessions") and _has_table(inspector, "daily_attendance_records"):
        bind.execute(
            text(
                """
                INSERT INTO daily_attendance_records (
                    user_id, work_date, status, total_work_seconds, total_break_seconds,
                    created_at, updated_at
                )
                SELECT DISTINCT
                    ws.user_id,
                    DATE(ws.start_time),
                    'present',
                    0,
                    0,
                    MIN(COALESCE(ws.created_at, CURRENT_TIMESTAMP)),
                    MAX(COALESCE(ws.updated_at, CURRENT_TIMESTAMP))
                FROM workday_sessions ws
                WHERE NOT EXISTS (
                    SELECT 1 FROM daily_attendance_records dar
                    WHERE dar.user_id = ws.user_id AND dar.work_date = DATE(ws.start_time)
                )
                GROUP BY ws.user_id, DATE(ws.start_time)
                """
            )
        )
        bind.execute(
            text(
                """
                INSERT INTO attendance_work_periods (
                    attendance_day_id, user_id, start_time, end_time, duration_seconds,
                    source, auto_closed, notes, workday_session_id, created_at, updated_at
                )
                SELECT
                    dar.id,
                    ws.user_id,
                    ws.start_time,
                    ws.end_time,
                    ws.duration_seconds,
                    COALESCE(ws.source, 'manual'),
                    COALESCE(ws.auto_closed, 0),
                    ws.notes,
                    ws.id,
                    COALESCE(ws.created_at, CURRENT_TIMESTAMP),
                    COALESCE(ws.updated_at, CURRENT_TIMESTAMP)
                FROM workday_sessions ws
                JOIN daily_attendance_records dar
                    ON dar.user_id = ws.user_id AND dar.work_date = DATE(ws.start_time)
                WHERE NOT EXISTS (
                    SELECT 1 FROM attendance_work_periods awp
                    WHERE awp.workday_session_id = ws.id
                )
                """
            )
        )
        bind.execute(
            text(
                """
                UPDATE daily_attendance_records dar
                SET total_work_seconds = (
                    SELECT COALESCE(SUM(awp.duration_seconds), 0)
                    FROM attendance_work_periods awp
                    WHERE awp.attendance_day_id = dar.id
                )
                """
            )
        )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    for col in (
        "compliance_standard_weekly_hours",
        "compliance_standard_daily_hours",
        "compliance_jurisdiction_preset",
        "other_employers_declared_at",
        "other_employers_note",
        "has_other_employers",
    ):
        if "users" in inspector.get_table_names() and _has_column(inspector, "users", col):
            op.drop_column("users", col)

    for col in (
        "compliance_royal_decree_config",
        "compliance_require_workday_registration",
        "compliance_attendance_retention_years",
        "compliance_min_daily_rest_hours",
        "compliance_min_break_minutes",
        "compliance_break_after_hours",
        "compliance_standard_weekly_hours",
        "compliance_standard_daily_hours",
        "compliance_jurisdiction_preset",
        "compliance_enabled",
    ):
        if "settings" in inspector.get_table_names() and _has_column(inspector, "settings", col):
            op.drop_column("settings", col)

    for table in (
        "attendance_corrections",
        "attendance_breaks",
        "attendance_work_periods",
        "daily_attendance_records",
    ):
        if _has_table(inspector, table):
            op.drop_table(table)
