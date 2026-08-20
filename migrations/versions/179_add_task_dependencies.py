"""Add task_dependencies table.

Revision ID: 179_add_task_dependencies
Revises: 178_fix_approvalstatus_enum_case
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "179_add_task_dependencies"
down_revision = "178_fix_approvalstatus_enum_case"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if "task_dependencies" in inspector.get_table_names():
        return
    op.create_table(
        "task_dependencies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("depends_on_id", sa.Integer(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dependency_type", sa.String(20), nullable=False, server_default="finish_to_start"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_task_dependencies_task_id", "task_dependencies", ["task_id"])
    op.create_index("ix_task_dependencies_depends_on_id", "task_dependencies", ["depends_on_id"])
    op.create_unique_constraint("uq_task_dependencies_pair", "task_dependencies", ["task_id", "depends_on_id"])


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if "task_dependencies" not in inspector.get_table_names():
        return
    op.drop_table("task_dependencies")
