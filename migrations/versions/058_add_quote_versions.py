"""Add quote versions table for revision history

Revision ID: 058
Revises: 057
Create Date: 2025-01-27

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '058'
down_revision = '057'
branch_labels = None
depends_on = None


def upgrade():
    """Create quote_versions table"""
    op.create_table('quote_versions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('quote_id', sa.Integer(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('quote_data', sa.Text(), nullable=False),
        sa.Column('changed_by', sa.Integer(), nullable=False),
        sa.Column('changed_at', sa.DateTime(), nullable=False),
        sa.Column('change_summary', sa.String(length=500), nullable=True),
        sa.Column('fields_changed', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['quote_id'], ['quotes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['changed_by'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_quote_versions_quote_id', 'quote_versions', ['quote_id'], unique=False)
    op.create_index('ix_quote_versions_changed_by', 'quote_versions', ['changed_by'], unique=False)
    op.create_index('ix_quote_versions_version_number', 'quote_versions', ['quote_id', 'version_number'], unique=True)


def downgrade():
    """Drop quote_versions table"""
    op.drop_index('ix_quote_versions_version_number', table_name='quote_versions')
    op.drop_index('ix_quote_versions_changed_by', table_name='quote_versions')
    op.drop_index('ix_quote_versions_quote_id', table_name='quote_versions')
    op.drop_table('quote_versions')

