"""add user avatar filename column

Revision ID: 020
Revises: 019
Create Date: 2025-10-21 00:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '020'
down_revision = '019'
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return column_name in [col['name'] for col in inspector.get_columns(table_name)]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if 'users' not in inspector.get_table_names():
        return

    if not _has_column(inspector, 'users', 'avatar_filename'):
        op.add_column('users', sa.Column('avatar_filename', sa.String(length=255), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if 'users' not in inspector.get_table_names():
        return

    if _has_column(inspector, 'users', 'avatar_filename'):
        try:
            op.drop_column('users', 'avatar_filename')
        except Exception:
            pass


