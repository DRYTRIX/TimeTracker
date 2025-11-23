"""Add quote support to comments table

Revision ID: 054
Revises: 053
Create Date: 2025-01-27

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '054'
down_revision = '053'
branch_labels = None
depends_on = None


def upgrade():
    """Add quote_id and is_internal fields to comments table"""
    # Add quote_id column
    op.add_column('comments',
        sa.Column('quote_id', sa.Integer(), nullable=True)
    )
    
    # Add is_internal column (True = internal team comment, False = client-visible)
    op.add_column('comments',
        sa.Column('is_internal', sa.Boolean(), nullable=False, server_default='true')
    )
    
    # Create index on quote_id
    op.create_index('ix_comments_quote_id', 'comments', ['quote_id'], unique=False)
    
    # Add foreign key constraint
    op.create_foreign_key('fk_comments_quote_id', 'comments', 'quotes', ['quote_id'], ['id'], ondelete='CASCADE')


def downgrade():
    """Remove quote support from comments table"""
    # Drop foreign key
    op.drop_constraint('fk_comments_quote_id', 'comments', type_='foreignkey')
    
    # Drop index
    op.drop_index('ix_comments_quote_id', 'comments')
    
    # Drop columns
    op.drop_column('comments', 'is_internal')
    op.drop_column('comments', 'quote_id')

