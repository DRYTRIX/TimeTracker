"""Add recurring project costs table.

Revision ID: 189_add_recurring_project_costs
Revises: 188_add_activitywatch_rules
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "189_add_recurring_project_costs"
down_revision = "188_add_activitywatch_rules"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if "recurring_project_costs" in inspector.get_table_names():
        return

    op.create_table(
        "recurring_project_costs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("billable", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("currency_code", sa.String(length=3), nullable=False, server_default="EUR"),
        sa.Column("frequency", sa.String(length=20), nullable=False),
        sa.Column("interval", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("next_run_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_generated_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_recurring_project_costs_project_id", "recurring_project_costs", ["project_id"])
    op.create_index("ix_recurring_project_costs_user_id", "recurring_project_costs", ["user_id"])
    op.create_index("ix_recurring_project_costs_next_run_date", "recurring_project_costs", ["next_run_date"])
    op.create_index("ix_recurring_project_costs_is_active", "recurring_project_costs", ["is_active"])


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if "recurring_project_costs" not in inspector.get_table_names():
        return
    op.drop_index("ix_recurring_project_costs_is_active", table_name="recurring_project_costs")
    op.drop_index("ix_recurring_project_costs_next_run_date", table_name="recurring_project_costs")
    op.drop_index("ix_recurring_project_costs_user_id", table_name="recurring_project_costs")
    op.drop_index("ix_recurring_project_costs_project_id", table_name="recurring_project_costs")
    op.drop_table("recurring_project_costs")
