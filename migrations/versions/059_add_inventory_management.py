"""Add inventory management system

Revision ID: 059
Revises: 058
Create Date: 2025-01-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '059'
down_revision = '058'
branch_labels = None
depends_on = None


def upgrade():
    """Add inventory management tables and fields"""
    
    # Create warehouses table
    op.create_table('warehouses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('contact_person', sa.String(length=200), nullable=True),
        sa.Column('contact_email', sa.String(length=200), nullable=True),
        sa.Column('contact_phone', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_warehouses_code', 'warehouses', ['code'], unique=True)
    op.create_index('ix_warehouses_created_by', 'warehouses', ['created_by'], unique=False)
    
    # Create stock_items table
    op.create_table('stock_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sku', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('unit', sa.String(length=20), nullable=False, server_default='pcs'),
        sa.Column('default_cost', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('default_price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('currency_code', sa.String(length=3), nullable=False, server_default='EUR'),
        sa.Column('barcode', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('is_trackable', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('reorder_point', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('reorder_quantity', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('supplier', sa.String(length=200), nullable=True),
        sa.Column('supplier_sku', sa.String(length=100), nullable=True),
        sa.Column('image_url', sa.String(length=500), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_stock_items_sku', 'stock_items', ['sku'], unique=True)
    op.create_index('ix_stock_items_barcode', 'stock_items', ['barcode'], unique=False)
    op.create_index('ix_stock_items_category', 'stock_items', ['category'], unique=False)
    op.create_index('ix_stock_items_created_by', 'stock_items', ['created_by'], unique=False)
    
    # Create warehouse_stock table
    op.create_table('warehouse_stock',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('warehouse_id', sa.Integer(), nullable=False),
        sa.Column('stock_item_id', sa.Integer(), nullable=False),
        sa.Column('quantity_on_hand', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'),
        sa.Column('quantity_reserved', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'),
        sa.Column('location', sa.String(length=100), nullable=True),
        sa.Column('last_counted_at', sa.DateTime(), nullable=True),
        sa.Column('last_counted_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['stock_item_id'], ['stock_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['last_counted_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('warehouse_id', 'stock_item_id', name='uq_warehouse_stock')
    )
    op.create_index('ix_warehouse_stock_warehouse_id', 'warehouse_stock', ['warehouse_id'], unique=False)
    op.create_index('ix_warehouse_stock_stock_item_id', 'warehouse_stock', ['stock_item_id'], unique=False)
    
    # Create stock_movements table
    op.create_table('stock_movements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('movement_type', sa.String(length=20), nullable=False),
        sa.Column('stock_item_id', sa.Integer(), nullable=False),
        sa.Column('warehouse_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('reference_type', sa.String(length=50), nullable=True),
        sa.Column('reference_id', sa.Integer(), nullable=True),
        sa.Column('unit_cost', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('reason', sa.String(length=500), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('moved_by', sa.Integer(), nullable=False),
        sa.Column('moved_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['stock_item_id'], ['stock_items.id'], ),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ),
        sa.ForeignKeyConstraint(['moved_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_stock_movements_movement_type', 'stock_movements', ['movement_type'], unique=False)
    op.create_index('ix_stock_movements_stock_item_id', 'stock_movements', ['stock_item_id'], unique=False)
    op.create_index('ix_stock_movements_warehouse_id', 'stock_movements', ['warehouse_id'], unique=False)
    op.create_index('ix_stock_movements_reference_type', 'stock_movements', ['reference_type'], unique=False)
    op.create_index('ix_stock_movements_reference_id', 'stock_movements', ['reference_id'], unique=False)
    op.create_index('ix_stock_movements_moved_by', 'stock_movements', ['moved_by'], unique=False)
    op.create_index('ix_stock_movements_moved_at', 'stock_movements', ['moved_at'], unique=False)
    op.create_index('ix_stock_movements_reference', 'stock_movements', ['reference_type', 'reference_id'], unique=False)
    op.create_index('ix_stock_movements_item_date', 'stock_movements', ['stock_item_id', 'moved_at'], unique=False)
    
    # Create stock_reservations table
    op.create_table('stock_reservations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('stock_item_id', sa.Integer(), nullable=False),
        sa.Column('warehouse_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('reservation_type', sa.String(length=20), nullable=False),
        sa.Column('reservation_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='reserved'),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('reserved_by', sa.Integer(), nullable=False),
        sa.Column('reserved_at', sa.DateTime(), nullable=False),
        sa.Column('fulfilled_at', sa.DateTime(), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['stock_item_id'], ['stock_items.id'], ),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ),
        sa.ForeignKeyConstraint(['reserved_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_stock_reservations_stock_item_id', 'stock_reservations', ['stock_item_id'], unique=False)
    op.create_index('ix_stock_reservations_warehouse_id', 'stock_reservations', ['warehouse_id'], unique=False)
    op.create_index('ix_stock_reservations_reservation_type', 'stock_reservations', ['reservation_type'], unique=False)
    op.create_index('ix_stock_reservations_reservation_id', 'stock_reservations', ['reservation_id'], unique=False)
    op.create_index('ix_stock_reservations_reserved_by', 'stock_reservations', ['reserved_by'], unique=False)
    op.create_index('ix_stock_reservations_expires_at', 'stock_reservations', ['expires_at'], unique=False)
    op.create_index('ix_stock_reservations_reservation', 'stock_reservations', ['reservation_type', 'reservation_id'], unique=False)
    
    # Create project_stock_allocations table
    op.create_table('project_stock_allocations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('stock_item_id', sa.Integer(), nullable=False),
        sa.Column('warehouse_id', sa.Integer(), nullable=False),
        sa.Column('quantity_allocated', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('quantity_used', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'),
        sa.Column('allocated_by', sa.Integer(), nullable=False),
        sa.Column('allocated_at', sa.DateTime(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['stock_item_id'], ['stock_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ),
        sa.ForeignKeyConstraint(['allocated_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_project_stock_allocations_project_id', 'project_stock_allocations', ['project_id'], unique=False)
    op.create_index('ix_project_stock_allocations_stock_item_id', 'project_stock_allocations', ['stock_item_id'], unique=False)
    op.create_index('ix_project_stock_allocations_warehouse_id', 'project_stock_allocations', ['warehouse_id'], unique=False)
    op.create_index('ix_project_stock_allocations_allocated_by', 'project_stock_allocations', ['allocated_by'], unique=False)
    
    # Add inventory fields to quote_items (idempotent)
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    is_sqlite = conn.dialect.name == 'sqlite'
    existing_tables = inspector.get_table_names()
    
    if 'quote_items' in existing_tables:
        quote_items_columns = [col['name'] for col in inspector.get_columns('quote_items')]
        quote_items_indexes = [idx['name'] for idx in inspector.get_indexes('quote_items')]
        quote_items_fks = [fk['name'] for fk in inspector.get_foreign_keys('quote_items')]
        
        if 'stock_item_id' not in quote_items_columns:
            op.add_column('quote_items', sa.Column('stock_item_id', sa.Integer(), nullable=True))
        if 'warehouse_id' not in quote_items_columns:
            op.add_column('quote_items', sa.Column('warehouse_id', sa.Integer(), nullable=True))
        if 'is_stock_item' not in quote_items_columns:
            op.add_column('quote_items', sa.Column('is_stock_item', sa.Boolean(), nullable=False, server_default='0'))
        
        if 'stock_item_id' in quote_items_columns and 'ix_quote_items_stock_item_id' not in quote_items_indexes:
            op.create_index('ix_quote_items_stock_item_id', 'quote_items', ['stock_item_id'], unique=False)
        
        if is_sqlite:
            with op.batch_alter_table('quote_items', schema=None) as batch_op:
                if 'stock_item_id' in quote_items_columns and 'fk_quote_items_stock_item_id' not in quote_items_fks:
                    batch_op.create_foreign_key('fk_quote_items_stock_item_id', 'stock_items', ['stock_item_id'], ['id'])
                if 'warehouse_id' in quote_items_columns and 'fk_quote_items_warehouse_id' not in quote_items_fks:
                    batch_op.create_foreign_key('fk_quote_items_warehouse_id', 'warehouses', ['warehouse_id'], ['id'])
        else:
            if 'stock_item_id' in quote_items_columns and 'fk_quote_items_stock_item_id' not in quote_items_fks:
                op.create_foreign_key('fk_quote_items_stock_item_id', 'quote_items', 'stock_items', ['stock_item_id'], ['id'])
            if 'warehouse_id' in quote_items_columns and 'fk_quote_items_warehouse_id' not in quote_items_fks:
                op.create_foreign_key('fk_quote_items_warehouse_id', 'quote_items', 'warehouses', ['warehouse_id'], ['id'])
    
    # Add inventory fields to invoice_items (idempotent)
    if 'invoice_items' in existing_tables:
        invoice_items_columns = [col['name'] for col in inspector.get_columns('invoice_items')]
        invoice_items_indexes = [idx['name'] for idx in inspector.get_indexes('invoice_items')]
        invoice_items_fks = [fk['name'] for fk in inspector.get_foreign_keys('invoice_items')]
        
        if 'stock_item_id' not in invoice_items_columns:
            op.add_column('invoice_items', sa.Column('stock_item_id', sa.Integer(), nullable=True))
        if 'warehouse_id' not in invoice_items_columns:
            op.add_column('invoice_items', sa.Column('warehouse_id', sa.Integer(), nullable=True))
        if 'is_stock_item' not in invoice_items_columns:
            op.add_column('invoice_items', sa.Column('is_stock_item', sa.Boolean(), nullable=False, server_default='0'))
        
        if 'stock_item_id' in invoice_items_columns and 'ix_invoice_items_stock_item_id' not in invoice_items_indexes:
            op.create_index('ix_invoice_items_stock_item_id', 'invoice_items', ['stock_item_id'], unique=False)
        
        if is_sqlite:
            with op.batch_alter_table('invoice_items', schema=None) as batch_op:
                if 'stock_item_id' in invoice_items_columns and 'fk_invoice_items_stock_item_id' not in invoice_items_fks:
                    batch_op.create_foreign_key('fk_invoice_items_stock_item_id', 'stock_items', ['stock_item_id'], ['id'])
                if 'warehouse_id' in invoice_items_columns and 'fk_invoice_items_warehouse_id' not in invoice_items_fks:
                    batch_op.create_foreign_key('fk_invoice_items_warehouse_id', 'warehouses', ['warehouse_id'], ['id'])
        else:
            if 'stock_item_id' in invoice_items_columns and 'fk_invoice_items_stock_item_id' not in invoice_items_fks:
                op.create_foreign_key('fk_invoice_items_stock_item_id', 'invoice_items', 'stock_items', ['stock_item_id'], ['id'])
            if 'warehouse_id' in invoice_items_columns and 'fk_invoice_items_warehouse_id' not in invoice_items_fks:
                op.create_foreign_key('fk_invoice_items_warehouse_id', 'invoice_items', 'warehouses', ['warehouse_id'], ['id'])
    
    # Add inventory field to extra_goods (idempotent)
    if 'extra_goods' in existing_tables:
        extra_goods_columns = [col['name'] for col in inspector.get_columns('extra_goods')]
        extra_goods_indexes = [idx['name'] for idx in inspector.get_indexes('extra_goods')]
        extra_goods_fks = [fk['name'] for fk in inspector.get_foreign_keys('extra_goods')]
        
        if 'stock_item_id' not in extra_goods_columns:
            op.add_column('extra_goods', sa.Column('stock_item_id', sa.Integer(), nullable=True))
        
        if 'stock_item_id' in extra_goods_columns and 'ix_extra_goods_stock_item_id' not in extra_goods_indexes:
            op.create_index('ix_extra_goods_stock_item_id', 'extra_goods', ['stock_item_id'], unique=False)
        
        if 'stock_item_id' in extra_goods_columns and 'fk_extra_goods_stock_item_id' not in extra_goods_fks:
            if is_sqlite:
                with op.batch_alter_table('extra_goods', schema=None) as batch_op:
                    batch_op.create_foreign_key('fk_extra_goods_stock_item_id', 'stock_items', ['stock_item_id'], ['id'])
            else:
                op.create_foreign_key('fk_extra_goods_stock_item_id', 'extra_goods', 'stock_items', ['stock_item_id'], ['id'])


def downgrade():
    """Remove inventory management tables and fields"""
    
    # Remove inventory fields from extra_goods
    op.drop_constraint('fk_extra_goods_stock_item_id', 'extra_goods', type_='foreignkey')
    op.drop_index('ix_extra_goods_stock_item_id', table_name='extra_goods')
    op.drop_column('extra_goods', 'stock_item_id')
    
    # Remove inventory fields from invoice_items
    op.drop_constraint('fk_invoice_items_warehouse_id', 'invoice_items', type_='foreignkey')
    op.drop_constraint('fk_invoice_items_stock_item_id', 'invoice_items', type_='foreignkey')
    op.drop_index('ix_invoice_items_stock_item_id', table_name='invoice_items')
    op.drop_column('invoice_items', 'is_stock_item')
    op.drop_column('invoice_items', 'warehouse_id')
    op.drop_column('invoice_items', 'stock_item_id')
    
    # Remove inventory fields from quote_items
    op.drop_constraint('fk_quote_items_warehouse_id', 'quote_items', type_='foreignkey')
    op.drop_constraint('fk_quote_items_stock_item_id', 'quote_items', type_='foreignkey')
    op.drop_index('ix_quote_items_stock_item_id', table_name='quote_items')
    op.drop_column('quote_items', 'is_stock_item')
    op.drop_column('quote_items', 'warehouse_id')
    op.drop_column('quote_items', 'stock_item_id')
    
    # Drop project_stock_allocations table
    op.drop_index('ix_project_stock_allocations_allocated_by', table_name='project_stock_allocations')
    op.drop_index('ix_project_stock_allocations_warehouse_id', table_name='project_stock_allocations')
    op.drop_index('ix_project_stock_allocations_stock_item_id', table_name='project_stock_allocations')
    op.drop_index('ix_project_stock_allocations_project_id', table_name='project_stock_allocations')
    op.drop_table('project_stock_allocations')
    
    # Drop stock_reservations table
    op.drop_index('ix_stock_reservations_reservation', table_name='stock_reservations')
    op.drop_index('ix_stock_reservations_expires_at', table_name='stock_reservations')
    op.drop_index('ix_stock_reservations_reserved_by', table_name='stock_reservations')
    op.drop_index('ix_stock_reservations_reservation_id', table_name='stock_reservations')
    op.drop_index('ix_stock_reservations_reservation_type', table_name='stock_reservations')
    op.drop_index('ix_stock_reservations_warehouse_id', table_name='stock_reservations')
    op.drop_index('ix_stock_reservations_stock_item_id', table_name='stock_reservations')
    op.drop_table('stock_reservations')
    
    # Drop stock_movements table
    op.drop_index('ix_stock_movements_item_date', table_name='stock_movements')
    op.drop_index('ix_stock_movements_reference', table_name='stock_movements')
    op.drop_index('ix_stock_movements_moved_at', table_name='stock_movements')
    op.drop_index('ix_stock_movements_moved_by', table_name='stock_movements')
    op.drop_index('ix_stock_movements_reference_id', table_name='stock_movements')
    op.drop_index('ix_stock_movements_reference_type', table_name='stock_movements')
    op.drop_index('ix_stock_movements_warehouse_id', table_name='stock_movements')
    op.drop_index('ix_stock_movements_stock_item_id', table_name='stock_movements')
    op.drop_index('ix_stock_movements_movement_type', table_name='stock_movements')
    op.drop_table('stock_movements')
    
    # Drop warehouse_stock table
    op.drop_index('ix_warehouse_stock_stock_item_id', table_name='warehouse_stock')
    op.drop_index('ix_warehouse_stock_warehouse_id', table_name='warehouse_stock')
    op.drop_table('warehouse_stock')
    
    # Drop stock_items table
    op.drop_index('ix_stock_items_created_by', table_name='stock_items')
    op.drop_index('ix_stock_items_category', table_name='stock_items')
    op.drop_index('ix_stock_items_barcode', table_name='stock_items')
    op.drop_index('ix_stock_items_sku', table_name='stock_items')
    op.drop_table('stock_items')
    
    # Drop warehouses table
    op.drop_index('ix_warehouses_created_by', table_name='warehouses')
    op.drop_index('ix_warehouses_code', table_name='warehouses')
    op.drop_table('warehouses')

