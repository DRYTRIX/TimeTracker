"""Replace single task assigned_to with multi-assignee tables.

Revision ID: 199_task_multi_assignees
Revises: 198_add_oauth_applications
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "199_task_multi_assignees"
down_revision = "198_add_oauth_applications"
branch_labels = None
depends_on = None


def _has_table(inspector, name: str) -> bool:
    try:
        return name in inspector.get_table_names()
    except Exception:
        return False


def _has_column(inspector, table: str, column: str) -> bool:
    try:
        return any(c["name"] == column for c in inspector.get_columns(table))
    except Exception:
        return False


def _drop_fk_on_column(inspector, table: str, column: str):
    try:
        for fk in inspector.get_foreign_keys(table):
            if column in (fk.get("constrained_columns") or []):
                name = fk.get("name")
                if name:
                    op.drop_constraint(name, table, type_="foreignkey")
    except Exception:
        pass


def _drop_indexes_on_column(inspector, table: str, column: str):
    try:
        for ix in inspector.get_indexes(table):
            if column in (ix.get("column_names") or []):
                name = ix.get("name")
                if name:
                    op.drop_index(name, table_name=table)
    except Exception:
        pass


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    if not _has_table(inspector, "task_assignees"):
        op.create_table(
            "task_assignees",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("task_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("task_id", "user_id", name="uq_task_assignee"),
        )
        op.create_index("ix_task_assignees_task_id", "task_assignees", ["task_id"])
        op.create_index("ix_task_assignees_user_id", "task_assignees", ["user_id"])

    if not _has_table(inspector, "recurring_task_assignees"):
        op.create_table(
            "recurring_task_assignees",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("recurring_task_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["recurring_task_id"], ["recurring_tasks.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("recurring_task_id", "user_id", name="uq_recurring_task_assignee"),
        )
        op.create_index(
            "ix_recurring_task_assignees_recurring_task_id",
            "recurring_task_assignees",
            ["recurring_task_id"],
        )
        op.create_index("ix_recurring_task_assignees_user_id", "recurring_task_assignees", ["user_id"])

    # Backfill from legacy assigned_to columns
    inspector = inspect(bind)
    if _has_column(inspector, "tasks", "assigned_to"):
        op.execute(
            sa.text(
                """
                INSERT INTO task_assignees (task_id, user_id, created_at)
                SELECT id, assigned_to, CURRENT_TIMESTAMP
                FROM tasks
                WHERE assigned_to IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM task_assignees ta
                      WHERE ta.task_id = tasks.id AND ta.user_id = tasks.assigned_to
                  )
                """
            )
        )
        _drop_fk_on_column(inspector, "tasks", "assigned_to")
        _drop_indexes_on_column(inspector, "tasks", "assigned_to")
        op.drop_column("tasks", "assigned_to")

    inspector = inspect(bind)
    if _has_column(inspector, "recurring_tasks", "assigned_to"):
        op.execute(
            sa.text(
                """
                INSERT INTO recurring_task_assignees (recurring_task_id, user_id, created_at)
                SELECT id, assigned_to, CURRENT_TIMESTAMP
                FROM recurring_tasks
                WHERE assigned_to IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM recurring_task_assignees rta
                      WHERE rta.recurring_task_id = recurring_tasks.id
                        AND rta.user_id = recurring_tasks.assigned_to
                  )
                """
            )
        )
        _drop_fk_on_column(inspector, "recurring_tasks", "assigned_to")
        _drop_indexes_on_column(inspector, "recurring_tasks", "assigned_to")
        op.drop_column("recurring_tasks", "assigned_to")


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    if not _has_column(inspector, "tasks", "assigned_to"):
        op.add_column("tasks", sa.Column("assigned_to", sa.Integer(), nullable=True))
        op.create_foreign_key(
            None, "tasks", "users", ["assigned_to"], ["id"], ondelete="SET NULL"
        )
        op.create_index("ix_tasks_assigned_to", "tasks", ["assigned_to"])
        if _has_table(inspector, "task_assignees"):
            op.execute(
                sa.text(
                    """
                    UPDATE tasks
                    SET assigned_to = (
                        SELECT ta.user_id FROM task_assignees ta
                        WHERE ta.task_id = tasks.id
                        ORDER BY ta.id ASC
                        LIMIT 1
                    )
                    """
                )
            )

    inspector = inspect(bind)
    if not _has_column(inspector, "recurring_tasks", "assigned_to"):
        op.add_column("recurring_tasks", sa.Column("assigned_to", sa.Integer(), nullable=True))
        op.create_foreign_key(None, "recurring_tasks", "users", ["assigned_to"], ["id"])
        op.create_index("ix_recurring_tasks_assigned_to", "recurring_tasks", ["assigned_to"])
        if _has_table(inspector, "recurring_task_assignees"):
            op.execute(
                sa.text(
                    """
                    UPDATE recurring_tasks
                    SET assigned_to = (
                        SELECT rta.user_id FROM recurring_task_assignees rta
                        WHERE rta.recurring_task_id = recurring_tasks.id
                        ORDER BY rta.id ASC
                        LIMIT 1
                    )
                    """
                )
            )

    if _has_table(inspector, "task_assignees"):
        op.drop_table("task_assignees")
    if _has_table(inspector, "recurring_task_assignees"):
        op.drop_table("recurring_task_assignees")
