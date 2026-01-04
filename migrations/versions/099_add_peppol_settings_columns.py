"""Add Peppol settings fields

Revision ID: 099_add_peppol_settings_columns
Revises: 098_add_invoice_peppol_transmissions
Create Date: 2026-01-03
"""

from alembic import op
import sqlalchemy as sa


revision = "099_add_peppol_settings_columns"
down_revision = "098_add_invoice_peppol_transmissions"
branch_labels = None
depends_on = None


def upgrade():
    """Add Peppol settings columns to settings table"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    if 'settings' not in existing_tables:
        return
    
    settings_columns = {c['name'] for c in inspector.get_columns('settings')}
    
    columns_to_add = [
        ("peppol_enabled", sa.Column("peppol_enabled", sa.Boolean(), nullable=True)),
        ("peppol_sender_endpoint_id", sa.Column("peppol_sender_endpoint_id", sa.String(length=100), nullable=True, server_default="")),
        ("peppol_sender_scheme_id", sa.Column("peppol_sender_scheme_id", sa.String(length=20), nullable=True, server_default="")),
        ("peppol_sender_country", sa.Column("peppol_sender_country", sa.String(length=2), nullable=True, server_default="")),
        ("peppol_access_point_url", sa.Column("peppol_access_point_url", sa.String(length=500), nullable=True, server_default="")),
        ("peppol_access_point_token", sa.Column("peppol_access_point_token", sa.String(length=255), nullable=True, server_default="")),
        ("peppol_access_point_timeout", sa.Column("peppol_access_point_timeout", sa.Integer(), nullable=True, server_default="30")),
        ("peppol_provider", sa.Column("peppol_provider", sa.String(length=50), nullable=True, server_default="generic")),
    ]
    
    for col_name, col_def in columns_to_add:
        if col_name in settings_columns:
            print(f"✓ Column {col_name} already exists in settings table")
            continue
        
        try:
            op.add_column("settings", col_def)
            print(f"✓ Added {col_name} column to settings table")
        except Exception as e:
            error_msg = str(e)
            if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
                print(f"✓ Column {col_name} already exists in settings table (detected via error)")
            else:
                print(f"✗ Error adding {col_name} column: {e}")
                raise


def downgrade():
    """Remove Peppol settings columns from settings table"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    if 'settings' not in existing_tables:
        return
    
    settings_columns = {c['name'] for c in inspector.get_columns('settings')}
    
    columns_to_drop = [
        "peppol_provider",
        "peppol_access_point_timeout",
        "peppol_access_point_token",
        "peppol_access_point_url",
        "peppol_sender_country",
        "peppol_sender_scheme_id",
        "peppol_sender_endpoint_id",
        "peppol_enabled",
    ]
    
    for col_name in columns_to_drop:
        if col_name not in settings_columns:
            print(f"⊘ Column {col_name} does not exist in settings table, skipping")
            continue
        
        try:
            op.drop_column("settings", col_name)
            print(f"✓ Dropped {col_name} column from settings table")
        except Exception as e:
            error_msg = str(e)
            if 'does not exist' in error_msg.lower() or 'no such column' in error_msg.lower():
                print(f"⊘ Column {col_name} does not exist in settings table (detected via error)")
            else:
                print(f"⚠ Warning: Could not drop {col_name} column: {e}")

