"""Add tenant_id to core tables (multi-tenant SaaS)

Revision ID: 101_add_tenant_id_to_core_tables
Revises: 100_add_tenants_and_membership
Create Date: 2026-01-03
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "101_add_tenant_id_to_core_tables"
down_revision = "100_add_tenants_and_membership"
branch_labels = None
depends_on = None


def _ensure_default_tenant_id(bind) -> int:
    """Create default tenant row if missing and return its id."""
    default_slug = "default"
    dialect = bind.dialect.name if bind is not None else "generic"

    if dialect == "postgresql":
        op.execute(
            sa.text(
                """
                INSERT INTO tenants (slug, name, status, created_at)
                VALUES (:slug, :name, 'active', CURRENT_TIMESTAMP)
                ON CONFLICT (slug) DO NOTHING
                """
            ).bindparams(slug=default_slug, name="Default")
        )
    elif dialect == "sqlite":
        # SQLite supports OR IGNORE
        op.execute(
            sa.text(
                """
                INSERT OR IGNORE INTO tenants (slug, name, status, created_at)
                VALUES (:slug, :name, 'active', CURRENT_TIMESTAMP)
                """
            ).bindparams(slug=default_slug, name="Default")
        )
    else:
        # Best-effort for other DBs
        try:
            op.execute(
                sa.text(
                    """
                    INSERT INTO tenants (slug, name, status, created_at)
                    VALUES (:slug, :name, 'active', CURRENT_TIMESTAMP)
                    """
                ).bindparams(slug=default_slug, name="Default")
            )
        except Exception:
            pass

    tenant_id = bind.execute(sa.text("SELECT id FROM tenants WHERE slug = :slug"), {"slug": default_slug}).scalar()
    return int(tenant_id)


def _add_tenant_id_column(table_name: str, bind, *, set_not_null: bool) -> None:
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns(table_name)}
    if "tenant_id" not in cols:
        op.add_column(table_name, sa.Column("tenant_id", sa.Integer(), nullable=True))
        op.create_index(f"ix_{table_name}_tenant_id", table_name, ["tenant_id"], unique=False)
        # Add FK only where supported (SQLite cannot easily add constraints post-hoc)
        if bind.dialect.name == "postgresql":
            op.create_foreign_key(
                f"fk_{table_name}_tenant_id_tenants",
                table_name,
                "tenants",
                ["tenant_id"],
                ["id"],
                ondelete="CASCADE",
            )

    if set_not_null and bind.dialect.name == "postgresql":
        # Enforce not null on Postgres (SQLite ALTER limitations)
        op.alter_column(table_name, "tenant_id", existing_type=sa.Integer(), nullable=False)


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Ensure default tenant exists for backfill
    default_tenant_id = _ensure_default_tenant_id(bind)

    # Add tenant_id columns (nullable first), backfill, then set NOT NULL (Postgres only)
    core_tables = ["clients", "projects", "tasks", "time_entries", "invoices", "expenses", "settings"]
    for table in core_tables:
        if table in inspector.get_table_names():
            _add_tenant_id_column(table, bind, set_not_null=False)

    # Backfill existing rows into default tenant
    for table in core_tables:
        if table not in inspector.get_table_names():
            continue
        op.execute(sa.text(f"UPDATE {table} SET tenant_id = :tid WHERE tenant_id IS NULL").bindparams(tid=default_tenant_id))

    # Settings should be one row per tenant; keep existing row as default tenant settings.
    # Add a unique constraint in Postgres to enforce this going forward.
    if "settings" in inspector.get_table_names() and bind.dialect.name == "postgresql":
        try:
            op.create_unique_constraint("uq_settings_tenant_id", "settings", ["tenant_id"])
        except Exception:
            pass

    # Enforce NOT NULL on Postgres
    if bind.dialect.name == "postgresql":
        for table in core_tables:
            if table in inspector.get_table_names():
                try:
                    op.alter_column(table, "tenant_id", existing_type=sa.Integer(), nullable=False)
                except Exception:
                    # Best-effort; do not block deploy if a table can't be altered.
                    pass


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    core_tables = ["settings", "expenses", "invoices", "time_entries", "tasks", "projects", "clients"]

    for table in core_tables:
        if table not in inspector.get_table_names():
            continue
        # Drop FK if exists (Postgres)
        if bind.dialect.name == "postgresql":
            try:
                op.drop_constraint(f"fk_{table}_tenant_id_tenants", table, type_="foreignkey")
            except Exception:
                pass
        try:
            op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        except Exception:
            pass
        try:
            op.drop_column(table, "tenant_id")
        except Exception:
            pass

