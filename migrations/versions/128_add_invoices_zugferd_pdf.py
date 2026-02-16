"""Add invoices_zugferd_pdf to settings

Revision ID: 128_add_invoices_zugferd_pdf
Revises: 127_add_user_clients
Create Date: 2026-02-16

When enabled, exported invoice PDFs embed EN 16931 UBL XML (ZugFerd/Factur-X).
"""
from alembic import op
import sqlalchemy as sa


revision = "128_add_invoices_zugferd_pdf"
down_revision = "127_add_user_clients"
branch_labels = None
depends_on = None


def upgrade():
    """Add invoices_zugferd_pdf column to settings table"""
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)

    existing_tables = inspector.get_table_names()
    if "settings" not in existing_tables:
        return

    settings_columns = {c["name"] for c in inspector.get_columns("settings")}
    if "invoices_zugferd_pdf" in settings_columns:
        print("✓ Column invoices_zugferd_pdf already exists in settings table")
        return

    try:
        op.add_column(
            "settings",
            sa.Column("invoices_zugferd_pdf", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
        print("✓ Added invoices_zugferd_pdf column to settings table")
    except Exception as e:
        error_msg = str(e)
        if "already exists" in error_msg.lower() or "duplicate" in error_msg.lower():
            print("✓ Column invoices_zugferd_pdf already exists in settings table (detected via error)")
        else:
            print(f"✗ Error adding invoices_zugferd_pdf column: {e}")
            raise


def downgrade():
    """Remove invoices_zugferd_pdf column from settings table"""
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)

    existing_tables = inspector.get_table_names()
    if "settings" not in existing_tables:
        return

    settings_columns = {c["name"] for c in inspector.get_columns("settings")}
    if "invoices_zugferd_pdf" not in settings_columns:
        print("⊘ Column invoices_zugferd_pdf does not exist in settings table, skipping")
        return

    try:
        op.drop_column("settings", "invoices_zugferd_pdf")
        print("✓ Dropped invoices_zugferd_pdf column from settings table")
    except Exception as e:
        error_msg = str(e)
        if "does not exist" in error_msg.lower() or "no such column" in error_msg.lower():
            print("⊘ Column invoices_zugferd_pdf does not exist in settings table (detected via error)")
        else:
            print(f"⚠ Warning: Could not drop invoices_zugferd_pdf column: {e}")
