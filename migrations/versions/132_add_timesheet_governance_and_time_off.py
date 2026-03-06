"""Add timesheet governance, time-off and policy tables

Revision ID: 132_add_timesheet_governance_and_time_off
Revises: 131_add_donation_variant
Create Date: 2026-03-05
"""

from alembic import op
import sqlalchemy as sa


revision = "132_add_timesheet_governance_and_time_off"
down_revision = "131_add_donation_variant"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "timesheet_periods" not in existing:
        op.create_table(
            "timesheet_periods",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("period_type", sa.String(length=20), nullable=False, server_default="weekly"),
            sa.Column("period_start", sa.Date(), nullable=False),
            sa.Column("period_end", sa.Date(), nullable=False),
            sa.Column(
                "status",
                sa.Enum("draft", "submitted", "approved", "rejected", "closed", name="timesheetperiodstatus"),
                nullable=False,
                server_default="draft",
            ),
            sa.Column("submitted_at", sa.DateTime(), nullable=True),
            sa.Column("submitted_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.Column("approved_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("rejected_at", sa.DateTime(), nullable=True),
            sa.Column("rejected_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("rejection_reason", sa.Text(), nullable=True),
            sa.Column("closed_at", sa.DateTime(), nullable=True),
            sa.Column("closed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("close_reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("user_id", "period_type", "period_start", "period_end", name="uq_timesheet_period_user_range"),
        )
        op.create_index("ix_timesheet_period_user_status", "timesheet_periods", ["user_id", "status"], unique=False)

    if "leave_types" not in existing:
        op.create_table(
            "leave_types",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("code", sa.String(length=40), nullable=False),
            sa.Column("is_paid", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("annual_allowance_hours", sa.Numeric(10, 2), nullable=True),
            sa.Column("accrual_hours_per_month", sa.Numeric(10, 2), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("code", name="uq_leave_types_code"),
        )

    if "time_off_requests" not in existing:
        op.create_table(
            "time_off_requests",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("leave_type_id", sa.Integer(), sa.ForeignKey("leave_types.id"), nullable=False),
            sa.Column("start_date", sa.Date(), nullable=False),
            sa.Column("end_date", sa.Date(), nullable=False),
            sa.Column("start_half_day", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("end_half_day", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("requested_hours", sa.Numeric(10, 2), nullable=True),
            sa.Column(
                "status",
                sa.Enum("draft", "submitted", "approved", "rejected", "cancelled", name="timeoffrequeststatus"),
                nullable=False,
                server_default="draft",
            ),
            sa.Column("requested_comment", sa.Text(), nullable=True),
            sa.Column("review_comment", sa.Text(), nullable=True),
            sa.Column("submitted_at", sa.DateTime(), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(), nullable=True),
            sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_time_off_user_status_dates", "time_off_requests", ["user_id", "status", "start_date", "end_date"], unique=False)

    if "company_holidays" not in existing:
        op.create_table(
            "company_holidays",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("start_date", sa.Date(), nullable=False),
            sa.Column("end_date", sa.Date(), nullable=False),
            sa.Column("region", sa.String(length=50), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    if "timesheet_policies" not in existing:
        op.create_table(
            "timesheet_policies",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("default_period_type", sa.String(length=20), nullable=False, server_default="weekly"),
            sa.Column("auto_lock_days", sa.Integer(), nullable=True),
            sa.Column("approver_user_ids", sa.String(length=1000), nullable=True),
            sa.Column("enable_multi_level_approval", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("require_rejection_comment", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("enable_admin_override", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "timesheet_policies" in existing:
        op.drop_table("timesheet_policies")
    if "company_holidays" in existing:
        op.drop_table("company_holidays")
    if "time_off_requests" in existing:
        op.drop_index("ix_time_off_user_status_dates", table_name="time_off_requests")
        op.drop_table("time_off_requests")
    if "leave_types" in existing:
        op.drop_table("leave_types")
    if "timesheet_periods" in existing:
        op.drop_index("ix_timesheet_period_user_status", table_name="timesheet_periods")
        op.drop_table("timesheet_periods")

    try:
        op.execute("DROP TYPE IF EXISTS timeoffrequeststatus")
    except Exception:
        pass
    try:
        op.execute("DROP TYPE IF EXISTS timesheetperiodstatus")
    except Exception:
        pass
