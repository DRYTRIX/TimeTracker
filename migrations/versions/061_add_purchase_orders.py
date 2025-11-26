"""Add purchase order system

Revision ID: 061
Revises: 060
Create Date: 2025-01-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '061'
down_revision = '060'
branch_labels = None
depends_on = None


def upgrade():
    """Add purchase order tables"""
    
    # Create purchase_orders table
    op.create_table('purchase_orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('po_number', sa.String(length=50), nullable=False),
        sa.Column('supplier_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('order_date', sa.Date(), nullable=False),
        sa.Column('expected_delivery_date', sa.Date(), nullable=True),
        sa.Column('received_date', sa.Date(), nullable=True),
        sa.Column('subtotal', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'),
        sa.Column('tax_amount', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'),
        sa.Column('shipping_cost', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'),
        sa.Column('total_amount', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'),
        sa.Column('currency_code', sa.String(length=3), nullable=False, server_default='EUR'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('internal_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_purchase_orders_po_number', 'purchase_orders', ['po_number'], unique=True)
    op.create_index('ix_purchase_orders_supplier_id', 'purchase_orders', ['supplier_id'], unique=False)
    op.create_index('ix_purchase_orders_status', 'purchase_orders', ['status'], unique=False)
    op.create_index('ix_purchase_orders_order_date', 'purchase_orders', ['order_date'], unique=False)
    op.create_index('ix_purchase_orders_created_by', 'purchase_orders', ['created_by'], unique=False)
    
    # Create purchase_order_items table
    op.create_table('purchase_order_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('purchase_order_id', sa.Integer(), nullable=False),
        sa.Column('stock_item_id', sa.Integer(), nullable=True),
        sa.Column('supplier_stock_item_id', sa.Integer(), nullable=True),
        sa.Column('description', sa.String(length=500), nullable=False),
        sa.Column('supplier_sku', sa.String(length=100), nullable=True),
        sa.Column('quantity_ordered', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('quantity_received', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'),
        sa.Column('unit_cost', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('line_total', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency_code', sa.String(length=3), nullable=False, server_default='EUR'),
        sa.Column('warehouse_id', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['purchase_order_id'], ['purchase_orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['stock_item_id'], ['stock_items.id'], ),
        sa.ForeignKeyConstraint(['supplier_stock_item_id'], ['supplier_stock_items.id'], ),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_purchase_order_items_purchase_order_id', 'purchase_order_items', ['purchase_order_id'], unique=False)
    op.create_index('ix_purchase_order_items_stock_item_id', 'purchase_order_items', ['stock_item_id'], unique=False)
    op.create_index('ix_purchase_order_items_supplier_stock_item_id', 'purchase_order_items', ['supplier_stock_item_id'], unique=False)
    op.create_index('ix_purchase_order_items_warehouse_id', 'purchase_order_items', ['warehouse_id'], unique=False)


def downgrade():
    """Remove purchase order tables"""
    op.drop_index('ix_purchase_order_items_warehouse_id', table_name='purchase_order_items')
    op.drop_index('ix_purchase_order_items_supplier_stock_item_id', table_name='purchase_order_items')
    op.drop_index('ix_purchase_order_items_stock_item_id', table_name='purchase_order_items')
    op.drop_index('ix_purchase_order_items_purchase_order_id', table_name='purchase_order_items')
    op.drop_table('purchase_order_items')
    op.drop_index('ix_purchase_orders_created_by', table_name='purchase_orders')
    op.drop_index('ix_purchase_orders_order_date', table_name='purchase_orders')
    op.drop_index('ix_purchase_orders_status', table_name='purchase_orders')
    op.drop_index('ix_purchase_orders_supplier_id', table_name='purchase_orders')
    op.drop_index('ix_purchase_orders_po_number', table_name='purchase_orders')
    op.drop_table('purchase_orders')

