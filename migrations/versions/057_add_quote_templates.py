"""Add quote templates table

Revision ID: 057
Revises: 056
Create Date: 2025-01-27

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '057'
down_revision = '056'
branch_labels = None
depends_on = None


def upgrade():
    """Create quote_templates table"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    def _has_table(name: str) -> bool:
        try:
            return name in inspector.get_table_names()
        except Exception:
            return False

    def _has_index(table_name: str, index_name: str) -> bool:
        try:
            return any((idx.get("name") or "") == index_name for idx in inspector.get_indexes(table_name))
        except Exception:
            return False

    if not _has_table('quote_templates'):
        op.create_table('quote_templates',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('template_data', sa.Text(), nullable=True),
            sa.Column('default_tax_rate', sa.Numeric(precision=5, scale=2), nullable=True),
            sa.Column('default_currency_code', sa.String(length=3), nullable=True),
            sa.Column('default_payment_terms', sa.String(length=100), nullable=True),
            sa.Column('default_terms', sa.Text(), nullable=True),
            sa.Column('default_valid_until_days', sa.Integer(), nullable=True),
            sa.Column('default_requires_approval', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('default_approval_level', sa.Integer(), nullable=True),
            sa.Column('default_items', sa.Text(), nullable=True),
            sa.Column('created_by', sa.Integer(), nullable=False),
            sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
    else:
        print("[Migration 057] ℹ Table quote_templates already exists, skipping creation")

    # Ensure indexes exist (best-effort / idempotent)
    if _has_table('quote_templates'):
        if not _has_index('quote_templates', 'ix_quote_templates_name'):
            try:
                op.create_index('ix_quote_templates_name', 'quote_templates', ['name'], unique=False)
            except Exception:
                pass
        if not _has_index('quote_templates', 'ix_quote_templates_created_by'):
            try:
                op.create_index('ix_quote_templates_created_by', 'quote_templates', ['created_by'], unique=False)
            except Exception:
                pass


def downgrade():
    """Drop quote_templates table"""
    op.drop_index('ix_quote_templates_created_by', table_name='quote_templates')
    op.drop_index('ix_quote_templates_name', table_name='quote_templates')
    op.drop_table('quote_templates')

