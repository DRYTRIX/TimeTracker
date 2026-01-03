"""Make global unique constraints tenant-scoped

Revision ID: 103_make_unique_constraints_tenant_scoped
Revises: 102_add_tenant_billing_and_stripe_events
Create Date: 2026-01-03
"""

from alembic import op
import sqlalchemy as sa


revision = "103_make_unique_constraints_tenant_scoped"
down_revision = "102_add_tenant_billing_and_stripe_events"
branch_labels = None
depends_on = None


def _drop_unique_constraints_on_columns(bind, table_name: str, columns: list[str]) -> None:
    """Drop any existing unique constraints that match exactly these columns (Postgres only)."""
    if bind.dialect.name != "postgresql":
        return
    insp = sa.inspect(bind)
    for uc in insp.get_unique_constraints(table_name) or []:
        cols = uc.get("column_names") or []
        if list(cols) == list(columns):
            try:
                op.drop_constraint(uc["name"], table_name, type_="unique")
            except Exception:
                pass


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if "clients" in insp.get_table_names():
        _drop_unique_constraints_on_columns(bind, "clients", ["name"])
        _drop_unique_constraints_on_columns(bind, "clients", ["portal_username"])

        # Create tenant-scoped unique indexes (works well with NULLs)
        try:
            op.create_index("ux_clients_tenant_name", "clients", ["tenant_id", "name"], unique=True)
        except Exception:
            pass
        try:
            op.create_index("ux_clients_tenant_portal_username", "clients", ["tenant_id", "portal_username"], unique=True)
        except Exception:
            pass

    if "projects" in insp.get_table_names():
        _drop_unique_constraints_on_columns(bind, "projects", ["code"])
        try:
            op.create_index("ux_projects_tenant_code", "projects", ["tenant_id", "code"], unique=True)
        except Exception:
            pass

    if "invoices" in insp.get_table_names():
        _drop_unique_constraints_on_columns(bind, "invoices", ["invoice_number"])
        try:
            op.create_index("ux_invoices_tenant_invoice_number", "invoices", ["tenant_id", "invoice_number"], unique=True)
        except Exception:
            pass


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # Drop tenant-scoped indexes
    if "invoices" in insp.get_table_names():
        try:
            op.drop_index("ux_invoices_tenant_invoice_number", table_name="invoices")
        except Exception:
            pass

    if "projects" in insp.get_table_names():
        try:
            op.drop_index("ux_projects_tenant_code", table_name="projects")
        except Exception:
            pass

    if "clients" in insp.get_table_names():
        try:
            op.drop_index("ux_clients_tenant_portal_username", table_name="clients")
        except Exception:
            pass
        try:
            op.drop_index("ux_clients_tenant_name", table_name="clients")
        except Exception:
            pass

