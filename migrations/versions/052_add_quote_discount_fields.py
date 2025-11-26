"""Add discount fields to quotes

Revision ID: 052
Revises: 051
Create Date: 2025-01-27

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '052'
down_revision = '051'
branch_labels = None
depends_on = None


def upgrade():
    """Add discount fields to quotes table"""
    # Add discount fields
    op.add_column('quotes',
        sa.Column('discount_type', sa.String(length=20), nullable=True)
    )
    op.add_column('quotes',
        sa.Column('discount_amount', sa.Numeric(precision=10, scale=2), nullable=True, server_default='0')
    )
    op.add_column('quotes',
        sa.Column('discount_reason', sa.String(length=500), nullable=True)
    )
    op.add_column('quotes',
        sa.Column('coupon_code', sa.String(length=50), nullable=True)
    )
    
    # Create index on coupon_code for faster lookups
    op.create_index('ix_quotes_coupon_code', 'quotes', ['coupon_code'], unique=False)


def downgrade():
    """Remove discount fields from quotes table"""
    # Drop index
    op.drop_index('ix_quotes_coupon_code', 'quotes')
    
    # Drop columns
    op.drop_column('quotes', 'coupon_code')
    op.drop_column('quotes', 'discount_reason')
    op.drop_column('quotes', 'discount_amount')
    op.drop_column('quotes', 'discount_type')

