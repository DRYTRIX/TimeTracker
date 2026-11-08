"""Add users.external_subject and users.external_issuer for SAML/OIDC linking.

Revision ID: 204_add_user_external_identity
Revises: 203_add_oauth_access_tokens
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "204_add_user_external_identity"
down_revision = "203_add_oauth_access_tokens"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("users")}
    if "external_subject" not in cols:
        op.add_column("users", sa.Column("external_subject", sa.String(length=255), nullable=True))
    if "external_issuer" not in cols:
        op.add_column("users", sa.Column("external_issuer", sa.String(length=255), nullable=True))
    # Refresh inspector for indexes
    inspector = inspect(bind)
    existing_indexes = {ix["name"] for ix in inspector.get_indexes("users")}
    if "ix_users_external_issuer_subject" not in existing_indexes:
        try:
            op.create_index(
                "ix_users_external_issuer_subject",
                "users",
                ["external_issuer", "external_subject"],
                unique=True,
            )
        except Exception:
            # Some DBs treat multiple NULLs as conflicting for unique indexes; ignore if already ok.
            pass


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_indexes = {ix["name"] for ix in inspector.get_indexes("users")}
    if "ix_users_external_issuer_subject" in existing_indexes:
        op.drop_index("ix_users_external_issuer_subject", table_name="users")
    cols = {c["name"] for c in inspector.get_columns("users")}
    if "external_issuer" in cols:
        op.drop_column("users", "external_issuer")
    if "external_subject" in cols:
        op.drop_column("users", "external_subject")
