"""Add last_used_at to projects for recency-based sorting.

Revision ID: 182_add_project_last_used_at
Revises: 181_add_quote_signature
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "182_add_project_last_used_at"
down_revision = "181_add_quote_signature"
branch_labels = None
depends_on = None


def _has_column(inspector, table_name, column_name):
    try:
        return column_name in {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return False


def _has_index(inspector, table_name, index_name):
    try:
        if table_name not in inspector.get_table_names():
            return False
        return any(idx["name"] == index_name for idx in inspector.get_indexes(table_name))
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if "projects" not in inspector.get_table_names():
        return
    if not _has_column(inspector, "projects", "last_used_at"):
        op.add_column("projects", sa.Column("last_used_at", sa.DateTime(), nullable=True))
        inspector = inspect(bind)
    if not _has_index(inspector, "projects", "ix_projects_last_used_at"):
        op.create_index("ix_projects_last_used_at", "projects", ["last_used_at"])


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if "projects" not in inspector.get_table_names():
        return
    if _has_index(inspector, "projects", "ix_projects_last_used_at"):
        op.drop_index("ix_projects_last_used_at", table_name="projects")
        inspector = inspect(bind)
    if _has_column(inspector, "projects", "last_used_at"):
        op.drop_column("projects", "last_used_at")
