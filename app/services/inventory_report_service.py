"""
Service for inventory reports and analytics.
"""

from typing import Dict, List, Any, Optional
from decimal import Decimal
from datetime import datetime, timedelta
from app import db
from app.models import StockItem, WarehouseStock, Warehouse, StockMovement, StockLot
from sqlalchemy import func, and_


class InventoryReportService:
    """
    Service for inventory reporting and analytics.

    Provides methods for:
    - Stock valuation calculations
    - Inventory turnover analysis
    - Movement history reports
    - Low stock reports
    """

    def get_stock_valuation(
        self, warehouse_id: Optional[int] = None, category: Optional[str] = None, currency_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate total stock valuation.

        Args:
            warehouse_id: Filter by specific warehouse (None for all)
            category: Filter by stock item category (None for all)
            currency_code: Filter by currency (None for all)

        Returns:
            dict with valuation data including:
            - total_value: Total inventory value
            - by_warehouse: Value breakdown by warehouse
            - by_category: Value breakdown by category
            - item_details: Detailed item-level valuation
        """
        # Prefer lot-based valuation when lots exist; fallback to default_cost * WarehouseStock otherwise.
        # Lots unlock devalued returns/waste without creating new stock items.
        lots_exist = False
        try:
            lots_exist = db.session.query(StockLot.id).limit(1).scalar() is not None
        except Exception:
            lots_exist = False

        total_value = Decimal("0")
        by_warehouse = {}
        by_category = {}
        item_details = []

        if lots_exist:
            lot_query = (
                db.session.query(StockLot, StockItem, Warehouse)
                .join(StockItem, StockLot.stock_item_id == StockItem.id)
                .join(Warehouse, StockLot.warehouse_id == Warehouse.id)
                .filter(StockItem.is_active == True, StockItem.is_trackable == True, StockLot.quantity_on_hand > 0)
            )

            if warehouse_id:
                lot_query = lot_query.filter(StockLot.warehouse_id == warehouse_id)
            if category:
                lot_query = lot_query.filter(StockItem.category == category)
            if currency_code:
                lot_query = lot_query.filter(StockItem.currency_code == currency_code)

            results = lot_query.all()

            # Aggregate per item+warehouse to stay compatible with templates.
            agg = {}  # (item_id, warehouse_id) -> dict
            for lot, item, warehouse in results:
                qty = Decimal(str(lot.quantity_on_hand or 0))
                cost = Decimal(str(lot.unit_cost or 0))
                value = qty * cost

                total_value += value

                warehouse_key = f"{warehouse.name} ({warehouse.code})"
                if warehouse_key not in by_warehouse:
                    by_warehouse[warehouse_key] = {
                        "warehouse_id": warehouse.id,
                        "warehouse_name": warehouse.name,
                        "warehouse_code": warehouse.code,
                        "value": Decimal("0"),
                        "currency": item.currency_code,
                    }
                by_warehouse[warehouse_key]["value"] += value

                cat = item.category or "Uncategorized"
                if cat not in by_category:
                    by_category[cat] = {"category": cat, "value": Decimal("0"), "currency": item.currency_code}
                by_category[cat]["value"] += value

                key = (item.id, warehouse.id)
                if key not in agg:
                    agg[key] = {
                        "item": item,
                        "warehouse": warehouse,
                        "total_qty": Decimal("0"),
                        "total_value": Decimal("0"),
                    }
                agg[key]["total_qty"] += qty
                agg[key]["total_value"] += value

            for (item_id_k, warehouse_id_k), row in agg.items():
                item = row["item"]
                warehouse = row["warehouse"]
                qty = row["total_qty"]
                value = row["total_value"]
                avg_cost = (value / qty) if qty > 0 else Decimal("0")
                item_details.append(
                    {
                        "item_id": item.id,
                        "sku": item.sku,
                        "name": item.name,
                        "category": item.category,
                        "warehouse_id": warehouse.id,
                        "warehouse_name": warehouse.name,
                        "quantity": float(qty),
                        "cost": float(avg_cost),
                        "value": float(value),
                        "currency": item.currency_code,
                    }
                )
        else:
            # Base query: join WarehouseStock with StockItem
            query = (
                db.session.query(WarehouseStock, StockItem, Warehouse)
                .join(StockItem, WarehouseStock.stock_item_id == StockItem.id)
                .join(Warehouse, WarehouseStock.warehouse_id == Warehouse.id)
                .filter(
                    StockItem.is_active == True,
                    StockItem.is_trackable == True,
                    WarehouseStock.quantity_on_hand > 0,
                )
            )

            # Apply filters
            if warehouse_id:
                query = query.filter(WarehouseStock.warehouse_id == warehouse_id)
            if category:
                query = query.filter(StockItem.category == category)
            if currency_code:
                query = query.filter(StockItem.currency_code == currency_code)

            results = query.all()

            for stock, item, warehouse in results:
                cost = item.default_cost or Decimal("0")
                quantity = Decimal(str(stock.quantity_on_hand or 0))
                value = cost * quantity

                total_value += value

                warehouse_key = f"{warehouse.name} ({warehouse.code})"
                if warehouse_key not in by_warehouse:
                    by_warehouse[warehouse_key] = {
                        "warehouse_id": warehouse.id,
                        "warehouse_name": warehouse.name,
                        "warehouse_code": warehouse.code,
                        "value": Decimal("0"),
                        "currency": item.currency_code,
                    }
                by_warehouse[warehouse_key]["value"] += value

                cat = item.category or "Uncategorized"
                if cat not in by_category:
                    by_category[cat] = {"category": cat, "value": Decimal("0"), "currency": item.currency_code}
                by_category[cat]["value"] += value

                item_details.append(
                    {
                        "item_id": item.id,
                        "sku": item.sku,
                        "name": item.name,
                        "category": item.category,
                        "warehouse_id": warehouse.id,
                        "warehouse_name": warehouse.name,
                        "quantity": float(quantity),
                        "cost": float(cost),
                        "value": float(value),
                        "currency": item.currency_code,
                    }
                )

        return {
            "total_value": float(total_value),
            "by_warehouse": {k: {**v, "value": float(v["value"])} for k, v in by_warehouse.items()},
            "by_category": {k: {**v, "value": float(v["value"])} for k, v in by_category.items()},
            "item_details": item_details,
            "currency": currency_code or "EUR",
            "warehouse_id": warehouse_id,
            "category": category,
        }

    def get_inventory_turnover(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, item_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Calculate inventory turnover analysis.

        Args:
            start_date: Start of analysis period
            end_date: End of analysis period
            item_id: Specific item to analyze (None for all)

        Returns:
            dict with turnover data
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=365)
        if not end_date:
            end_date = datetime.utcnow()

        # Get movements in the period
        query = StockMovement.query.filter(
            StockMovement.movement_date >= start_date,
            StockMovement.movement_date <= end_date,
            StockMovement.movement_type.in_(["sale", "usage", "consumption"]),
        )

        if item_id:
            query = query.filter(StockMovement.stock_item_id == item_id)

        movements = query.all()

        # Aggregate by item
        item_turnover = {}
        for movement in movements:
            item_id = movement.stock_item_id
            if item_id not in item_turnover:
                item = StockItem.query.get(item_id)
                if not item:
                    continue

                # Get average stock level during period
                avg_stock = self._calculate_average_stock(item_id, start_date, end_date)

                item_turnover[item_id] = {
                    "item_id": item_id,
                    "sku": item.sku,
                    "name": item.name,
                    "quantity_sold": Decimal("0"),
                    "avg_stock": avg_stock,
                    "turnover_rate": Decimal("0"),
                    "days_on_hand": Decimal("0"),
                }

            item_turnover[item_id]["quantity_sold"] += abs(movement.quantity)

        # Calculate turnover rates
        for item_id, data in item_turnover.items():
            if data["avg_stock"] > 0:
                days = (end_date - start_date).days
                data["turnover_rate"] = data["quantity_sold"] / data["avg_stock"] if days > 0 else Decimal("0")
                data["days_on_hand"] = days / data["turnover_rate"] if data["turnover_rate"] > 0 else Decimal("0")
            else:
                data["turnover_rate"] = Decimal("0")
                data["days_on_hand"] = Decimal("0")

            # Convert to float for JSON serialization
            data["quantity_sold"] = float(data["quantity_sold"])
            data["avg_stock"] = float(data["avg_stock"])
            data["turnover_rate"] = float(data["turnover_rate"])
            data["days_on_hand"] = float(data["days_on_hand"])

        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "items": list(item_turnover.values()),
        }

    def _calculate_average_stock(self, item_id: int, start_date: datetime, end_date: datetime) -> Decimal:
        """Calculate average stock level for an item during a period."""
        # Get stock levels at start and end
        start_stock = self._get_stock_at_date(item_id, start_date)
        end_stock = self._get_stock_at_date(item_id, end_date)

        # Simple average (can be enhanced with more data points)
        return (start_stock + end_stock) / 2

    def _get_stock_at_date(self, item_id: int, date: datetime) -> Decimal:
        """Get stock level for an item at a specific date."""
        # Get the most recent movement before or at the date
        movement = (
            StockMovement.query.filter(StockMovement.stock_item_id == item_id, StockMovement.movement_date <= date)
            .order_by(StockMovement.movement_date.desc())
            .first()
        )

        if movement:
            # Get stock after this movement
            # This is simplified - in reality, we'd need to track historical stock levels
            stock = WarehouseStock.query.filter_by(stock_item_id=item_id).first()
            return stock.quantity_on_hand if stock else Decimal("0")

        # No movements, get current stock
        stock = WarehouseStock.query.filter_by(stock_item_id=item_id).first()
        return stock.quantity_on_hand if stock else Decimal("0")

    def get_movement_history(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        item_id: Optional[int] = None,
        warehouse_id: Optional[int] = None,
        movement_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get detailed movement history.

        Returns:
            dict with movement history data
        """
        query = StockMovement.query

        if start_date:
            query = query.filter(StockMovement.movement_date >= start_date)
        if end_date:
            query = query.filter(StockMovement.movement_date <= end_date)
        if item_id:
            query = query.filter(StockMovement.stock_item_id == item_id)
        if warehouse_id:
            query = query.filter(StockMovement.warehouse_id == warehouse_id)
        if movement_type:
            query = query.filter(StockMovement.movement_type == movement_type)

        movements = query.order_by(StockMovement.movement_date.desc()).all()

        return {
            "movements": [
                {
                    "id": m.id,
                    "date": m.movement_date.isoformat() if m.movement_date else None,
                    "item_id": m.stock_item_id,
                    "item_sku": m.stock_item.sku if m.stock_item else None,
                    "item_name": m.stock_item.name if m.stock_item else None,
                    "warehouse_id": m.warehouse_id,
                    "warehouse_name": m.warehouse.name if m.warehouse else None,
                    "quantity": float(m.quantity),
                    "type": m.movement_type,
                    "reference": m.reference,
                    "notes": m.notes,
                }
                for m in movements
            ],
            "total_movements": len(movements),
        }
