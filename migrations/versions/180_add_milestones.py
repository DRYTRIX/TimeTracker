"""Add milestones table and tasks.milestone_id.

Revision ID: 180_add_milestones
Revises: 179_add_task_dependencies
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "180_add_milestones"
down_revision = "179_add_task_dependencies"
branch_labels = None
depends_on = None


def _has_column(inspector, table_name, column_name):
    try:
        return column_name in {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if "milestones" not in inspector.get_table_names():
        op.create_table(
            "milestones",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("due_date", sa.Date(), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="upcoming"),
            sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_milestones_project_id", "milestones", ["project_id"])
        op.create_index("ix_milestones_due_date", "milestones", ["due_date"])
        op.create_index("ix_milestones_status", "milestones", ["status"])
        op.create_index("ix_milestones_created_by", "milestones", ["created_by"])

    inspector = inspect(bind)
    # SQLite cannot ALTER to add FK constraints; use batch copy-and-move.
    if not _has_column(inspector, "tasks", "milestone_id"):
        with op.batch_alter_table("tasks", schema=None) as batch_op:
            batch_op.add_column(sa.Column("milestone_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_tasks_milestone_id_milestones",
                "milestones",
                ["milestone_id"],
                ["id"],
                ondelete="SET NULL",
            )
            batch_op.create_index("ix_tasks_milestone_id", ["milestone_id"])


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if _has_column(inspector, "tasks", "milestone_id"):
        with op.batch_alter_table("tasks", schema=None) as batch_op:
            batch_op.drop_index("ix_tasks_milestone_id")
            batch_op.drop_constraint("fk_tasks_milestone_id_milestones", type_="foreignkey")
            batch_op.drop_column("milestone_id")
    inspector = inspect(bind)
    if "milestones" in inspector.get_table_names():
        op.drop_table("milestones")
