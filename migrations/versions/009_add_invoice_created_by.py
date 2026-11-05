"""add invoices.created_by column and FK (idempotent)

Revision ID: 009
Revises: 008
Create Date: 2025-09-08 16:58:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    table_names = set(inspector.get_table_names())
    if "invoices" not in table_names:
        return

    invoice_cols = {c["name"] for c in inspector.get_columns("invoices")}

    # Add created_by if missing
    if "created_by" not in invoice_cols:
        with op.batch_alter_table("invoices") as batch_op:
            batch_op.add_column(sa.Column("created_by", sa.Integer(), nullable=True))

    # Create FK if not present and users table exists
    fk_names = {fk["name"] for fk in inspector.get_foreign_keys("invoices") if fk.get("name")}
    if "users" in table_names and "fk_invoices_created_by_users" not in fk_names:
        try:
            op.create_foreign_key(
                "fk_invoices_created_by_users",
                source_table="invoices",
                referent_table="users",
                local_cols=["created_by"],
                remote_cols=["id"],
                ondelete="SET NULL",
            )
        except Exception:
            # Some backends or existing FK may cause this to fail; ignore to keep idempotent
            pass


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    if "invoices" not in table_names:
        return

    # Drop FK first (best-effort)
    try:
        op.drop_constraint("fk_invoices_created_by_users", "invoices", type_="foreignkey")
    except Exception:
        pass

    invoice_cols = {c["name"] for c in inspector.get_columns("invoices")}
    if "created_by" in invoice_cols:
        with op.batch_alter_table("invoices") as batch_op:
            batch_op.drop_column("created_by")
