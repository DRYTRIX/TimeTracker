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
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    is_sqlite = conn.dialect.name == 'sqlite'
    existing_tables = inspector.get_table_names()
    
    if 'comments' not in existing_tables:
        return
    
    comments_columns = [col['name'] for col in inspector.get_columns('comments')]
    comments_indexes = [idx['name'] for idx in inspector.get_indexes('comments')]
    comments_fks = [fk['name'] for fk in inspector.get_foreign_keys('comments')]
    
    # Add quote_id column (idempotent)
    if 'quote_id' not in comments_columns:
        op.add_column('comments',
            sa.Column('quote_id', sa.Integer(), nullable=True)
        )
    
    # Add is_internal column (True = internal team comment, False = client-visible) (idempotent)
    if 'is_internal' not in comments_columns:
        op.add_column('comments',
            sa.Column('is_internal', sa.Boolean(), nullable=False, server_default='true')
        )
    
    # Create index on quote_id (idempotent)
    if 'quote_id' in comments_columns and 'ix_comments_quote_id' not in comments_indexes:
        op.create_index('ix_comments_quote_id', 'comments', ['quote_id'], unique=False)
    
    # Add foreign key constraint (idempotent)
    if 'quote_id' in comments_columns and 'fk_comments_quote_id' not in comments_fks:
        if is_sqlite:
            with op.batch_alter_table('comments', schema=None) as batch_op:
                batch_op.create_foreign_key('fk_comments_quote_id', 'quotes', ['quote_id'], ['id'])
        else:
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

