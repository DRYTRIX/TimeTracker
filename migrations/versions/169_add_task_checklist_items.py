"""Add task_checklist_items table for per-task checklists/subtasks.

Revision ID: 169_add_task_checklist_items
Revises: 168_add_kanban_wip_limit
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "169_add_task_checklist_items"
down_revision = "166_add_slack_user_id"
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    try:
        return table_name in inspector.get_table_names()
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if _has_table(inspector, "task_checklist_items"):
        return
    op.create_table(
        "task_checklist_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.String(length=500), nullable=False),
        sa.Column("is_done", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_checklist_items_task_id", "task_checklist_items", ["task_id"])
    op.create_index("ix_task_checklist_items_position", "task_checklist_items", ["position"])


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if not _has_table(inspector, "task_checklist_items"):
        return
    op.drop_index("ix_task_checklist_items_position", table_name="task_checklist_items")
    op.drop_index("ix_task_checklist_items_task_id", table_name="task_checklist_items")
    op.drop_table("task_checklist_items")
