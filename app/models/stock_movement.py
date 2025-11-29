"""StockMovement model for tracking inventory movements"""

from datetime import datetime
from decimal import Decimal
from app import db


class StockMovement(db.Model):
    """StockMovement model - tracks all inventory movements"""

    __tablename__ = "stock_movements"

    id = db.Column(db.Integer, primary_key=True)
    movement_type = db.Column(
        db.String(20), nullable=False, index=True
    )  # 'adjustment', 'transfer', 'sale', 'purchase', 'return', 'waste'
    stock_item_id = db.Column(db.Integer, db.ForeignKey("stock_items.id"), nullable=False, index=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"), nullable=False, index=True)
    quantity = db.Column(db.Numeric(10, 2), nullable=False)  # Positive for additions, negative for removals
    reference_type = db.Column(
        db.String(50), nullable=True, index=True
    )  # 'invoice', 'quote', 'project', 'manual', 'purchase_order'
    reference_id = db.Column(db.Integer, nullable=True, index=True)
    unit_cost = db.Column(db.Numeric(10, 2), nullable=True)
    reason = db.Column(db.String(500), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    moved_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    moved_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    moved_by_user = db.relationship("User", foreign_keys=[moved_by])

    # Composite index for reference lookups
    __table_args__ = (
        db.Index("ix_stock_movements_reference", "reference_type", "reference_id"),
        db.Index("ix_stock_movements_item_date", "stock_item_id", "moved_at"),
    )

    def __init__(
        self,
        movement_type,
        stock_item_id,
        warehouse_id,
        quantity,
        moved_by,
        reference_type=None,
        reference_id=None,
        unit_cost=None,
        reason=None,
        notes=None,
    ):
        self.movement_type = movement_type
        self.stock_item_id = stock_item_id
        self.warehouse_id = warehouse_id
        self.quantity = Decimal(str(quantity))
        self.moved_by = moved_by
        self.reference_type = reference_type
        self.reference_id = reference_id
        self.unit_cost = Decimal(str(unit_cost)) if unit_cost else None
        self.reason = reason.strip() if reason else None
        self.notes = notes.strip() if notes else None

    def __repr__(self):
        return f"<StockMovement {self.movement_type} {self.quantity} of {self.stock_item_id} at {self.warehouse_id}>"

    def to_dict(self):
        """Convert stock movement to dictionary"""
        return {
            "id": self.id,
            "movement_type": self.movement_type,
            "stock_item_id": self.stock_item_id,
            "warehouse_id": self.warehouse_id,
            "quantity": float(self.quantity),
            "reference_type": self.reference_type,
            "reference_id": self.reference_id,
            "unit_cost": float(self.unit_cost) if self.unit_cost else None,
            "reason": self.reason,
            "notes": self.notes,
            "moved_by": self.moved_by,
            "moved_at": self.moved_at.isoformat() if self.moved_at else None,
        }

    @classmethod
    def record_movement(
        cls,
        movement_type,
        stock_item_id,
        warehouse_id,
        quantity,
        moved_by,
        reference_type=None,
        reference_id=None,
        unit_cost=None,
        reason=None,
        notes=None,
        update_stock=True,
    ):
        """
        Record a stock movement and optionally update warehouse stock levels

        Returns:
            tuple: (StockMovement instance, updated WarehouseStock instance or None)
        """
        from .warehouse_stock import WarehouseStock

        movement = cls(
            movement_type=movement_type,
            stock_item_id=stock_item_id,
            warehouse_id=warehouse_id,
            quantity=quantity,
            moved_by=moved_by,
            reference_type=reference_type,
            reference_id=reference_id,
            unit_cost=unit_cost,
            reason=reason,
            notes=notes,
        )

        db.session.add(movement)

        updated_stock = None
        if update_stock:
            # Get or create warehouse stock record
            stock = WarehouseStock.query.filter_by(warehouse_id=warehouse_id, stock_item_id=stock_item_id).first()

            if not stock:
                stock = WarehouseStock(warehouse_id=warehouse_id, stock_item_id=stock_item_id, quantity_on_hand=0)
                db.session.add(stock)

            # Update stock level
            stock.adjust_on_hand(quantity)
            updated_stock = stock

        return movement, updated_stock
