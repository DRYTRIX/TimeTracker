"""Increase invoice_prefix column length

Revision ID: 107_increase_invoice_prefix_length
Revises: 106_add_reportlab_template_json
Create Date: 2026-01-11

This migration increases the invoice_prefix column length from 10 to 50 characters
to allow longer invoice prefixes.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '107_increase_invoice_prefix_length'
down_revision = '106_add_reportlab_template_json'
branch_labels = None
depends_on = None


def upgrade():
    """Increase invoice_prefix column length from 10 to 50"""
    bind = op.get_bind()
    inspector = inspect(bind)
    is_sqlite = bind.dialect.name == 'sqlite'
    
    # Check if settings table exists
    if 'settings' not in inspector.get_table_names():
        return
    
    settings_cols = {c['name']: c for c in inspector.get_columns('settings')}
    
    # Check if invoice_prefix column exists and needs to be altered
    if 'invoice_prefix' in settings_cols:
        try:
            if is_sqlite:
                # SQLite requires batch_alter_table
                with op.batch_alter_table('settings', schema=None) as batch_op:
                    batch_op.alter_column('invoice_prefix',
                                        type_=sa.String(length=50),
                                        existing_type=sa.String(length=10),
                                        existing_nullable=False,
                                        existing_server_default='INV')
            else:
                # PostgreSQL/MySQL - use ALTER COLUMN
                op.alter_column('settings', 'invoice_prefix',
                              type_=sa.String(length=50),
                              existing_type=sa.String(length=10),
                              existing_nullable=False,
                              existing_server_default='INV')
            print("✓ Increased invoice_prefix column length from 10 to 50")
        except Exception as e:
            print(f"⚠ Warning altering invoice_prefix column: {e}")
    else:
        print("⚠ invoice_prefix column not found in settings table")


def downgrade():
    """Decrease invoice_prefix column length from 50 to 10"""
    bind = op.get_bind()
    inspector = inspect(bind)
    is_sqlite = bind.dialect.name == 'sqlite'
    
    # Check if settings table exists
    if 'settings' not in inspector.get_table_names():
        return
    
    settings_cols = {c['name']: c for c in inspector.get_columns('settings')}
    
    # Check if invoice_prefix column exists
    if 'invoice_prefix' in settings_cols:
        try:
            if is_sqlite:
                with op.batch_alter_table('settings', schema=None) as batch_op:
                    batch_op.alter_column('invoice_prefix',
                                        type_=sa.String(length=10),
                                        existing_type=sa.String(length=50),
                                        existing_nullable=False,
                                        existing_server_default='INV')
            else:
                op.alter_column('settings', 'invoice_prefix',
                              type_=sa.String(length=10),
                              existing_type=sa.String(length=50),
                              existing_nullable=False,
                              existing_server_default='INV')
            print("✓ Decreased invoice_prefix column length from 50 to 10")
        except Exception as e:
            print(f"⚠ Warning altering invoice_prefix column: {e}")
