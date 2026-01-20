"""Add Gantt colors (project, task) and modules_disabled (settings)

Revision ID: 100_gantt_colors_modules
Revises: 099_add_peppol_settings_columns
Create Date: 2026-01-19

"""
from alembic import op
import sqlalchemy as sa


revision = "100_gantt_colors_modules"
down_revision = "099_add_peppol_settings_columns"
branch_labels = None
depends_on = None


def upgrade():
    """Add color to projects and tasks; modules_disabled to settings."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # projects.color
    if "projects" in inspector.get_table_names():
        projects_cols = {c["name"] for c in inspector.get_columns("projects")}
        if "color" not in projects_cols:
            op.add_column(
                "projects",
                sa.Column("color", sa.String(length=7), nullable=True),
            )

    # tasks.color
    if "tasks" in inspector.get_table_names():
        tasks_cols = {c["name"] for c in inspector.get_columns("tasks")}
        if "color" not in tasks_cols:
            op.add_column(
                "tasks",
                sa.Column("color", sa.String(length=7), nullable=True),
            )

    # settings.modules_disabled
    if "settings" in inspector.get_table_names():
        settings_cols = {c["name"] for c in inspector.get_columns("settings")}
        if "modules_disabled" not in settings_cols:
            op.add_column(
                "settings",
                sa.Column("modules_disabled", sa.Text(), nullable=True),
            )


def downgrade():
    """Remove color from projects and tasks; modules_disabled from settings."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    is_sqlite = bind.dialect.name == "sqlite"

    if "projects" in inspector.get_table_names():
        projects_cols = {c["name"] for c in inspector.get_columns("projects")}
        if "color" in projects_cols:
            if is_sqlite:
                with op.batch_alter_table("projects", schema=None) as batch_op:
                    batch_op.drop_column("color")
            else:
                op.drop_column("projects", "color")

    if "tasks" in inspector.get_table_names():
        tasks_cols = {c["name"] for c in inspector.get_columns("tasks")}
        if "color" in tasks_cols:
            if is_sqlite:
                with op.batch_alter_table("tasks", schema=None) as batch_op:
                    batch_op.drop_column("color")
            else:
                op.drop_column("tasks", "color")

    if "settings" in inspector.get_table_names():
        settings_cols = {c["name"] for c in inspector.get_columns("settings")}
        if "modules_disabled" in settings_cols:
            if is_sqlite:
                with op.batch_alter_table("settings", schema=None) as batch_op:
                    batch_op.drop_column("modules_disabled")
            else:
                op.drop_column("settings", "modules_disabled")
