"""Add invoices_peppol_compliant to settings

Revision ID: 112_add_invoices_peppol_compliant
Revises: 111_add_use_last_month_dates
Create Date: 2025-01-30

When enabled, PDFs include PEPPOL/EN 16931 identifiers and warnings are shown
when required data is missing. UBL for Peppol includes mandatory elements.
"""
from alembic import op
import sqlalchemy as sa


revision = "112_add_invoices_peppol_compliant"
down_revision = "111_add_use_last_month_dates"
branch_labels = None
depends_on = None


def upgrade():
    """Add invoices_peppol_compliant column to settings table"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)

    existing_tables = inspector.get_table_names()
    if 'settings' not in existing_tables:
        return

    settings_columns = {c['name'] for c in inspector.get_columns('settings')}
    if 'invoices_peppol_compliant' in settings_columns:
        print("✓ Column invoices_peppol_compliant already exists in settings table")
        return

    try:
        op.add_column(
            "settings",
            sa.Column("invoices_peppol_compliant", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
        print("✓ Added invoices_peppol_compliant column to settings table")
    except Exception as e:
        error_msg = str(e)
        if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
            print("✓ Column invoices_peppol_compliant already exists in settings table (detected via error)")
        else:
            print(f"✗ Error adding invoices_peppol_compliant column: {e}")
            raise


def downgrade():
    """Remove invoices_peppol_compliant column from settings table"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)

    existing_tables = inspector.get_table_names()
    if 'settings' not in existing_tables:
        return

    settings_columns = {c['name'] for c in inspector.get_columns('settings')}
    if 'invoices_peppol_compliant' not in settings_columns:
        print("⊘ Column invoices_peppol_compliant does not exist in settings table, skipping")
        return

    try:
        op.drop_column("settings", "invoices_peppol_compliant")
        print("✓ Dropped invoices_peppol_compliant column from settings table")
    except Exception as e:
        error_msg = str(e)
        if 'does not exist' in error_msg.lower() or 'no such column' in error_msg.lower():
            print("⊘ Column invoices_peppol_compliant does not exist in settings table (detected via error)")
        else:
            print(f"⚠ Warning: Could not drop invoices_peppol_compliant column: {e}")
