"""Add buyer_reference to invoices (PEPPOL BT-10)

Revision ID: 113_add_invoice_buyer_reference
Revises: 112_add_invoices_peppol_compliant
Create Date: 2025-01-30

Optional PEPPOL/EN 16931 Buyer Reference (BT-10) for use in UBL.
"""
from alembic import op
import sqlalchemy as sa


revision = "113_add_invoice_buyer_reference"
down_revision = "112_add_invoices_peppol_compliant"
branch_labels = None
depends_on = None


def upgrade():
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)

    if "invoices" not in inspector.get_table_names():
        return
    if "buyer_reference" in {c["name"] for c in inspector.get_columns("invoices")}:
        print("✓ Column buyer_reference already exists in invoices table")
        return

    try:
        op.add_column(
            "invoices",
            sa.Column("buyer_reference", sa.String(length=200), nullable=True),
        )
        print("✓ Added buyer_reference column to invoices table")
    except Exception as e:
        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
            print("✓ Column buyer_reference already exists in invoices table (detected via error)")
        else:
            raise


def downgrade():
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)

    if "invoices" not in inspector.get_table_names():
        return
    if "buyer_reference" not in {c["name"] for c in inspector.get_columns("invoices")}:
        print("⊘ Column buyer_reference does not exist in invoices table, skipping")
        return

    try:
        op.drop_column("invoices", "buyer_reference")
        print("✓ Dropped buyer_reference column from invoices table")
    except Exception as e:
        if "does not exist" in str(e).lower() or "no such column" in str(e).lower():
            print("⊘ Column buyer_reference does not exist (detected via error)")
        else:
            print(f"⚠ Warning: Could not drop buyer_reference column: {e}")
