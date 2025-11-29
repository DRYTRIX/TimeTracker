"""Add password_change_required to users table

Revision ID: 074_password_change_required
Revises: 073_ai_features_gps_tracking
Create Date: 2025-01-27

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '074_password_change_required'
down_revision = '073_ai_features_gps_tracking'
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    try:
        return column_name in [col['name'] for col in inspector.get_columns(table_name)]
    except Exception:
        return False


def upgrade():
    """Add password_change_required column to users table"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Ensure users table exists
    if 'users' not in inspector.get_table_names():
        return

    # Add password_change_required column if missing
    if not _has_column(inspector, 'users', 'password_change_required'):
        op.add_column('users', sa.Column('password_change_required', sa.Boolean(), nullable=False, server_default='false'))


def downgrade():
    """Remove password_change_required column from users table"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if 'users' not in inspector.get_table_names():
        return

    # Drop password_change_required column if exists
    if _has_column(inspector, 'users', 'password_change_required'):
        op.drop_column('users', 'password_change_required')

