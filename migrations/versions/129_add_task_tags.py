"""Add tags column to tasks table

Revision ID: 129_add_task_tags
Revises: 128_add_invoices_zugferd_pdf
Create Date: 2026-02-28

"""
from alembic import op
import sqlalchemy as sa


revision = "129_add_task_tags"
down_revision = "128_add_invoices_zugferd_pdf"
branch_labels = None
depends_on = None


def upgrade():
    """Add tags column to tasks table for categorization."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "tasks" in inspector.get_table_names():
        tasks_cols = {c["name"] for c in inspector.get_columns("tasks")}
        if "tags" not in tasks_cols:
            op.add_column(
                "tasks",
                sa.Column("tags", sa.String(length=500), nullable=True),
            )


def downgrade():
    """Remove tags column from tasks table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    is_sqlite = bind.dialect.name == "sqlite"

    if "tasks" in inspector.get_table_names():
        tasks_cols = {c["name"] for c in inspector.get_columns("tasks")}
        if "tags" in tasks_cols:
            if is_sqlite:
                with op.batch_alter_table("tasks", schema=None) as batch_op:
                    batch_op.drop_column("tags")
            else:
                op.drop_column("tasks", "tags")
