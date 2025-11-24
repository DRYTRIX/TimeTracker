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
    # Add kiosk mode settings columns
    op.add_column('settings', sa.Column('kiosk_mode_enabled', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('settings', sa.Column('kiosk_auto_logout_minutes', sa.Integer(), nullable=False, server_default='15'))
    op.add_column('settings', sa.Column('kiosk_allow_camera_scanning', sa.Boolean(), nullable=False, server_default='1'))
    op.add_column('settings', sa.Column('kiosk_require_reason_for_adjustments', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('settings', sa.Column('kiosk_default_movement_type', sa.String(20), nullable=False, server_default='adjustment'))


def downgrade():
    """Remove kiosk mode settings"""
    op.drop_column('settings', 'kiosk_default_movement_type')
    op.drop_column('settings', 'kiosk_require_reason_for_adjustments')
    op.drop_column('settings', 'kiosk_allow_camera_scanning')
    op.drop_column('settings', 'kiosk_auto_logout_minutes')
    op.drop_column('settings', 'kiosk_mode_enabled')

