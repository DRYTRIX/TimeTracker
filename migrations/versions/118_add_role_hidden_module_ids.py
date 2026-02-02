"""Add hidden_module_ids to roles for per-role module visibility

Revision ID: 118_add_role_hidden_module_ids
Revises: 117_add_user_calendar_type_colors
Create Date: 2026-02-02

Adds roles.hidden_module_ids (JSON array) which stores module IDs hidden for a role.
Empty/NULL means no modules are hidden (all visible unless disabled globally).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = "118_add_role_hidden_module_ids"
down_revision = "117_add_user_calendar_type_colors"
branch_labels = None
depends_on = None


def upgrade():
    """Add hidden_module_ids (JSON/JSONB) to roles table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "roles" not in inspector.get_table_names():
        return

    role_cols = {c["name"] for c in inspector.get_columns("roles")}
    if "hidden_module_ids" in role_cols:
        return

    # Use JSON for SQLite/MySQL, JSONB for PostgreSQL
    is_pg = bind.dialect.name == "postgresql"
    col_type = JSONB() if is_pg else sa.JSON()

    op.add_column(
        "roles",
        sa.Column("hidden_module_ids", col_type, nullable=True),
    )


def downgrade():
    """Remove hidden_module_ids from roles table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    is_sqlite = bind.dialect.name == "sqlite"

    if "roles" not in inspector.get_table_names():
        return

    role_cols = {c["name"] for c in inspector.get_columns("roles")}
    if "hidden_module_ids" not in role_cols:
        return

    if is_sqlite:
        with op.batch_alter_table("roles", schema=None) as batch_op:
            batch_op.drop_column("hidden_module_ids")
    else:
        op.drop_column("roles", "hidden_module_ids")

