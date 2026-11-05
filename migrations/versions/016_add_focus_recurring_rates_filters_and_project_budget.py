"""add focus sessions, recurring blocks, rate overrides, saved filters, and project budget fields

Revision ID: 016
Revises: 015
Create Date: 2025-10-06 00:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_tables = set(inspector.get_table_names())

    # projects: add estimates/budget fields if missing
    if "projects" in existing_tables:
        cols = {c["name"] for c in inspector.get_columns("projects")}
        with op.batch_alter_table("projects") as batch:
            if "estimated_hours" not in cols:
                batch.add_column(sa.Column("estimated_hours", sa.Float(), nullable=True))
            if "budget_amount" not in cols:
                batch.add_column(sa.Column("budget_amount", sa.Numeric(10, 2), nullable=True))
            if "budget_threshold_percent" not in cols:
                batch.add_column(
                    sa.Column("budget_threshold_percent", sa.Integer(), nullable=False, server_default="80")
                )

    # focus_sessions table
    if "focus_sessions" not in existing_tables:
        op.create_table(
            "focus_sessions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
            sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=True, index=True),
            sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id"), nullable=True, index=True),
            sa.Column("time_entry_id", sa.Integer(), sa.ForeignKey("time_entries.id"), nullable=True, index=True),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("ended_at", sa.DateTime(), nullable=True),
            sa.Column("pomodoro_length", sa.Integer(), nullable=False, server_default="25"),
            sa.Column("short_break_length", sa.Integer(), nullable=False, server_default="5"),
            sa.Column("long_break_length", sa.Integer(), nullable=False, server_default="15"),
            sa.Column("long_break_interval", sa.Integer(), nullable=False, server_default="4"),
            sa.Column("cycles_completed", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("interruptions", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )

    # recurring_blocks table
    if "recurring_blocks" not in existing_tables:
        op.create_table(
            "recurring_blocks",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
            sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False, index=True),
            sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id"), nullable=True, index=True),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("recurrence", sa.String(length=20), nullable=False, server_default="weekly"),
            sa.Column("weekdays", sa.String(length=50), nullable=True),
            sa.Column("start_time_local", sa.String(length=5), nullable=False),
            sa.Column("end_time_local", sa.String(length=5), nullable=False),
            sa.Column("starts_on", sa.Date(), nullable=True),
            sa.Column("ends_on", sa.Date(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("tags", sa.String(length=500), nullable=True),
            sa.Column("billable", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
            sa.Column("last_generated_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )

    # rate_overrides table
    if "rate_overrides" not in existing_tables:
        op.create_table(
            "rate_overrides",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True, index=True),
            sa.Column("hourly_rate", sa.Numeric(9, 2), nullable=False),
            sa.Column("effective_from", sa.Date(), nullable=True),
            sa.Column("effective_to", sa.Date(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("project_id", "user_id", "effective_from", name="ux_rate_override_unique_window"),
        )

    # saved_filters table
    if "saved_filters" not in existing_tables:
        op.create_table(
            "saved_filters",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("scope", sa.String(length=50), nullable=False, server_default="global"),
            sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("is_shared", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("user_id", "name", "scope", name="ux_saved_filter_user_name_scope"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "saved_filters" in existing_tables:
        op.drop_table("saved_filters")
    if "rate_overrides" in existing_tables:
        op.drop_table("rate_overrides")
    if "recurring_blocks" in existing_tables:
        op.drop_table("recurring_blocks")
    if "focus_sessions" in existing_tables:
        op.drop_table("focus_sessions")

    if "projects" in existing_tables:
        cols = {c["name"] for c in inspector.get_columns("projects")}
        with op.batch_alter_table("projects") as batch:
            if "budget_threshold_percent" in cols:
                batch.drop_column("budget_threshold_percent")
            if "budget_amount" in cols:
                batch.drop_column("budget_amount")
            if "estimated_hours" in cols:
                batch.drop_column("estimated_hours")
