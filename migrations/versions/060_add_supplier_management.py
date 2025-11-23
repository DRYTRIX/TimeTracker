"""Add supplier management system

Revision ID: 060
Revises: 059
Create Date: 2025-01-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '060'
down_revision = '059'
branch_labels = None
depends_on = None


def upgrade():
    """Add supplier management tables"""
    
    # Create suppliers table
    op.create_table('suppliers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('contact_person', sa.String(length=200), nullable=True),
        sa.Column('email', sa.String(length=200), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('website', sa.String(length=500), nullable=True),
        sa.Column('tax_id', sa.String(length=100), nullable=True),
        sa.Column('payment_terms', sa.String(length=100), nullable=True),
        sa.Column('currency_code', sa.String(length=3), nullable=False, server_default='EUR'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_suppliers_code', 'suppliers', ['code'], unique=True)
    op.create_index('ix_suppliers_created_by', 'suppliers', ['created_by'], unique=False)
    
    # Create supplier_stock_items table (many-to-many with pricing)
    op.create_table('supplier_stock_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('supplier_id', sa.Integer(), nullable=False),
        sa.Column('stock_item_id', sa.Integer(), nullable=False),
        sa.Column('supplier_sku', sa.String(length=100), nullable=True),
        sa.Column('supplier_name', sa.String(length=200), nullable=True),
        sa.Column('unit_cost', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('currency_code', sa.String(length=3), nullable=False, server_default='EUR'),
        sa.Column('minimum_order_quantity', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('lead_time_days', sa.Integer(), nullable=True),
        sa.Column('is_preferred', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['stock_item_id'], ['stock_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('supplier_id', 'stock_item_id', name='uq_supplier_stock_item')
    )
    op.create_index('ix_supplier_stock_items_supplier_id', 'supplier_stock_items', ['supplier_id'], unique=False)
    op.create_index('ix_supplier_stock_items_stock_item_id', 'supplier_stock_items', ['stock_item_id'], unique=False)


def downgrade():
    """Remove supplier management tables"""
    op.drop_index('ix_supplier_stock_items_stock_item_id', table_name='supplier_stock_items')
    op.drop_index('ix_supplier_stock_items_supplier_id', table_name='supplier_stock_items')
    op.drop_table('supplier_stock_items')
    op.drop_index('ix_suppliers_created_by', table_name='suppliers')
    op.drop_index('ix_suppliers_code', table_name='suppliers')
    op.drop_table('suppliers')

