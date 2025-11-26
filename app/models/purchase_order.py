"""Purchase Order models for inventory management"""
from datetime import datetime
from decimal import Decimal
from app import db


class PurchaseOrder(db.Model):
    """PurchaseOrder model - represents a purchase order to a supplier"""
    
    __tablename__ = 'purchase_orders'
    
    id = db.Column(db.Integer, primary_key=True)
    po_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False, index=True)
    status = db.Column(db.String(20), default='draft', nullable=False, index=True)  # draft, sent, confirmed, received, cancelled
    order_date = db.Column(db.Date, nullable=False, index=True)
    expected_delivery_date = db.Column(db.Date, nullable=True)
    received_date = db.Column(db.Date, nullable=True)
    
    # Financial
    subtotal = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    tax_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    shipping_cost = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    currency_code = db.Column(db.String(3), nullable=False, default='EUR')
    
    # Metadata
    notes = db.Column(db.Text, nullable=True)
    internal_notes = db.Column(db.Text, nullable=True)  # Not visible to supplier
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Relationships
    items = db.relationship('PurchaseOrderItem', backref='purchase_order', lazy='dynamic', cascade='all, delete-orphan')
    
    def __init__(self, po_number, supplier_id, order_date, created_by, expected_delivery_date=None,
                 notes=None, internal_notes=None, currency_code='EUR'):
        self.po_number = po_number.strip().upper()
        self.supplier_id = supplier_id
        self.order_date = order_date
        self.expected_delivery_date = expected_delivery_date
        self.created_by = created_by
        self.notes = notes.strip() if notes else None
        self.internal_notes = internal_notes.strip() if internal_notes else None
        self.currency_code = currency_code.upper()
        self.status = 'draft'
        self.subtotal = Decimal('0')
        self.tax_amount = Decimal('0')
        self.shipping_cost = Decimal('0')
        self.total_amount = Decimal('0')
    
    def __repr__(self):
        return f'<PurchaseOrder {self.po_number} ({self.status})>'
    
    def calculate_totals(self):
        """Calculate subtotal, tax, and total from items"""
        self.subtotal = sum(item.line_total for item in self.items)
        # Tax calculation can be added later if needed
        self.total_amount = self.subtotal + self.tax_amount + self.shipping_cost
        self.updated_at = datetime.utcnow()
    
    def mark_as_sent(self):
        """Mark purchase order as sent to supplier"""
        if self.status == 'draft':
            self.status = 'sent'
            self.updated_at = datetime.utcnow()
    
    def mark_as_received(self, received_date=None):
        """Mark purchase order as received"""
        # Allow receiving from draft, sent, or confirmed status
        if self.status not in ['received', 'cancelled']:
            self.status = 'received'
            self.received_date = received_date or datetime.utcnow().date()
            self.updated_at = datetime.utcnow()
            
            # Create stock movements for received items
            for item in self.items:
                if item.stock_item_id and item.quantity_received and item.quantity_received > 0:
                    from .stock_movement import StockMovement
                    # Use warehouse from item, or get first active warehouse
                    warehouse_id = item.warehouse_id
                    if not warehouse_id:
                        from .warehouse import Warehouse
                        first_warehouse = Warehouse.query.filter_by(is_active=True).first()
                        warehouse_id = first_warehouse.id if first_warehouse else None
                    
                    if warehouse_id:
                        StockMovement.record_movement(
                            movement_type='purchase',
                            stock_item_id=item.stock_item_id,
                            warehouse_id=warehouse_id,
                            quantity=item.quantity_received,
                            moved_by=self.created_by,
                            reason=f'Purchase Order {self.po_number}',
                            reference_type='purchase_order',
                            reference_id=self.id,
                            unit_cost=item.unit_cost,
                            update_stock=True
                        )
    
    def cancel(self):
        """Cancel purchase order"""
        if self.status not in ['received', 'cancelled']:
            self.status = 'cancelled'
            self.updated_at = datetime.utcnow()
    
    def to_dict(self):
        """Convert purchase order to dictionary"""
        return {
            'id': self.id,
            'po_number': self.po_number,
            'supplier_id': self.supplier_id,
            'status': self.status,
            'order_date': self.order_date.isoformat() if self.order_date else None,
            'expected_delivery_date': self.expected_delivery_date.isoformat() if self.expected_delivery_date else None,
            'received_date': self.received_date.isoformat() if self.received_date else None,
            'subtotal': float(self.subtotal),
            'tax_amount': float(self.tax_amount),
            'shipping_cost': float(self.shipping_cost),
            'total_amount': float(self.total_amount),
            'currency_code': self.currency_code,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by
        }


class PurchaseOrderItem(db.Model):
    """PurchaseOrderItem model - items in a purchase order"""
    
    __tablename__ = 'purchase_order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    purchase_order_id = db.Column(db.Integer, db.ForeignKey('purchase_orders.id'), nullable=False, index=True)
    stock_item_id = db.Column(db.Integer, db.ForeignKey('stock_items.id'), nullable=True, index=True)
    supplier_stock_item_id = db.Column(db.Integer, db.ForeignKey('supplier_stock_items.id'), nullable=True, index=True)
    
    # Item details
    description = db.Column(db.String(500), nullable=False)
    supplier_sku = db.Column(db.String(100), nullable=True)
    quantity_ordered = db.Column(db.Numeric(10, 2), nullable=False)
    quantity_received = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    unit_cost = db.Column(db.Numeric(10, 2), nullable=False)
    line_total = db.Column(db.Numeric(10, 2), nullable=False)
    currency_code = db.Column(db.String(3), nullable=False, default='EUR')
    
    # Warehouse destination
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=True, index=True)
    
    # Notes
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __init__(self, purchase_order_id, description, quantity_ordered, unit_cost, 
                 stock_item_id=None, supplier_stock_item_id=None, supplier_sku=None,
                 warehouse_id=None, notes=None, currency_code='EUR'):
        self.purchase_order_id = purchase_order_id
        self.stock_item_id = stock_item_id
        self.supplier_stock_item_id = supplier_stock_item_id
        self.description = description.strip()
        self.supplier_sku = supplier_sku.strip() if supplier_sku else None
        self.quantity_ordered = Decimal(str(quantity_ordered))
        self.quantity_received = Decimal('0')
        self.unit_cost = Decimal(str(unit_cost))
        self.line_total = self.quantity_ordered * self.unit_cost
        self.warehouse_id = warehouse_id
        self.notes = notes.strip() if notes else None
        self.currency_code = currency_code.upper()
    
    def __repr__(self):
        return f'<PurchaseOrderItem {self.description} ({self.quantity_ordered})>'
    
    def update_line_total(self):
        """Recalculate line total"""
        self.line_total = self.quantity_ordered * self.unit_cost
        self.updated_at = datetime.utcnow()
    
    def to_dict(self):
        """Convert purchase order item to dictionary"""
        return {
            'id': self.id,
            'purchase_order_id': self.purchase_order_id,
            'stock_item_id': self.stock_item_id,
            'supplier_stock_item_id': self.supplier_stock_item_id,
            'description': self.description,
            'supplier_sku': self.supplier_sku,
            'quantity_ordered': float(self.quantity_ordered),
            'quantity_received': float(self.quantity_received),
            'unit_cost': float(self.unit_cost),
            'line_total': float(self.line_total),
            'currency_code': self.currency_code,
            'warehouse_id': self.warehouse_id,
            'notes': self.notes
        }

