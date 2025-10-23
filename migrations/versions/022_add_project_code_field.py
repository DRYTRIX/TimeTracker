"""Add short project code field for compact identifiers

Revision ID: 023
Revises: 022
Create Date: 2025-10-23 00:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '023'
down_revision = '022'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    dialect_name = bind.dialect.name if bind else 'generic'

    # Add code column if not present
    with op.batch_alter_table('projects') as batch_op:
        batch_op.add_column(sa.Column('code', sa.String(length=20), nullable=True))
        try:
            batch_op.create_unique_constraint('uq_projects_code', ['code'])
        except Exception:
            # Some dialects may not support unique with NULLs the same way; ignore if exists
            pass
        try:
            batch_op.create_index('ix_projects_code', ['code'])
        except Exception:
            pass


def downgrade():
    with op.batch_alter_table('projects') as batch_op:
        try:
            batch_op.drop_index('ix_projects_code')
        except Exception:
            pass
        try:
            batch_op.drop_constraint('uq_projects_code', type_='unique')
        except Exception:
            pass
        try:
            batch_op.drop_column('code')
        except Exception:
            pass


