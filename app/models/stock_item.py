"""StockItem model for inventory management"""
from datetime import datetime
from decimal import Decimal
from app import db


class StockItem(db.Model):
    """StockItem model - represents a product/item in the inventory catalog"""
    
    __tablename__ = 'stock_items'
    
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(100), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(100), nullable=True, index=True)
    unit = db.Column(db.String(20), nullable=False, default='pcs')
    default_cost = db.Column(db.Numeric(10, 2), nullable=True)
    default_price = db.Column(db.Numeric(10, 2), nullable=True)
    currency_code = db.Column(db.String(3), nullable=False, default='EUR')
    barcode = db.Column(db.String(100), nullable=True, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_trackable = db.Column(db.Boolean, default=True, nullable=False)
    reorder_point = db.Column(db.Numeric(10, 2), nullable=True)
    reorder_quantity = db.Column(db.Numeric(10, 2), nullable=True)
    supplier = db.Column(db.String(200), nullable=True)
    supplier_sku = db.Column(db.String(100), nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Relationships
    warehouse_stock = db.relationship('WarehouseStock', backref='stock_item', lazy='dynamic', cascade='all, delete-orphan')
    stock_movements = db.relationship('StockMovement', backref='stock_item', lazy='dynamic')
    reservations = db.relationship('StockReservation', backref='stock_item', lazy='dynamic')
    supplier_items = db.relationship('SupplierStockItem', backref='stock_item', lazy='dynamic', cascade='all, delete-orphan')
    
    def __init__(self, sku, name, created_by, description=None, category=None, unit='pcs',
                 default_cost=None, default_price=None, currency_code='EUR', barcode=None,
                 is_active=True, is_trackable=True, reorder_point=None, reorder_quantity=None,
                 supplier=None, supplier_sku=None, image_url=None, notes=None):
        self.sku = sku.strip().upper()
        self.name = name.strip()
        self.created_by = created_by
        self.description = description.strip() if description else None
        self.category = category.strip() if category else None
        self.unit = unit.strip() if unit else 'pcs'
        self.default_cost = Decimal(str(default_cost)) if default_cost else None
        self.default_price = Decimal(str(default_price)) if default_price else None
        self.currency_code = currency_code.upper()
        self.barcode = barcode.strip() if barcode else None
        self.is_active = is_active
        self.is_trackable = is_trackable
        self.reorder_point = Decimal(str(reorder_point)) if reorder_point else None
        self.reorder_quantity = Decimal(str(reorder_quantity)) if reorder_quantity else None
        self.supplier = supplier.strip() if supplier else None
        self.supplier_sku = supplier_sku.strip() if supplier_sku else None
        self.image_url = image_url.strip() if image_url else None
        self.notes = notes.strip() if notes else None
    
    def __repr__(self):
        return f'<StockItem {self.sku} ({self.name})>'
    
    @property
    def total_quantity_on_hand(self):
        """Calculate total quantity across all warehouses"""
        if not self.is_trackable:
            return None
        from .warehouse_stock import WarehouseStock
        total = db.session.query(db.func.sum(WarehouseStock.quantity_on_hand)).filter_by(
            stock_item_id=self.id
        ).scalar()
        return Decimal(str(total)) if total else Decimal('0')
    
    @property
    def total_quantity_reserved(self):
        """Calculate total reserved quantity across all warehouses"""
        if not self.is_trackable:
            return None
        from .warehouse_stock import WarehouseStock
        total = db.session.query(db.func.sum(WarehouseStock.quantity_reserved)).filter_by(
            stock_item_id=self.id
        ).scalar()
        return Decimal(str(total)) if total else Decimal('0')
    
    @property
    def total_quantity_available(self):
        """Calculate total available quantity (on-hand minus reserved)"""
        if not self.is_trackable:
            return None
        on_hand = self.total_quantity_on_hand or Decimal('0')
        reserved = self.total_quantity_reserved or Decimal('0')
        return on_hand - reserved
    
    @property
    def is_low_stock(self):
        """Check if any warehouse is below reorder point"""
        if not self.is_trackable or not self.reorder_point:
            return False
        from .warehouse_stock import WarehouseStock
        low_stock = WarehouseStock.query.filter(
            WarehouseStock.stock_item_id == self.id,
            WarehouseStock.quantity_on_hand < self.reorder_point
        ).first()
        return low_stock is not None
    
    def get_stock_level(self, warehouse_id):
        """Get stock level for a specific warehouse"""
        if not self.is_trackable:
            return None
        from .warehouse_stock import WarehouseStock
        stock = WarehouseStock.query.filter_by(
            stock_item_id=self.id,
            warehouse_id=warehouse_id
        ).first()
        return stock.quantity_on_hand if stock else Decimal('0')
    
    def get_available_quantity(self, warehouse_id):
        """Get available quantity for a specific warehouse"""
        if not self.is_trackable:
            return None
        from .warehouse_stock import WarehouseStock
        stock = WarehouseStock.query.filter_by(
            stock_item_id=self.id,
            warehouse_id=warehouse_id
        ).first()
        if not stock:
            return Decimal('0')
        return stock.quantity_on_hand - stock.quantity_reserved
    
    def to_dict(self):
        """Convert stock item to dictionary"""
        return {
            'id': self.id,
            'sku': self.sku,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'unit': self.unit,
            'default_cost': float(self.default_cost) if self.default_cost else None,
            'default_price': float(self.default_price) if self.default_price else None,
            'currency_code': self.currency_code,
            'barcode': self.barcode,
            'is_active': self.is_active,
            'is_trackable': self.is_trackable,
            'reorder_point': float(self.reorder_point) if self.reorder_point else None,
            'reorder_quantity': float(self.reorder_quantity) if self.reorder_quantity else None,
            'supplier': self.supplier,
            'supplier_sku': self.supplier_sku,
            'image_url': self.image_url,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'total_quantity_on_hand': float(self.total_quantity_on_hand) if self.total_quantity_on_hand else None,
            'total_quantity_reserved': float(self.total_quantity_reserved) if self.total_quantity_reserved else None,
            'total_quantity_available': float(self.total_quantity_available) if self.total_quantity_available else None,
            'is_low_stock': self.is_low_stock
        }

