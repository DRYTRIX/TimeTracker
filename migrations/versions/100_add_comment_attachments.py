"""Add comment attachments table

Revision ID: 100_add_comment_attachments
Revises: 099_add_peppol_settings_columns
Create Date: 2025-01-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '100_add_comment_attachments'
down_revision = '099_add_peppol_settings_columns'
branch_labels = None
depends_on = None


def upgrade():
    """Create comment_attachments table"""
    op.create_table(
        'comment_attachments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('comment_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=True),
        sa.Column('uploaded_by', sa.Integer(), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['comment_id'], ['comments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_comment_attachments_comment_id'), 'comment_attachments', ['comment_id'], unique=False)
    op.create_index(op.f('ix_comment_attachments_uploaded_by'), 'comment_attachments', ['uploaded_by'], unique=False)


def downgrade():
    """Drop comment_attachments table"""
    op.drop_index(op.f('ix_comment_attachments_uploaded_by'), table_name='comment_attachments')
    op.drop_index(op.f('ix_comment_attachments_comment_id'), table_name='comment_attachments')
    op.drop_table('comment_attachments')
