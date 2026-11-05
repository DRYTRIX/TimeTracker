"""add company_logo_filename to settings and started/completed to tasks

Revision ID: 006
Revises: 005
Create Date: 2025-09-08 16:41:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    settings_cols = {c["name"] for c in inspector.get_columns("settings")}
    tasks_cols = {c["name"] for c in inspector.get_columns("tasks")}

    # Add company_logo_filename to settings if missing
    if "company_logo_filename" not in settings_cols:
        with op.batch_alter_table("settings") as batch_op:
            batch_op.add_column(
                sa.Column("company_logo_filename", sa.String(length=255), nullable=True, server_default="")
            )

    # Add started_at and completed_at to tasks if missing
    add_task_cols = []
    if "started_at" not in tasks_cols:
        add_task_cols.append(sa.Column("started_at", sa.DateTime(), nullable=True))
    if "completed_at" not in tasks_cols:
        add_task_cols.append(sa.Column("completed_at", sa.DateTime(), nullable=True))
    if add_task_cols:
        with op.batch_alter_table("tasks") as batch_op:
            for col in add_task_cols:
                batch_op.add_column(col)


def downgrade() -> None:
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_column("completed_at")
        batch_op.drop_column("started_at")

    with op.batch_alter_table("settings") as batch_op:
        batch_op.drop_column("company_logo_filename")
