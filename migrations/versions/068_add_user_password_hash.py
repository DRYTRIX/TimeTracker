"""Add password_hash to users table

Revision ID: 068_add_user_password_hash
Revises: 067_integration_credentials
Create Date: 2025-01-27

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '068_add_user_password_hash'
down_revision = '067_integration_credentials'
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    try:
        return column_name in [col['name'] for col in inspector.get_columns(table_name)]
    except Exception:
        return False


def upgrade():
    """Add password_hash column to users table"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Ensure users table exists
    if 'users' not in inspector.get_table_names():
        return

    # Add password_hash column if missing
    if not _has_column(inspector, 'users', 'password_hash'):
        op.add_column('users', sa.Column('password_hash', sa.String(length=255), nullable=True))


def downgrade():
    """Remove password_hash column from users table"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if 'users' not in inspector.get_table_names():
        return

    # Drop password_hash column if exists
    if _has_column(inspector, 'users', 'password_hash'):
        op.drop_column('users', 'password_hash')

