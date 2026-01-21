"""Add disabled_module_ids to settings for admin module visibility control

Revision ID: 110_add_disabled_module_ids
Revises: 109_add_pdf_template_date_format
Create Date: 2025-01-30

Admin can disable modules system-wide via settings.disabled_module_ids (JSON array).
Empty or NULL means no modules are disabled (all enabled).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "110_add_disabled_module_ids"
down_revision = "109_add_pdf_template_date_format"
branch_labels = None
depends_on = None


def upgrade():
    """Add disabled_module_ids (JSON/JSONB) to settings table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "settings" not in inspector.get_table_names():
        return

    settings_cols = {c["name"] for c in inspector.get_columns("settings")}
    if "disabled_module_ids" in settings_cols:
        return

    # Use JSON for SQLite/MySQL, JSONB for PostgreSQL
    is_pg = bind.dialect.name == "postgresql"
    col_type = JSONB() if is_pg else sa.JSON()

    op.add_column(
        "settings",
        sa.Column("disabled_module_ids", col_type, nullable=True),
    )


def downgrade():
    """Remove disabled_module_ids from settings table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    is_sqlite = bind.dialect.name == "sqlite"

    if "settings" not in inspector.get_table_names():
        return

    settings_cols = {c["name"] for c in inspector.get_columns("settings")}
    if "disabled_module_ids" not in settings_cols:
        return

    if is_sqlite:
        with op.batch_alter_table("settings", schema=None) as batch_op:
            batch_op.drop_column("disabled_module_ids")
    else:
        op.drop_column("settings", "disabled_module_ids")
