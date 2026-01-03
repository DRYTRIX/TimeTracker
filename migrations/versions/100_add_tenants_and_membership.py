"""Add tenants and tenant membership tables

Revision ID: 100_add_tenants_and_membership
Revises: 099_add_peppol_settings_columns
Create Date: 2026-01-03
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "100_add_tenants_and_membership"
down_revision = "099_add_peppol_settings_columns"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Create tenants table
    if "tenants" not in inspector.get_table_names():
        op.create_table(
            "tenants",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("slug", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'active'")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("primary_owner_user_id", sa.Integer(), nullable=True),
            sa.Column("billing_email", sa.String(length=200), nullable=True),
            sa.Column("default_timezone", sa.String(length=50), nullable=True),
            sa.Column("default_currency", sa.String(length=3), nullable=True),
        )
        op.create_index("ix_tenants_slug", "tenants", ["slug"], unique=True)
        op.create_index("ix_tenants_created_by_user_id", "tenants", ["created_by_user_id"], unique=False)
        op.create_index("ix_tenants_primary_owner_user_id", "tenants", ["primary_owner_user_id"], unique=False)

    # Re-inspect for subsequent operations
    inspector = sa.inspect(bind)

    # Create tenant_members table
    if "tenant_members" not in inspector.get_table_names():
        op.create_table(
            "tenant_members",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("role", sa.String(length=20), nullable=False, server_default=sa.text("'member'")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("tenant_id", "user_id", name="uq_tenant_members_tenant_user"),
        )
        op.create_index("ix_tenant_members_tenant_id", "tenant_members", ["tenant_id"], unique=False)
        op.create_index("ix_tenant_members_user_id", "tenant_members", ["user_id"], unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "tenant_members" in inspector.get_table_names():
        try:
            op.drop_index("ix_tenant_members_user_id", table_name="tenant_members")
        except Exception:
            pass
        try:
            op.drop_index("ix_tenant_members_tenant_id", table_name="tenant_members")
        except Exception:
            pass
        op.drop_table("tenant_members")

    inspector = sa.inspect(bind)
    if "tenants" in inspector.get_table_names():
        try:
            op.drop_index("ix_tenants_primary_owner_user_id", table_name="tenants")
        except Exception:
            pass
        try:
            op.drop_index("ix_tenants_created_by_user_id", table_name="tenants")
        except Exception:
            pass
        try:
            op.drop_index("ix_tenants_slug", table_name="tenants")
        except Exception:
            pass
        op.drop_table("tenants")

