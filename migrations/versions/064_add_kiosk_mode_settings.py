"""Add kiosk mode settings

Revision ID: 064
Revises: 063
Create Date: 2025-01-27

This migration adds kiosk mode settings to the settings table.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '064'
down_revision = '063'
branch_labels = None
depends_on = None


def upgrade():
    """Add kiosk mode settings"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    if 'settings' not in existing_tables:
        return
    
    settings_columns = {c['name'] for c in inspector.get_columns('settings')}
    
    columns_to_add = [
        ('kiosk_mode_enabled', sa.Column('kiosk_mode_enabled', sa.Boolean(), nullable=False, server_default='0')),
        ('kiosk_auto_logout_minutes', sa.Column('kiosk_auto_logout_minutes', sa.Integer(), nullable=False, server_default='15')),
        ('kiosk_allow_camera_scanning', sa.Column('kiosk_allow_camera_scanning', sa.Boolean(), nullable=False, server_default='1')),
        ('kiosk_require_reason_for_adjustments', sa.Column('kiosk_require_reason_for_adjustments', sa.Boolean(), nullable=False, server_default='0')),
        ('kiosk_default_movement_type', sa.Column('kiosk_default_movement_type', sa.String(20), nullable=False, server_default='adjustment')),
    ]
    
    for col_name, col_def in columns_to_add:
        if col_name in settings_columns:
            print(f"✓ Column {col_name} already exists in settings table")
            continue
        
        try:
            op.add_column('settings', col_def)
            print(f"✓ Added {col_name} column to settings table")
        except Exception as e:
            error_msg = str(e)
            if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
                print(f"✓ Column {col_name} already exists in settings table (detected via error)")
            else:
                print(f"✗ Error adding {col_name} column: {e}")
                raise


def downgrade():
    """Remove kiosk mode settings"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    if 'settings' not in existing_tables:
        return
    
    settings_columns = {c['name'] for c in inspector.get_columns('settings')}
    
    columns_to_drop = [
        'kiosk_default_movement_type',
        'kiosk_require_reason_for_adjustments',
        'kiosk_allow_camera_scanning',
        'kiosk_auto_logout_minutes',
        'kiosk_mode_enabled',
    ]
    
    for col_name in columns_to_drop:
        if col_name not in settings_columns:
            print(f"⊘ Column {col_name} does not exist in settings table, skipping")
            continue
        
        try:
            op.drop_column('settings', col_name)
            print(f"✓ Dropped {col_name} column from settings table")
        except Exception as e:
            error_msg = str(e)
            if 'does not exist' in error_msg.lower() or 'no such column' in error_msg.lower():
                print(f"⊘ Column {col_name} does not exist in settings table (detected via error)")
            else:
                print(f"⚠ Warning: Could not drop {col_name} column: {e}")

