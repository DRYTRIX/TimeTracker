"""Add kanban_board_templates table for saveable board layouts.

Revision ID: 170_add_kanban_board_templates
Revises: 169_add_task_checklist_items
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "170_add_kanban_board_templates"
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
    if _has_table(inspector, "kanban_board_templates"):
        return
    op.create_table(
        "kanban_board_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("columns", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_kanban_board_template_name"),
    )
    op.create_index("ix_kanban_board_templates_created_by", "kanban_board_templates", ["created_by"])


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if not _has_table(inspector, "kanban_board_templates"):
        return
    op.drop_index("ix_kanban_board_templates_created_by", table_name="kanban_board_templates")
    op.drop_table("kanban_board_templates")
