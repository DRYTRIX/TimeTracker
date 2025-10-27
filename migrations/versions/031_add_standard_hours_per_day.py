"""Add standard_hours_per_day to users

Revision ID: 031
Revises: 030
Create Date: 2025-10-27 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '031'
down_revision = '030'
branch_labels = None
depends_on = None


def upgrade():
    """Add standard_hours_per_day column to users table"""
    op.add_column('users', 
        sa.Column('standard_hours_per_day', sa.Float(), nullable=False, server_default='8.0')
    )


def downgrade():
    """Remove standard_hours_per_day column from users table"""
    op.drop_column('users', 'standard_hours_per_day')

