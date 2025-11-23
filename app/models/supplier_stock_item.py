"""SupplierStockItem model for many-to-many relationship between suppliers and stock items"""
from datetime import datetime
from decimal import Decimal
from app import db


class SupplierStockItem(db.Model):
    """SupplierStockItem model - links suppliers to stock items with pricing"""
    
    __tablename__ = 'supplier_stock_items'
    
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False, index=True)
    stock_item_id = db.Column(db.Integer, db.ForeignKey('stock_items.id'), nullable=False, index=True)
    
    # Supplier-specific information for this item
    supplier_sku = db.Column(db.String(100), nullable=True)
    supplier_name = db.Column(db.String(200), nullable=True)  # Supplier's name for this product
    unit_cost = db.Column(db.Numeric(10, 2), nullable=True)  # Cost per unit from this supplier
    currency_code = db.Column(db.String(3), nullable=False, default='EUR')
    minimum_order_quantity = db.Column(db.Numeric(10, 2), nullable=True)  # MOQ
    lead_time_days = db.Column(db.Integer, nullable=True)  # Lead time in days
    is_preferred = db.Column(db.Boolean, default=False, nullable=False)  # Preferred supplier for this item
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships (backref defined in Supplier and StockItem models)
    
    # Unique constraint: one supplier-item relationship
    __table_args__ = (
        db.UniqueConstraint('supplier_id', 'stock_item_id', name='uq_supplier_stock_item'),
    )
    
    def __init__(self, supplier_id, stock_item_id, supplier_sku=None, supplier_name=None,
                 unit_cost=None, currency_code='EUR', minimum_order_quantity=None,
                 lead_time_days=None, is_preferred=False, is_active=True, notes=None):
        self.supplier_id = supplier_id
        self.stock_item_id = stock_item_id
        self.supplier_sku = supplier_sku.strip() if supplier_sku else None
        self.supplier_name = supplier_name.strip() if supplier_name else None
        self.unit_cost = Decimal(str(unit_cost)) if unit_cost else None
        self.currency_code = currency_code.upper()
        self.minimum_order_quantity = Decimal(str(minimum_order_quantity)) if minimum_order_quantity else None
        self.lead_time_days = lead_time_days
        self.is_preferred = is_preferred
        self.is_active = is_active
        self.notes = notes.strip() if notes else None
    
    def __repr__(self):
        return f'<SupplierStockItem supplier_id={self.supplier_id} stock_item_id={self.stock_item_id}>'
    
    def to_dict(self):
        """Convert supplier stock item to dictionary"""
        return {
            'id': self.id,
            'supplier_id': self.supplier_id,
            'stock_item_id': self.stock_item_id,
            'supplier_sku': self.supplier_sku,
            'supplier_name': self.supplier_name,
            'unit_cost': float(self.unit_cost) if self.unit_cost else None,
            'currency_code': self.currency_code,
            'minimum_order_quantity': float(self.minimum_order_quantity) if self.minimum_order_quantity else None,
            'lead_time_days': self.lead_time_days,
            'is_preferred': self.is_preferred,
            'is_active': self.is_active,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

