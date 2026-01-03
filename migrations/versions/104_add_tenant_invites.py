"""Add tenant invites

Revision ID: 104_add_tenant_invites
Revises: 103_make_unique_constraints_tenant_scoped
Create Date: 2026-01-03
"""

from alembic import op
import sqlalchemy as sa


revision = "104_add_tenant_invites"
down_revision = "103_make_unique_constraints_tenant_scoped"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "tenant_invites" in inspector.get_table_names():
        return

    op.create_table(
        "tenant_invites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(length=200), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default=sa.text("'member'")),
        sa.Column("token", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("accepted_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.UniqueConstraint("token", name="uq_tenant_invites_token"),
    )

    op.create_index("ix_tenant_invites_tenant_id", "tenant_invites", ["tenant_id"], unique=False)
    op.create_index("ix_tenant_invites_email", "tenant_invites", ["email"], unique=False)
    op.create_index("ix_tenant_invites_token", "tenant_invites", ["token"], unique=True)
    op.create_index("ix_tenant_invites_accepted_by_user_id", "tenant_invites", ["accepted_by_user_id"], unique=False)
    op.create_index("ix_tenant_invites_revoked_by_user_id", "tenant_invites", ["revoked_by_user_id"], unique=False)
    op.create_index("ix_tenant_invites_created_by_user_id", "tenant_invites", ["created_by_user_id"], unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "tenant_invites" not in inspector.get_table_names():
        return

    for ix in (
        "ix_tenant_invites_created_by_user_id",
        "ix_tenant_invites_revoked_by_user_id",
        "ix_tenant_invites_accepted_by_user_id",
        "ix_tenant_invites_token",
        "ix_tenant_invites_email",
        "ix_tenant_invites_tenant_id",
    ):
        try:
            op.drop_index(ix, table_name="tenant_invites")
        except Exception:
            pass
    op.drop_table("tenant_invites")

