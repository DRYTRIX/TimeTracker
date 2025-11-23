"""Add payment terms to quotes

Revision ID: 053
Revises: 052
Create Date: 2025-01-27

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '053'
down_revision = '052'
branch_labels = None
depends_on = None


def upgrade():
    """Add payment_terms field to quotes table"""
    op.add_column('quotes',
        sa.Column('payment_terms', sa.String(length=100), nullable=True)
    )


def downgrade():
    """Remove payment_terms field from quotes table"""
    op.drop_column('quotes', 'payment_terms')

