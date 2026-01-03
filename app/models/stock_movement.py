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
    )  # 'adjustment', 'transfer', 'sale', 'rent', 'purchase', 'return', 'waste'
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
        lot_type=None,
        consume_from_lot_id=None,
        update_lots=True,
    ):
        """
        Record a stock movement and optionally update warehouse stock levels

        Returns:
            tuple: (StockMovement instance, updated WarehouseStock instance or None)
        """
        from .warehouse_stock import WarehouseStock
        from .stock_item import StockItem
        from .stock_lot import StockLot, StockLotAllocation

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
        db.session.flush()  # ensure movement.id is available for lot allocations

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

        # --- Lot/valuation layer tracking (best-effort, backward compatible) ---
        if update_lots:
            try:
                item = StockItem.query.get(stock_item_id)
                if item and item.is_trackable:
                    cls._apply_lot_changes(
                        movement=movement,
                        item=item,
                        updated_stock=updated_stock,
                        unit_cost=unit_cost,
                        lot_type=lot_type,
                        consume_from_lot_id=consume_from_lot_id,
                    )
            except Exception:
                # Do not break core stock tracking if lot tracking fails;
                # keep lots as an enhancement layer.
                pass

        return movement, updated_stock

    @classmethod
    def _ensure_legacy_lot(cls, item, warehouse_id, moved_by, updated_stock=None):
        """If there are no lots but there is stock, seed a legacy lot."""
        from .stock_lot import StockLot

        existing = StockLot.query.filter_by(stock_item_id=item.id, warehouse_id=warehouse_id).first()
        if existing:
            return

        qty_on_hand = None
        if updated_stock is not None:
            qty_on_hand = Decimal(str(updated_stock.quantity_on_hand or 0))

        if qty_on_hand is None or qty_on_hand <= 0:
            return

        legacy_cost = item.default_cost or Decimal("0")
        legacy = StockLot(
            stock_item_id=item.id,
            warehouse_id=warehouse_id,
            lot_type="normal",
            unit_cost=legacy_cost,
            quantity_on_hand=qty_on_hand,
            created_by=moved_by,
            notes="Legacy lot created automatically to support FIFO/valuation layers.",
        )
        db.session.add(legacy)

    @classmethod
    def _apply_lot_changes(cls, movement, item, updated_stock=None, unit_cost=None, lot_type=None, consume_from_lot_id=None):
        """
        Apply the movement to StockLots and create StockLotAllocations.

        - Positive quantities create a new lot (preserves FIFO granularity).
        - Negative quantities consume FIFO lots (oldest first), optionally preferring a specific lot.
        - Inbound transfers replicate cost layers from the paired outbound transfer when possible.
        """
        from .stock_lot import StockLot, StockLotAllocation

        qty = Decimal(str(movement.quantity or 0))
        if qty == 0:
            return

        # Seed a legacy lot if needed so outflows can be allocated even for pre-lot stock.
        cls._ensure_legacy_lot(item=item, warehouse_id=movement.warehouse_id, moved_by=movement.moved_by, updated_stock=updated_stock)

        # Handle inbound transfer: replicate allocations from the outbound paired movement if available.
        if qty > 0 and movement.movement_type == "transfer" and movement.reference_type == "transfer" and movement.reference_id:
            out_move = (
                cls.query.filter(
                    cls.movement_type == "transfer",
                    cls.reference_type == "transfer",
                    cls.reference_id == movement.reference_id,
                    cls.stock_item_id == movement.stock_item_id,
                    cls.warehouse_id != movement.warehouse_id,
                    cls.quantity < 0,
                )
                .order_by(cls.id.asc())
                .first()
            )

            if out_move and getattr(out_move, "lot_allocations", None):
                remaining = qty
                # Preserve original lot created_at ordering by using the source lot's created_at when creating dest lots.
                for alloc in out_move.lot_allocations:
                    if remaining <= 0:
                        break
                    alloc_qty = Decimal(str(abs(alloc.quantity)))
                    if alloc_qty <= 0:
                        continue
                    take = min(remaining, alloc_qty)
                    remaining -= take

                    src_lot = StockLot.query.get(alloc.stock_lot_id)
                    src_created_at = src_lot.created_at if src_lot else movement.moved_at
                    src_type = src_lot.lot_type if src_lot else "normal"

                    dest_lot = StockLot(
                        stock_item_id=movement.stock_item_id,
                        warehouse_id=movement.warehouse_id,
                        lot_type=src_type,
                        unit_cost=Decimal(str(alloc.unit_cost)),
                        quantity_on_hand=take,
                        created_by=movement.moved_by,
                        created_at=src_created_at,
                        source_movement_id=movement.id,
                        notes=f"Transferred in from movement {out_move.id}",
                    )
                    db.session.add(dest_lot)
                    db.session.flush()

                    db.session.add(
                        StockLotAllocation(
                            stock_movement_id=movement.id,
                            stock_lot_id=dest_lot.id,
                            quantity=take,
                            unit_cost=Decimal(str(alloc.unit_cost)),
                        )
                    )

                # If allocations didn't cover full qty (older data), fall back to a normal inbound lot.
                if remaining > 0:
                    inbound_cost = Decimal(str(unit_cost)) if unit_cost is not None else (item.default_cost or Decimal("0"))
                    inbound_type = lot_type or "normal"
                    lot = StockLot(
                        stock_item_id=movement.stock_item_id,
                        warehouse_id=movement.warehouse_id,
                        lot_type=inbound_type,
                        unit_cost=inbound_cost,
                        quantity_on_hand=remaining,
                        created_by=movement.moved_by,
                        source_movement_id=movement.id,
                    )
                    db.session.add(lot)
                    db.session.flush()
                    db.session.add(
                        StockLotAllocation(
                            stock_movement_id=movement.id,
                            stock_lot_id=lot.id,
                            quantity=remaining,
                            unit_cost=inbound_cost,
                        )
                    )
                return

        if qty > 0:
            inbound_cost = Decimal(str(unit_cost)) if unit_cost is not None else (item.default_cost or Decimal("0"))
            inbound_type = lot_type or "normal"
            lot = StockLot(
                stock_item_id=movement.stock_item_id,
                warehouse_id=movement.warehouse_id,
                lot_type=inbound_type,
                unit_cost=inbound_cost,
                quantity_on_hand=qty,
                created_by=movement.moved_by,
                source_movement_id=movement.id,
            )
            db.session.add(lot)
            db.session.flush()
            db.session.add(
                StockLotAllocation(
                    stock_movement_id=movement.id,
                    stock_lot_id=lot.id,
                    quantity=qty,
                    unit_cost=inbound_cost,
                )
            )
            return

        # Outbound: consume FIFO (oldest first). Prefer a specific lot if provided (used after devaluation).
        # Special case: "rent" movements keep value in stock (don't consume from lots) for accounting purposes
        if qty < 0 and movement.movement_type == "rent":
            # For rent, we don't consume from lots - this keeps the value in inventory
            # while removing physical quantity from warehouse
            return
        
        qty_to_consume = abs(qty)
        allow_negative = movement.movement_type == "adjustment"

        lots_q = StockLot.query.filter(
            StockLot.stock_item_id == movement.stock_item_id,
            StockLot.warehouse_id == movement.warehouse_id,
        )

        preferred_lot = None
        if consume_from_lot_id:
            preferred_lot = StockLot.query.get(int(consume_from_lot_id))

        lots = (
            lots_q.filter(StockLot.quantity_on_hand != 0)
            .order_by(StockLot.created_at.asc(), StockLot.id.asc())
            .all()
        )

        if preferred_lot:
            # Put preferred lot first if it matches scope and has non-zero quantity.
            lots = [l for l in lots if l.id != preferred_lot.id]
            if preferred_lot.stock_item_id == movement.stock_item_id and preferred_lot.warehouse_id == movement.warehouse_id:
                if Decimal(str(preferred_lot.quantity_on_hand or 0)) != 0:
                    lots = [preferred_lot] + lots

        remaining = qty_to_consume
        for lot in lots:
            if remaining <= 0:
                break
            lot_qty = Decimal(str(lot.quantity_on_hand or 0))
            if lot_qty == 0:
                continue

            # For normal FIFO, only consume positive on-hand lots. For adjustments, allow driving lots negative.
            available = lot_qty if lot_qty > 0 else Decimal("0")
            if available <= 0 and not allow_negative:
                continue

            take = remaining if allow_negative else min(remaining, available)
            remaining -= take if not allow_negative else Decimal("0")  # adjustments can drain a single lot

            lot.adjust_on_hand(-take)
            db.session.add(
                StockLotAllocation(
                    stock_movement_id=movement.id,
                    stock_lot_id=lot.id,
                    quantity=-take,
                    unit_cost=Decimal(str(lot.unit_cost)),
                )
            )

            if allow_negative:
                # If adjustment exceeds available, push lot negative and finish.
                remaining = Decimal("0")

        if remaining > 0:
            # If we're here, we couldn't allocate enough from existing lots.
            if allow_negative:
                # Create a new lot and drive it negative.
                fallback_cost = item.default_cost or Decimal("0")
                new_lot = StockLot(
                    stock_item_id=movement.stock_item_id,
                    warehouse_id=movement.warehouse_id,
                    lot_type="normal",
                    unit_cost=fallback_cost,
                    quantity_on_hand=Decimal("0"),
                    created_by=movement.moved_by,
                    notes="Auto-created lot to support negative adjustment.",
                )
                db.session.add(new_lot)
                db.session.flush()
                new_lot.adjust_on_hand(-remaining)
                db.session.add(
                    StockLotAllocation(
                        stock_movement_id=movement.id,
                        stock_lot_id=new_lot.id,
                        quantity=-remaining,
                        unit_cost=fallback_cost,
                    )
                )
                return

            raise ValueError("Insufficient stock lots to cover this movement (lots/FIFO)")

    @classmethod
    def record_devaluation(
        cls,
        stock_item_id,
        warehouse_id,
        quantity,
        moved_by,
        new_unit_cost,
        reason=None,
        notes=None,
    ):
        """
        Revalue (devalue) a quantity in-place by moving it into a devalued lot.

        Creates a StockMovement with quantity 0 (no physical stock change) and updates StockLots:
        FIFO consume from existing lots -> add same qty to a new 'devalued' lot at new_unit_cost.

        Returns:
            tuple: (StockMovement instance, StockLot instance)
        """
        from .stock_item import StockItem
        from .warehouse_stock import WarehouseStock
        from .stock_lot import StockLot, StockLotAllocation

        qty = Decimal(str(quantity))
        if qty <= 0:
            raise ValueError("Devaluation quantity must be positive")

        item = StockItem.query.get(stock_item_id)
        if not item or not item.is_trackable:
            raise ValueError("Item not found or not trackable")

        movement = cls(
            movement_type="devaluation",
            stock_item_id=stock_item_id,
            warehouse_id=warehouse_id,
            quantity=Decimal("0"),
            moved_by=moved_by,
            unit_cost=Decimal(str(new_unit_cost)),
            reason=reason,
            notes=notes,
        )
        db.session.add(movement)
        db.session.flush()

        # Ensure legacy lot exists if needed (based on current WarehouseStock)
        ws = WarehouseStock.query.filter_by(warehouse_id=warehouse_id, stock_item_id=stock_item_id).first()
        cls._ensure_legacy_lot(item=item, warehouse_id=warehouse_id, moved_by=moved_by, updated_stock=ws)

        # Consume FIFO from existing lots
        remaining = qty
        lots = (
            StockLot.query.filter(
                StockLot.stock_item_id == stock_item_id,
                StockLot.warehouse_id == warehouse_id,
                StockLot.quantity_on_hand > 0,
            )
            .order_by(StockLot.created_at.asc(), StockLot.id.asc())
            .all()
        )

        for lot in lots:
            if remaining <= 0:
                break
            lot_qty = Decimal(str(lot.quantity_on_hand or 0))
            if lot_qty <= 0:
                continue
            take = min(remaining, lot_qty)
            remaining -= take
            lot.adjust_on_hand(-take)
            db.session.add(
                StockLotAllocation(
                    stock_movement_id=movement.id,
                    stock_lot_id=lot.id,
                    quantity=-take,
                    unit_cost=Decimal(str(lot.unit_cost)),
                )
            )

        if remaining > 0:
            raise ValueError("Insufficient stock to devalue (lots/FIFO)")

        # Create the devalued lot receiving the quantity
        devalued_cost = Decimal(str(new_unit_cost))
        dest_lot = StockLot(
            stock_item_id=stock_item_id,
            warehouse_id=warehouse_id,
            lot_type="devalued",
            unit_cost=devalued_cost,
            quantity_on_hand=qty,
            created_by=moved_by,
            source_movement_id=movement.id,
            notes="Created by devaluation movement.",
        )
        db.session.add(dest_lot)
        db.session.flush()
        db.session.add(
            StockLotAllocation(
                stock_movement_id=movement.id,
                stock_lot_id=dest_lot.id,
                quantity=qty,
                unit_cost=devalued_cost,
            )
        )

        return movement, dest_lot
