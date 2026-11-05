"""Add TOTP 2FA fields to users.

Revision ID: 152_add_user_totp_2fa
Revises: 151_add_ai_helper_settings
Create Date: 2026-04-26
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "152_add_user_totp_2fa"
down_revision = "151_add_ai_helper_settings"
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    try:
        return column_name in {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if "users" not in inspector.get_table_names():
        return

    if not _has_column(inspector, "users", "two_factor_enabled"):
        op.add_column(
            "users", sa.Column("two_factor_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false"))
        )
    if not _has_column(inspector, "users", "two_factor_secret"):
        op.add_column("users", sa.Column("two_factor_secret", sa.String(length=255), nullable=True))
    if not _has_column(inspector, "users", "two_factor_confirmed_at"):
        op.add_column("users", sa.Column("two_factor_confirmed_at", sa.DateTime(), nullable=True))

    # Remove server default for new rows (keeps model default behavior).
    try:
        op.alter_column("users", "two_factor_enabled", server_default=None)
    except Exception:
        pass


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if "users" not in inspector.get_table_names():
        return

    for name in ("two_factor_confirmed_at", "two_factor_secret", "two_factor_enabled"):
        if _has_column(inspector, "users", name):
            op.drop_column("users", name)
