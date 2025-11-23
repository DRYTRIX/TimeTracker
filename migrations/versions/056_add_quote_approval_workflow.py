"""Add quote approval workflow fields

Revision ID: 056
Revises: 055
Create Date: 2025-01-27

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '056'
down_revision = '055'
branch_labels = None
depends_on = None


def column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def index_exists(table_name, index_name):
    """Check if an index exists"""
    bind = op.get_bind()
    inspector = inspect(bind)
    indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
    return index_name in indexes


def constraint_exists(table_name, constraint_name):
    """Check if a foreign key constraint exists"""
    bind = op.get_bind()
    inspector = inspect(bind)
    fks = [fk['name'] for fk in inspector.get_foreign_keys(table_name)]
    return constraint_name in fks


def upgrade():
    """Add approval workflow fields to quotes table"""
    # Add approval status (if it doesn't exist)
    if not column_exists('quotes', 'approval_status'):
        op.add_column('quotes',
            sa.Column('approval_status', sa.String(length=20), nullable=False, server_default='not_required')
        )
    
    # Add approver fields (if they don't exist)
    if not column_exists('quotes', 'approved_by'):
        op.add_column('quotes',
            sa.Column('approved_by', sa.Integer(), nullable=True)
        )
    
    if not column_exists('quotes', 'approved_at'):
        op.add_column('quotes',
            sa.Column('approved_at', sa.DateTime(), nullable=True)
        )
    
    if not column_exists('quotes', 'rejected_by'):
        op.add_column('quotes',
            sa.Column('rejected_by', sa.Integer(), nullable=True)
        )
    
    # Note: rejected_at already exists from migration 051, so we skip it
    
    if not column_exists('quotes', 'rejection_reason'):
        op.add_column('quotes',
            sa.Column('rejection_reason', sa.Text(), nullable=True)
        )
    
    # Add indexes (if they don't exist)
    if not index_exists('quotes', 'ix_quotes_approval_status'):
        op.create_index('ix_quotes_approval_status', 'quotes', ['approval_status'], unique=False)
    
    if not index_exists('quotes', 'ix_quotes_approved_by'):
        op.create_index('ix_quotes_approved_by', 'quotes', ['approved_by'], unique=False)
    
    # Add foreign keys (if they don't exist)
    if not constraint_exists('quotes', 'fk_quotes_approved_by'):
        op.create_foreign_key('fk_quotes_approved_by', 'quotes', 'users', ['approved_by'], ['id'], ondelete='SET NULL')
    
    if not constraint_exists('quotes', 'fk_quotes_rejected_by'):
        op.create_foreign_key('fk_quotes_rejected_by', 'quotes', 'users', ['rejected_by'], ['id'], ondelete='SET NULL')


def downgrade():
    """Remove approval workflow fields from quotes table"""
    # Drop foreign keys
    if constraint_exists('quotes', 'fk_quotes_rejected_by'):
        op.drop_constraint('fk_quotes_rejected_by', 'quotes', type_='foreignkey')
    if constraint_exists('quotes', 'fk_quotes_approved_by'):
        op.drop_constraint('fk_quotes_approved_by', 'quotes', type_='foreignkey')
    
    # Drop indexes
    if index_exists('quotes', 'ix_quotes_approved_by'):
        op.drop_index('ix_quotes_approved_by', table_name='quotes')
    if index_exists('quotes', 'ix_quotes_approval_status'):
        op.drop_index('ix_quotes_approval_status', table_name='quotes')
    
    # Drop columns
    if column_exists('quotes', 'rejection_reason'):
        op.drop_column('quotes', 'rejection_reason')
    if column_exists('quotes', 'rejected_by'):
        op.drop_column('quotes', 'rejected_by')
    if column_exists('quotes', 'approved_at'):
        op.drop_column('quotes', 'approved_at')
    if column_exists('quotes', 'approved_by'):
        op.drop_column('quotes', 'approved_by')
    if column_exists('quotes', 'approval_status'):
        op.drop_column('quotes', 'approval_status')

