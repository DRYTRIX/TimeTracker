"""Add users.scim_external_id for SCIM provisioning.

Revision ID: 205_add_user_scim_external_id
Revises: 204_add_user_external_identity
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "205_add_user_scim_external_id"
down_revision = "204_add_user_external_identity"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("users")}
    if "scim_external_id" not in cols:
        op.add_column("users", sa.Column("scim_external_id", sa.String(length=255), nullable=True))
    inspector = inspect(bind)
    existing_indexes = {ix["name"] for ix in inspector.get_indexes("users")}
    if "ix_users_scim_external_id" not in existing_indexes:
        op.create_index("ix_users_scim_external_id", "users", ["scim_external_id"], unique=True)


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_indexes = {ix["name"] for ix in inspector.get_indexes("users")}
    if "ix_users_scim_external_id" in existing_indexes:
        op.drop_index("ix_users_scim_external_id", table_name="users")
    cols = {c["name"] for c in inspector.get_columns("users")}
    if "scim_external_id" in cols:
        op.drop_column("users", "scim_external_id")
