"""Add custom_fields JSON to tasks for integration metadata

Revision ID: 143_add_task_custom_fields
Revises: 142_add_mail_test_recipient
Create Date: 2026-04-05
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "143_add_task_custom_fields"
down_revision = "142_add_mail_test_recipient"
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    try:
        return column_name in [col["name"] for col in inspector.get_columns(table_name)]
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "tasks" not in inspector.get_table_names():
        return
    if _has_column(inspector, "tasks", "custom_fields"):
        return
    try:
        op.add_column(
            "tasks",
            sa.Column("custom_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        )
    except Exception:
        op.add_column("tasks", sa.Column("custom_fields", sa.JSON(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "tasks" not in inspector.get_table_names():
        return
    if not _has_column(inspector, "tasks", "custom_fields"):
        return
    op.drop_column("tasks", "custom_fields")
