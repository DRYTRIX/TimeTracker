"""Add oauth_access_tokens table for authorization-server issued tokens.

Revision ID: 203_add_oauth_access_tokens
Revises: 202_add_client_leitweg_id
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "203_add_oauth_access_tokens"
down_revision = "202_add_client_leitweg_id"
branch_labels = None
depends_on = None


def _has_table(inspector, name: str) -> bool:
    try:
        return name in inspector.get_table_names()
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    if not _has_table(inspector, "oauth_access_tokens"):
        op.create_table(
            "oauth_access_tokens",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("token_hash", sa.String(length=128), nullable=False),
            sa.Column("token_prefix", sa.String(length=16), nullable=False),
            sa.Column("application_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("scopes", sa.Text(), nullable=False, server_default=""),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("refresh_token_hash", sa.String(length=128), nullable=True),
            sa.Column("refresh_expires_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("last_used_at", sa.DateTime(), nullable=True),
            sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
            sa.ForeignKeyConstraint(["application_id"], ["oauth_applications.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_oauth_access_tokens_token_hash", "oauth_access_tokens", ["token_hash"], unique=True)
        op.create_index(
            "ix_oauth_access_tokens_refresh_token_hash",
            "oauth_access_tokens",
            ["refresh_token_hash"],
            unique=True,
        )
        op.create_index("ix_oauth_access_tokens_application_id", "oauth_access_tokens", ["application_id"])
        op.create_index("ix_oauth_access_tokens_user_id", "oauth_access_tokens", ["user_id"])


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if _has_table(inspector, "oauth_access_tokens"):
        op.drop_table("oauth_access_tokens")
