"""Add OAuth application and authorization code tables (Phase 5 scaffolding).

Revision ID: 198_add_oauth_applications
Revises: 197_phase4_gdpr_and_governance
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "198_add_oauth_applications"
down_revision = "197_phase4_gdpr_and_governance"
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

    if not _has_table(inspector, "oauth_applications"):
        op.create_table(
            "oauth_applications",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("client_id", sa.String(length=64), nullable=False),
            sa.Column("client_secret_hash", sa.String(length=128), nullable=True),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("owner_user_id", sa.Integer(), nullable=False),
            sa.Column("redirect_uris", sa.JSON(), nullable=False),
            sa.Column("allowed_scopes", sa.Text(), nullable=False, server_default=""),
            sa.Column("grant_types", sa.JSON(), nullable=False),
            sa.Column("is_confidential", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_oauth_applications_client_id", "oauth_applications", ["client_id"], unique=True)
        op.create_index("ix_oauth_applications_owner_user_id", "oauth_applications", ["owner_user_id"])

    if not _has_table(inspector, "oauth_authorization_codes"):
        op.create_table(
            "oauth_authorization_codes",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("code_hash", sa.String(length=128), nullable=False),
            sa.Column("application_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("redirect_uri", sa.String(length=500), nullable=False),
            sa.Column("scope", sa.Text(), nullable=False, server_default=""),
            sa.Column("code_challenge", sa.String(length=128), nullable=True),
            sa.Column("code_challenge_method", sa.String(length=10), nullable=True),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("used_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["application_id"], ["oauth_applications.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_oauth_authorization_codes_code_hash", "oauth_authorization_codes", ["code_hash"], unique=True
        )
        op.create_index(
            "ix_oauth_authorization_codes_application_id", "oauth_authorization_codes", ["application_id"]
        )
        op.create_index("ix_oauth_authorization_codes_user_id", "oauth_authorization_codes", ["user_id"])


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if _has_table(inspector, "oauth_authorization_codes"):
        op.drop_table("oauth_authorization_codes")
    if _has_table(inspector, "oauth_applications"):
        op.drop_table("oauth_applications")
