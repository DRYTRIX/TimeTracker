"""Add quote attachments table

Revision ID: 055
Revises: 054
Create Date: 2025-01-27

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '055'
down_revision = '054'
branch_labels = None
depends_on = None


def upgrade():
    """Create quote_attachments table"""
    op.create_table('quote_attachments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('quote_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_visible_to_client', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('uploaded_by', sa.Integer(), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['quote_id'], ['quotes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_quote_attachments_quote_id', 'quote_attachments', ['quote_id'], unique=False)
    op.create_index('ix_quote_attachments_uploaded_by', 'quote_attachments', ['uploaded_by'], unique=False)


def downgrade():
    """Drop quote_attachments table"""
    op.drop_index('ix_quote_attachments_uploaded_by', table_name='quote_attachments')
    op.drop_index('ix_quote_attachments_quote_id', table_name='quote_attachments')
    op.drop_table('quote_attachments')

