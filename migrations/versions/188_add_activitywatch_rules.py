"""Add ActivityWatch rules and pending activities tables.

Revision ID: 188_add_activitywatch_rules
Revises: 187_add_integration_sync_errors
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "188_add_activitywatch_rules"
down_revision = "187_add_integration_sync_errors"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = inspector.get_table_names()
    if "activitywatch_rules" not in tables:
        op.create_table(
            "activitywatch_rules",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("pattern_type", sa.String(30), nullable=False, server_default="app"),
            sa.Column("pattern_value", sa.String(500), nullable=False),
            sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=True),
            sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id"), nullable=True),
            sa.Column("tags", sa.JSON(), nullable=True),
            sa.Column("billable", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("min_duration_seconds", sa.Integer(), nullable=True),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_activitywatch_rules_user_id", "activitywatch_rules", ["user_id"])
    if "pending_activities" not in tables:
        op.create_table(
            "pending_activities",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("aw_bucket", sa.String(255), nullable=True),
            sa.Column("app_name", sa.String(255), nullable=True),
            sa.Column("title", sa.String(500), nullable=True),
            sa.Column("url", sa.String(1000), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("matched_rule_id", sa.Integer(), sa.ForeignKey("activitywatch_rules.id"), nullable=True),
            sa.Column("suggested_project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=True),
            sa.Column("suggested_task_id", sa.Integer(), sa.ForeignKey("tasks.id"), nullable=True),
            sa.Column("suggested_billable", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("external_uid", sa.String(255), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_pending_activities_user_id", "pending_activities", ["user_id"])
        op.create_index("ix_pending_activities_status", "pending_activities", ["status"])


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = inspector.get_table_names()
    if "pending_activities" in tables:
        op.drop_table("pending_activities")
    if "activitywatch_rules" in tables:
        op.drop_table("activitywatch_rules")
