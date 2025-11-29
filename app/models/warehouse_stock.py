"""WarehouseStock model for tracking stock levels per warehouse"""

from datetime import datetime
from decimal import Decimal
from app import db


class WarehouseStock(db.Model):
    """WarehouseStock model - tracks stock levels per warehouse"""

    __tablename__ = "warehouse_stock"

    id = db.Column(db.Integer, primary_key=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False, index=True)
    stock_item_id = db.Column(
        db.Integer, db.ForeignKey("stock_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    quantity_on_hand = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    quantity_reserved = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    location = db.Column(db.String(100), nullable=True)
    last_counted_at = db.Column(db.DateTime, nullable=True)
    last_counted_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    counted_by_user = db.relationship("User", foreign_keys=[last_counted_by])

    # Unique constraint: one stock record per item per warehouse
    __table_args__ = (db.UniqueConstraint("warehouse_id", "stock_item_id", name="uq_warehouse_stock"),)

    def __init__(self, warehouse_id, stock_item_id, quantity_on_hand=0, quantity_reserved=0, location=None):
        self.warehouse_id = warehouse_id
        self.stock_item_id = stock_item_id
        self.quantity_on_hand = Decimal(str(quantity_on_hand))
        self.quantity_reserved = Decimal(str(quantity_reserved))
        self.location = location.strip() if location else None

    def __repr__(self):
        return f"<WarehouseStock {self.warehouse_id}/{self.stock_item_id}: {self.quantity_on_hand}>"

    @property
    def quantity_available(self):
        """Calculate available quantity (on-hand minus reserved)"""
        return self.quantity_on_hand - self.quantity_reserved

    def reserve(self, quantity):
        """Reserve quantity"""
        qty = Decimal(str(quantity))
        available = self.quantity_available
        if qty > available:
            raise ValueError(f"Insufficient stock. Available: {available}, Requested: {qty}")
        self.quantity_reserved += qty
        self.updated_at = datetime.utcnow()

    def release_reservation(self, quantity):
        """Release reserved quantity"""
        qty = Decimal(str(quantity))
        if qty > self.quantity_reserved:
            raise ValueError(f"Cannot release more than reserved. Reserved: {self.quantity_reserved}, Requested: {qty}")
        self.quantity_reserved -= qty
        self.updated_at = datetime.utcnow()

    def adjust_on_hand(self, quantity):
        """Adjust on-hand quantity (positive for additions, negative for removals)"""
        qty = Decimal(str(quantity))
        self.quantity_on_hand += qty
        if self.quantity_on_hand < 0:
            self.quantity_on_hand = Decimal("0")
        self.updated_at = datetime.utcnow()

    def record_count(self, counted_quantity, counted_by=None):
        """Record a physical count"""
        self.quantity_on_hand = Decimal(str(counted_quantity))
        self.last_counted_at = datetime.utcnow()
        if counted_by:
            self.last_counted_by = counted_by
        self.updated_at = datetime.utcnow()

    def to_dict(self):
        """Convert warehouse stock to dictionary"""
        return {
            "id": self.id,
            "warehouse_id": self.warehouse_id,
            "stock_item_id": self.stock_item_id,
            "quantity_on_hand": float(self.quantity_on_hand),
            "quantity_reserved": float(self.quantity_reserved),
            "quantity_available": float(self.quantity_available),
            "location": self.location,
            "last_counted_at": self.last_counted_at.isoformat() if self.last_counted_at else None,
            "last_counted_by": self.last_counted_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
