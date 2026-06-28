"""Add deleted_usernames table and users.portal_only column.

Revision ID: 163_deleted_usernames_and_portal_only
Revises: 162_add_invoice_group_time_entries_setting
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "163_deleted_usernames_and_portal_only"
down_revision = "162_add_invoice_group_time_entries_setting"
branch_labels = None
depends_on = None


def _has_table(inspector, table_name):
    return table_name in inspector.get_table_names()


def _has_column(inspector, table_name, column_name):
    try:
        return column_name in {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    dialect_name = bind.dialect.name if bind else "generic"
    bool_false_default = "0" if dialect_name == "sqlite" else ("false" if dialect_name == "postgresql" else "0")

    if not _has_table(inspector, "deleted_usernames"):
        op.create_table(
            "deleted_usernames",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("username", sa.String(length=80), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_by_user_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["deleted_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("username"),
        )
        op.create_index(op.f("ix_deleted_usernames_username"), "deleted_usernames", ["username"], unique=True)

    if _has_table(inspector, "users") and not _has_column(inspector, "users", "portal_only"):
        op.add_column(
            "users",
            sa.Column(
                "portal_only",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text(bool_false_default),
            ),
        )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    if _has_table(inspector, "users") and _has_column(inspector, "users", "portal_only"):
        op.drop_column("users", "portal_only")

    if _has_table(inspector, "deleted_usernames"):
        op.drop_index(op.f("ix_deleted_usernames_username"), table_name="deleted_usernames")
        op.drop_table("deleted_usernames")
