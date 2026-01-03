"""Stock lot (valuation layer) models for inventory valuation and devaluation.

This project historically valued inventory using StockItem.default_cost.
Stock lots allow per-quantity valuation (e.g. devalued returns) without creating new items.
"""

from datetime import datetime
from decimal import Decimal

from app import db


class StockLot(db.Model):
    """Represents a valuation layer for an item in a specific warehouse."""

    __tablename__ = "stock_lots"

    id = db.Column(db.Integer, primary_key=True)

    stock_item_id = db.Column(db.Integer, db.ForeignKey("stock_items.id"), nullable=False, index=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"), nullable=False, index=True)

    # Classification for reporting/traceability (kept simple on purpose)
    lot_type = db.Column(db.String(20), nullable=False, default="normal", index=True)  # normal, devalued

    unit_cost = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    quantity_on_hand = db.Column(db.Numeric(10, 2), nullable=False, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)

    # Link back to the originating stock movement (if any)
    source_movement_id = db.Column(db.Integer, db.ForeignKey("stock_movements.id"), nullable=True, index=True)

    notes = db.Column(db.Text, nullable=True)

    # Relationships (declared by string name to avoid circular imports)
    created_by_user = db.relationship("User", foreign_keys=[created_by])
    source_movement = db.relationship("StockMovement", foreign_keys=[source_movement_id])
    allocations = db.relationship(
        "StockLotAllocation",
        backref="stock_lot",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.Index("ix_stock_lots_item_wh_cost_type", "stock_item_id", "warehouse_id", "unit_cost", "lot_type"),
    )

    def adjust_on_hand(self, quantity):
        """Adjust on-hand quantity for this lot."""
        qty = Decimal(str(quantity))
        self.quantity_on_hand = Decimal(str(self.quantity_on_hand or 0)) + qty

    def __repr__(self):
        return (
            f"<StockLot item={self.stock_item_id} wh={self.warehouse_id} "
            f"type={self.lot_type} cost={self.unit_cost} qty={self.quantity_on_hand}>"
        )


class StockLotAllocation(db.Model):
    """Links a StockMovement to the StockLots it affected (supports multi-lot FIFO outs)."""

    __tablename__ = "stock_lot_allocations"

    id = db.Column(db.Integer, primary_key=True)

    stock_movement_id = db.Column(db.Integer, db.ForeignKey("stock_movements.id"), nullable=False, index=True)
    stock_lot_id = db.Column(db.Integer, db.ForeignKey("stock_lots.id"), nullable=False, index=True)

    # Signed quantity allocated to/from this lot (matches movement sign)
    quantity = db.Column(db.Numeric(10, 2), nullable=False)

    # Denormalized unit cost for faster reporting / easier auditing
    unit_cost = db.Column(db.Numeric(10, 2), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    movement = db.relationship("StockMovement", foreign_keys=[stock_movement_id], backref="lot_allocations")

    __table_args__ = (
        db.Index("ix_stock_lot_allocations_move_lot", "stock_movement_id", "stock_lot_id"),
    )

    def __repr__(self):
        return f"<StockLotAllocation move={self.stock_movement_id} lot={self.stock_lot_id} qty={self.quantity} cost={self.unit_cost}>"

