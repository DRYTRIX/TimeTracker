"""Per-user GitHub username + per-task external reference column.

Adds two columns that the GitHub / generic external-integration connectors
need:

* ``users.github_username``  – nullable String(100) so a TimeTracker user
  can be linked to their GitHub login (used by webhook-driven timer auto-
  start in ``GitHubConnector``).
* ``tasks.external_ref``     – nullable, indexed String(200) for storing
  the canonical external identifier of a task (e.g.
  ``github_issue_42``).

Both columns are added defensively: we check the inspector first so the
migration is safe to re-run on databases where it's already been applied
manually (or where a different branch added one of them).

Revision ID: 155_add_integration_columns
Revises: 154_add_smart_notify_break_and_eod
Create Date: 2026-05-15
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "155_add_integration_columns"
down_revision = "154_add_smart_notify_break_and_eod"
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    try:
        return column_name in {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return False


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    try:
        return any(idx.get("name") == index_name for idx in inspector.get_indexes(table_name))
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "users" in tables and not _has_column(inspector, "users", "github_username"):
        op.add_column(
            "users",
            sa.Column("github_username", sa.String(length=100), nullable=True),
        )

    if "tasks" in tables and not _has_column(inspector, "tasks", "external_ref"):
        op.add_column(
            "tasks",
            sa.Column("external_ref", sa.String(length=200), nullable=True),
        )
        # Refresh inspector before creating the index so SQLite/Postgres
        # both see the new column.
        inspector = inspect(bind)
        if _has_column(inspector, "tasks", "external_ref") and not _has_index(
            inspector, "tasks", "ix_tasks_external_ref"
        ):
            try:
                op.create_index("ix_tasks_external_ref", "tasks", ["external_ref"], unique=False)
            except Exception:
                pass


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "tasks" in tables:
        if _has_index(inspector, "tasks", "ix_tasks_external_ref"):
            try:
                op.drop_index("ix_tasks_external_ref", table_name="tasks")
            except Exception:
                pass
        if _has_column(inspector, "tasks", "external_ref"):
            try:
                op.drop_column("tasks", "external_ref")
            except Exception:
                pass

    if "users" in tables and _has_column(inspector, "users", "github_username"):
        try:
            op.drop_column("users", "github_username")
        except Exception:
            pass
