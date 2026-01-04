"""Inventory Management Routes"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db, log_event
from app.models import (
    Warehouse,
    StockItem,
    WarehouseStock,
    StockMovement,
    StockReservation,
    ProjectStockAllocation,
    Project,
    Supplier,
    SupplierStockItem,
    PurchaseOrder,
    PurchaseOrderItem,
    StockLot,
)
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from app.utils.db import safe_commit
from app.utils.permissions import admin_or_permission_required
from sqlalchemy import func, or_

inventory_bp = Blueprint("inventory", __name__)


# ==================== Stock Items API (for selection in forms) ====================


@inventory_bp.route("/api/inventory/stock-items/search")
@login_required
@admin_or_permission_required("view_inventory")
def search_stock_items():
    """Search stock items for dropdown/autocomplete (returns JSON)"""
    search = request.args.get("search", "").strip()
    active_only = request.args.get("active_only", "true").lower() == "true"

    query = StockItem.query.filter_by(is_active=True) if active_only else StockItem.query

    if search:
        like = f"%{search}%"
        query = query.filter(or_(StockItem.sku.ilike(like), StockItem.name.ilike(like), StockItem.barcode.ilike(like)))

    items = query.order_by(StockItem.name).limit(50).all()

    return jsonify(
        {
            "items": [
                {
                    "id": item.id,
                    "sku": item.sku,
                    "name": item.name,
                    "default_price": float(item.default_price) if item.default_price else None,
                    "default_cost": float(item.default_cost) if item.default_cost else None,
                    "unit": item.unit,
                    "description": item.description,
                    "is_trackable": item.is_trackable,
                    "currency_code": item.currency_code,
                }
                for item in items
            ]
        }
    )


@inventory_bp.route("/api/inventory/stock-items/<int:item_id>/availability")
@login_required
@admin_or_permission_required("view_inventory")
def get_item_availability(item_id):
    """Get stock availability for a specific item across warehouses"""
    item = StockItem.query.get_or_404(item_id)
    warehouse_id = request.args.get("warehouse_id", type=int)

    query = WarehouseStock.query.filter_by(stock_item_id=item_id)
    if warehouse_id:
        query = query.filter_by(warehouse_id=warehouse_id)

    stock_levels = query.all()

    availability = []
    for stock in stock_levels:
        availability.append(
            {
                "warehouse_id": stock.warehouse_id,
                "warehouse_code": stock.warehouse.code,
                "warehouse_name": stock.warehouse.name,
                "quantity_available": float(stock.quantity_available),
            }
        )

    return jsonify({"item_id": item_id, "item_sku": item.sku, "item_name": item.name, "availability": availability})


# ==================== Stock Items ====================


@inventory_bp.route("/inventory/items")
@login_required
@admin_or_permission_required("view_inventory")
def list_stock_items():
    """List all stock items"""
    search = request.args.get("search", "").strip()
    category = request.args.get("category", "")
    active_only = request.args.get("active", "true").lower() == "true"
    low_stock_only = request.args.get("low_stock", "false").lower() == "true"

    query = StockItem.query

    if active_only:
        query = query.filter_by(is_active=True)

    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                StockItem.sku.ilike(like),
                StockItem.name.ilike(like),
                StockItem.barcode.ilike(like),
                StockItem.description.ilike(like),
            )
        )

    if category:
        query = query.filter_by(category=category)

    items = query.order_by(StockItem.name).all()

    # Filter low stock items if requested
    if low_stock_only:
        items = [item for item in items if item.is_low_stock]

    # Get categories for filter dropdown
    categories = (
        db.session.query(StockItem.category)
        .distinct()
        .filter(StockItem.category.isnot(None))
        .order_by(StockItem.category)
        .all()
    )
    categories = [cat[0] for cat in categories]

    return render_template(
        "inventory/stock_items/list.html",
        items=items,
        search=search,
        category=category,
        active_only=active_only,
        low_stock_only=low_stock_only,
        categories=categories,
    )


@inventory_bp.route("/inventory/items/new", methods=["GET", "POST"])
@login_required
@admin_or_permission_required("manage_stock_items")
def new_stock_item():
    """Create a new stock item"""
    if request.method == "POST":
        try:
            sku = request.form.get("sku", "").strip().upper()
            name = request.form.get("name", "").strip()

            # Check if SKU already exists
            existing = StockItem.query.filter_by(sku=sku).first()
            if existing:
                flash(_("SKU already exists. Please use a different SKU."), "error")
                return render_template("inventory/stock_items/form.html", item=None, error="sku_exists")

            item = StockItem(
                sku=sku,
                name=name,
                created_by=current_user.id,
                description=request.form.get("description", "").strip() or None,
                category=request.form.get("category", "").strip() or None,
                unit=request.form.get("unit", "pcs").strip(),
                default_cost=request.form.get("default_cost") or None,
                default_price=request.form.get("default_price") or None,
                currency_code=request.form.get("currency_code", "EUR").upper(),
                barcode=request.form.get("barcode", "").strip() or None,
                is_active=request.form.get("is_active") == "on",
                is_trackable=request.form.get("is_trackable") != "off",
                reorder_point=request.form.get("reorder_point") or None,
                reorder_quantity=request.form.get("reorder_quantity") or None,
                supplier=request.form.get("supplier", "").strip() or None,
                supplier_sku=request.form.get("supplier_sku", "").strip() or None,
                image_url=request.form.get("image_url", "").strip() or None,
                notes=request.form.get("notes", "").strip() or None,
            )

            db.session.add(item)
            safe_commit()

            # Handle suppliers
            supplier_ids = request.form.getlist("supplier_id[]")
            supplier_skus = request.form.getlist("supplier_sku[]")
            supplier_unit_costs = request.form.getlist("supplier_unit_cost[]")
            supplier_moqs = request.form.getlist("supplier_moq[]")
            supplier_lead_times = request.form.getlist("supplier_lead_time[]")
            supplier_preferred = request.form.getlist("supplier_preferred[]")

            for i, supplier_id in enumerate(supplier_ids):
                if supplier_id and supplier_id.strip():
                    try:
                        supplier_stock_item = SupplierStockItem(
                            supplier_id=int(supplier_id),
                            stock_item_id=item.id,
                            supplier_sku=(
                                supplier_skus[i].strip() if i < len(supplier_skus) and supplier_skus[i] else None
                            ),
                            unit_cost=(
                                Decimal(supplier_unit_costs[i])
                                if i < len(supplier_unit_costs) and supplier_unit_costs[i]
                                else None
                            ),
                            minimum_order_quantity=(
                                Decimal(supplier_moqs[i]) if i < len(supplier_moqs) and supplier_moqs[i] else None
                            ),
                            lead_time_days=(
                                int(supplier_lead_times[i])
                                if i < len(supplier_lead_times) and supplier_lead_times[i]
                                else None
                            ),
                            is_preferred=str(item.id) in supplier_preferred if supplier_preferred else False,
                            currency_code=item.currency_code,
                        )
                        db.session.add(supplier_stock_item)
                    except (ValueError, InvalidOperation):
                        pass  # Skip invalid entries

            safe_commit()

            log_event("stock_item_created", stock_item_id=item.id, sku=item.sku)
            flash(_("Stock item created successfully."), "success")
            return redirect(url_for("inventory.view_stock_item", item_id=item.id))

        except Exception as e:
            db.session.rollback()
            flash(_("Error creating stock item: %(error)s", error=str(e)), "error")
            suppliers = Supplier.query.filter_by(is_active=True).order_by(Supplier.name).all()
            suppliers_dict = [supplier.to_dict() for supplier in suppliers]
            return render_template("inventory/stock_items/form.html", item=None, suppliers=suppliers_dict)

    suppliers = Supplier.query.filter_by(is_active=True).order_by(Supplier.name).all()
    suppliers_dict = [supplier.to_dict() for supplier in suppliers]
    return render_template("inventory/stock_items/form.html", item=None, suppliers=suppliers_dict)


@inventory_bp.route("/inventory/items/<int:item_id>")
@login_required
@admin_or_permission_required("view_inventory")
def view_stock_item(item_id):
    """View stock item details"""
    item = StockItem.query.get_or_404(item_id)

    # Get stock levels across all warehouses
    stock_levels = WarehouseStock.query.filter_by(stock_item_id=item_id).all()

    # Get stock lots grouped by warehouse (for devaluation breakdown)
    stock_lots_by_warehouse = {}
    if item.is_trackable:
        # Join with Warehouse to get warehouse information
        lots_query = (
            db.session.query(StockLot, Warehouse)
            .join(Warehouse, StockLot.warehouse_id == Warehouse.id)
            .filter(StockLot.stock_item_id == item_id)
            .filter(StockLot.quantity_on_hand > 0)
            .order_by(StockLot.warehouse_id, StockLot.created_at)
            .all()
        )
        
        default_cost = Decimal(str(item.default_cost)) if item.default_cost else Decimal("0")
        
        for lot, warehouse in lots_query:
            warehouse_id = lot.warehouse_id
            if warehouse_id not in stock_lots_by_warehouse:
                stock_lots_by_warehouse[warehouse_id] = {
                    "warehouse": warehouse,
                    "lots": [],
                    "total_quantity": float(0)
                }
            
            # Calculate devaluation percentage
            lot_cost = Decimal(str(lot.unit_cost or 0))
            devaluation_percentage = None
            if default_cost > 0:
                # Calculate percentage: (1 - (lot_cost / default_cost)) * 100
                # Positive means devaluation, negative means appreciation
                devaluation_percentage = float((Decimal("1") - (lot_cost / default_cost)) * Decimal("100"))
                # Round to 2 decimal places
                devaluation_percentage = round(devaluation_percentage, 2)
            
            # Determine if lot is devalued (either marked as devalued or has positive devaluation %)
            is_devalued = lot.lot_type == "devalued" or (devaluation_percentage is not None and devaluation_percentage > 0)
            
            quantity = Decimal(str(lot.quantity_on_hand or 0))
            stock_lots_by_warehouse[warehouse_id]["total_quantity"] += float(quantity)
            
            stock_lots_by_warehouse[warehouse_id]["lots"].append({
                "lot": lot,
                "quantity": float(quantity),
                "unit_cost": float(lot_cost),
                "lot_type": lot.lot_type,
                "devaluation_percentage": devaluation_percentage,
                "is_devalued": is_devalued,
            })

    # Get recent movements (last 20)
    recent_movements = (
        StockMovement.query.filter_by(stock_item_id=item_id).order_by(StockMovement.moved_at.desc()).limit(20).all()
    )

    # Get active reservations
    active_reservations = StockReservation.query.filter(
        StockReservation.stock_item_id == item_id, StockReservation.status == "reserved"
    ).all()

    return render_template(
        "inventory/stock_items/view.html",
        item=item,
        stock_levels=stock_levels,
        stock_lots_by_warehouse=stock_lots_by_warehouse,
        recent_movements=recent_movements,
        active_reservations=active_reservations,
    )


@inventory_bp.route("/inventory/items/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
@admin_or_permission_required("manage_stock_items")
def edit_stock_item(item_id):
    """Edit stock item"""
    item = StockItem.query.get_or_404(item_id)

    if request.method == "POST":
        try:
            # Check if SKU is being changed and if new SKU exists
            new_sku = request.form.get("sku", "").strip().upper()
            if new_sku != item.sku:
                existing = StockItem.query.filter_by(sku=new_sku).first()
                if existing:
                    flash(_("SKU already exists. Please use a different SKU."), "error")
                    suppliers = Supplier.query.filter_by(is_active=True).order_by(Supplier.name).all()
                    suppliers_dict = [supplier.to_dict() for supplier in suppliers]
                    return render_template("inventory/stock_items/form.html", item=item, suppliers=suppliers_dict)

            item.sku = new_sku
            item.name = request.form.get("name", "").strip()
            item.description = request.form.get("description", "").strip() or None
            item.category = request.form.get("category", "").strip() or None
            item.unit = request.form.get("unit", "pcs").strip()
            item.default_cost = Decimal(request.form.get("default_cost")) if request.form.get("default_cost") else None
            item.default_price = (
                Decimal(request.form.get("default_price")) if request.form.get("default_price") else None
            )
            item.currency_code = request.form.get("currency_code", "EUR").upper()
            item.barcode = request.form.get("barcode", "").strip() or None
            item.is_active = request.form.get("is_active") == "on"
            item.is_trackable = request.form.get("is_trackable") != "off"
            item.reorder_point = (
                Decimal(request.form.get("reorder_point")) if request.form.get("reorder_point") else None
            )
            item.reorder_quantity = (
                Decimal(request.form.get("reorder_quantity")) if request.form.get("reorder_quantity") else None
            )
            item.supplier = request.form.get("supplier", "").strip() or None
            item.supplier_sku = request.form.get("supplier_sku", "").strip() or None
            item.image_url = request.form.get("image_url", "").strip() or None
            item.notes = request.form.get("notes", "").strip() or None
            item.updated_at = datetime.utcnow()

            # Handle suppliers - update existing or create new
            # First, get all existing supplier items for this stock item
            supplier_item_ids = request.form.getlist("supplier_item_id[]")
            supplier_ids = request.form.getlist("supplier_id[]")
            supplier_skus = request.form.getlist("supplier_sku[]")
            supplier_unit_costs = request.form.getlist("supplier_unit_cost[]")
            supplier_moqs = request.form.getlist("supplier_moq[]")
            supplier_lead_times = request.form.getlist("supplier_lead_time[]")
            supplier_preferred = request.form.getlist("supplier_preferred[]")

            # Get existing supplier items
            existing_supplier_items = {
                si.id: si for si in SupplierStockItem.query.filter_by(stock_item_id=item.id).all()
            }
            processed_ids = set()

            for i, supplier_id in enumerate(supplier_ids):
                if supplier_id and supplier_id.strip():
                    try:
                        supplier_item_id = (
                            supplier_item_ids[i] if i < len(supplier_item_ids) and supplier_item_ids[i] else None
                        )

                        if supplier_item_id and supplier_item_id.strip():
                            # Update existing
                            supplier_item_id_int = int(supplier_item_id)
                            if supplier_item_id_int in existing_supplier_items:
                                supplier_item = existing_supplier_items[supplier_item_id_int]
                                supplier_item.supplier_id = int(supplier_id)
                                supplier_item.supplier_sku = (
                                    supplier_skus[i].strip() if i < len(supplier_skus) and supplier_skus[i] else None
                                )
                                supplier_item.unit_cost = (
                                    Decimal(supplier_unit_costs[i])
                                    if i < len(supplier_unit_costs) and supplier_unit_costs[i]
                                    else None
                                )
                                supplier_item.minimum_order_quantity = (
                                    Decimal(supplier_moqs[i]) if i < len(supplier_moqs) and supplier_moqs[i] else None
                                )
                                supplier_item.lead_time_days = (
                                    int(supplier_lead_times[i])
                                    if i < len(supplier_lead_times) and supplier_lead_times[i]
                                    else None
                                )
                                supplier_item.is_preferred = (
                                    supplier_item_id in supplier_preferred if supplier_preferred else False
                                )
                                supplier_item.updated_at = datetime.utcnow()
                                processed_ids.add(supplier_item_id_int)
                        else:
                            # Create new
                            supplier_stock_item = SupplierStockItem(
                                supplier_id=int(supplier_id),
                                stock_item_id=item.id,
                                supplier_sku=(
                                    supplier_skus[i].strip() if i < len(supplier_skus) and supplier_skus[i] else None
                                ),
                                unit_cost=(
                                    Decimal(supplier_unit_costs[i])
                                    if i < len(supplier_unit_costs) and supplier_unit_costs[i]
                                    else None
                                ),
                                minimum_order_quantity=(
                                    Decimal(supplier_moqs[i]) if i < len(supplier_moqs) and supplier_moqs[i] else None
                                ),
                                lead_time_days=(
                                    int(supplier_lead_times[i])
                                    if i < len(supplier_lead_times) and supplier_lead_times[i]
                                    else None
                                ),
                                is_preferred=False,
                                currency_code=item.currency_code,
                            )
                            db.session.add(supplier_stock_item)
                    except (ValueError, InvalidOperation):
                        pass  # Skip invalid entries

            # Deactivate removed supplier items
            for supplier_item_id, supplier_item in existing_supplier_items.items():
                if supplier_item_id not in processed_ids:
                    supplier_item.is_active = False
                    supplier_item.updated_at = datetime.utcnow()

            safe_commit()

            log_event("stock_item_updated", stock_item_id=item.id)
            flash(_("Stock item updated successfully."), "success")
            return redirect(url_for("inventory.view_stock_item", item_id=item.id))

        except Exception as e:
            db.session.rollback()
            flash(_("Error updating stock item: %(error)s", error=str(e)), "error")

    suppliers = Supplier.query.filter_by(is_active=True).order_by(Supplier.name).all()
    suppliers_dict = [supplier.to_dict() for supplier in suppliers]
    return render_template("inventory/stock_items/form.html", item=item, suppliers=suppliers_dict)


@inventory_bp.route("/inventory/items/<int:item_id>/delete", methods=["POST"])
@login_required
@admin_or_permission_required("manage_stock_items")
def delete_stock_item(item_id):
    """Delete stock item"""
    item = StockItem.query.get_or_404(item_id)

    # Check if item has any stock or movements
    has_stock = WarehouseStock.query.filter_by(stock_item_id=item_id).first()
    has_movements = StockMovement.query.filter_by(stock_item_id=item_id).first()

    if has_stock or has_movements:
        flash(_("Cannot delete stock item with existing stock or movement history."), "error")
        return redirect(url_for("inventory.view_stock_item", item_id=item_id))

    try:
        db.session.delete(item)
        safe_commit()

        log_event("stock_item_deleted", stock_item_id=item_id, sku=item.sku)
        flash(_("Stock item deleted successfully."), "success")
        return redirect(url_for("inventory.list_stock_items"))
    except Exception as e:
        db.session.rollback()
        flash(_("Error deleting stock item: %(error)s", error=str(e)), "error")
        return redirect(url_for("inventory.view_stock_item", item_id=item_id))


# ==================== Warehouses ====================


@inventory_bp.route("/inventory/warehouses")
@login_required
@admin_or_permission_required("view_inventory")
def list_warehouses():
    """List all warehouses"""
    active_only = request.args.get("active", "true").lower() == "true"

    query = Warehouse.query

    if active_only:
        query = query.filter_by(is_active=True)

    warehouses = query.order_by(Warehouse.code).all()

    return render_template("inventory/warehouses/list.html", warehouses=warehouses, active_only=active_only)


@inventory_bp.route("/inventory/warehouses/new", methods=["GET", "POST"])
@login_required
@admin_or_permission_required("manage_warehouses")
def new_warehouse():
    """Create a new warehouse"""
    if request.method == "POST":
        try:
            code = request.form.get("code", "").strip().upper()

            # Check if code already exists
            existing = Warehouse.query.filter_by(code=code).first()
            if existing:
                flash(_("Warehouse code already exists. Please use a different code."), "error")
                return render_template("inventory/warehouses/form.html", warehouse=None)

            warehouse = Warehouse(
                name=request.form.get("name", "").strip(),
                code=code,
                created_by=current_user.id,
                address=request.form.get("address", "").strip() or None,
                contact_person=request.form.get("contact_person", "").strip() or None,
                contact_email=request.form.get("contact_email", "").strip() or None,
                contact_phone=request.form.get("contact_phone", "").strip() or None,
                is_active=request.form.get("is_active") == "on",
                notes=request.form.get("notes", "").strip() or None,
            )

            db.session.add(warehouse)
            safe_commit()

            log_event("warehouse_created", warehouse_id=warehouse.id)
            flash(_("Warehouse created successfully."), "success")
            return redirect(url_for("inventory.view_warehouse", warehouse_id=warehouse.id))

        except Exception as e:
            db.session.rollback()
            flash(_("Error creating warehouse: %(error)s", error=str(e)), "error")

    return render_template("inventory/warehouses/form.html", warehouse=None)


@inventory_bp.route("/inventory/warehouses/<int:warehouse_id>")
@login_required
@admin_or_permission_required("view_inventory")
def view_warehouse(warehouse_id):
    """View warehouse details"""
    warehouse = Warehouse.query.get_or_404(warehouse_id)

    # Get stock levels in this warehouse
    stock_levels = (
        WarehouseStock.query.filter_by(warehouse_id=warehouse_id).join(StockItem).order_by(StockItem.name).all()
    )

    # Get recent movements
    recent_movements = (
        StockMovement.query.filter_by(warehouse_id=warehouse_id).order_by(StockMovement.moved_at.desc()).limit(20).all()
    )

    return render_template(
        "inventory/warehouses/view.html",
        warehouse=warehouse,
        stock_levels=stock_levels,
        recent_movements=recent_movements,
    )


@inventory_bp.route("/inventory/warehouses/<int:warehouse_id>/edit", methods=["GET", "POST"])
@login_required
@admin_or_permission_required("manage_warehouses")
def edit_warehouse(warehouse_id):
    """Edit warehouse"""
    warehouse = Warehouse.query.get_or_404(warehouse_id)

    if request.method == "POST":
        try:
            # Check if code is being changed
            new_code = request.form.get("code", "").strip().upper()
            if new_code != warehouse.code:
                existing = Warehouse.query.filter_by(code=new_code).first()
                if existing:
                    flash(_("Warehouse code already exists. Please use a different code."), "error")
                    return render_template("inventory/warehouses/form.html", warehouse=warehouse)

            warehouse.name = request.form.get("name", "").strip()
            warehouse.code = new_code
            warehouse.address = request.form.get("address", "").strip() or None
            warehouse.contact_person = request.form.get("contact_person", "").strip() or None
            warehouse.contact_email = request.form.get("contact_email", "").strip() or None
            warehouse.contact_phone = request.form.get("contact_phone", "").strip() or None
            warehouse.is_active = request.form.get("is_active") == "on"
            warehouse.notes = request.form.get("notes", "").strip() or None
            warehouse.updated_at = datetime.utcnow()

            safe_commit()

            log_event("warehouse_updated", warehouse_id=warehouse.id)
            flash(_("Warehouse updated successfully."), "success")
            return redirect(url_for("inventory.view_warehouse", warehouse_id=warehouse.id))

        except Exception as e:
            db.session.rollback()
            flash(_("Error updating warehouse: %(error)s", error=str(e)), "error")

    return render_template("inventory/warehouses/form.html", warehouse=warehouse)


@inventory_bp.route("/inventory/warehouses/<int:warehouse_id>/delete", methods=["POST"])
@login_required
@admin_or_permission_required("manage_warehouses")
def delete_warehouse(warehouse_id):
    """Delete warehouse"""
    warehouse = Warehouse.query.get_or_404(warehouse_id)

    # Check if warehouse has stock
    has_stock = WarehouseStock.query.filter_by(warehouse_id=warehouse_id).first()

    if has_stock:
        flash(_("Cannot delete warehouse with existing stock. Please transfer or remove all stock first."), "error")
        return redirect(url_for("inventory.view_warehouse", warehouse_id=warehouse_id))

    try:
        db.session.delete(warehouse)
        safe_commit()

        log_event("warehouse_deleted", warehouse_id=warehouse_id)
        flash(_("Warehouse deleted successfully."), "success")
        return redirect(url_for("inventory.list_warehouses"))
    except Exception as e:
        db.session.rollback()
        flash(_("Error deleting warehouse: %(error)s", error=str(e)), "error")
        return redirect(url_for("inventory.view_warehouse", warehouse_id=warehouse_id))


# ==================== Stock Levels ====================


@inventory_bp.route("/inventory/stock-levels")
@login_required
@admin_or_permission_required("view_stock_levels")
def stock_levels():
    """View stock levels across all warehouses"""
    warehouse_id = request.args.get("warehouse_id", type=int)
    category = request.args.get("category", "")
    low_stock_only = request.args.get("low_stock", "false").lower() == "true"

    query = WarehouseStock.query.join(StockItem).join(Warehouse)

    if warehouse_id:
        query = query.filter_by(warehouse_id=warehouse_id)

    if category:
        query = query.filter(StockItem.category == category)

    stock_levels = query.order_by(Warehouse.code, StockItem.name).all()

    # Filter low stock if requested
    if low_stock_only:
        stock_levels = [
            sl
            for sl in stock_levels
            if sl.stock_item.reorder_point and sl.quantity_on_hand < sl.stock_item.reorder_point
        ]

    # Get warehouses and categories for filters
    warehouses = Warehouse.query.filter_by(is_active=True).order_by(Warehouse.code).all()
    categories = (
        db.session.query(StockItem.category)
        .distinct()
        .filter(StockItem.category.isnot(None))
        .order_by(StockItem.category)
        .all()
    )
    categories = [cat[0] for cat in categories]

    return render_template(
        "inventory/stock_levels/list.html",
        stock_levels=stock_levels,
        warehouses=warehouses,
        categories=categories,
        selected_warehouse_id=warehouse_id,
        selected_category=category,
        low_stock_only=low_stock_only,
    )


@inventory_bp.route("/inventory/stock-levels/warehouse/<int:warehouse_id>")
@login_required
@admin_or_permission_required("view_stock_levels")
def stock_levels_by_warehouse(warehouse_id):
    """View stock levels for a specific warehouse"""
    warehouse = Warehouse.query.get_or_404(warehouse_id)
    category = request.args.get("category", "")
    low_stock_only = request.args.get("low_stock", "false").lower() == "true"

    query = WarehouseStock.query.filter_by(warehouse_id=warehouse_id).join(StockItem)

    if category:
        query = query.filter(StockItem.category == category)

    stock_levels = query.order_by(StockItem.name).all()

    # Filter low stock if requested
    if low_stock_only:
        stock_levels = [
            sl
            for sl in stock_levels
            if sl.stock_item.reorder_point and sl.quantity_on_hand < sl.stock_item.reorder_point
        ]

    # Get categories for filter
    categories = (
        db.session.query(StockItem.category)
        .distinct()
        .filter(StockItem.category.isnot(None))
        .order_by(StockItem.category)
        .all()
    )
    categories = [cat[0] for cat in categories]

    return render_template(
        "inventory/stock_levels/warehouse.html",
        warehouse=warehouse,
        stock_levels=stock_levels,
        categories=categories,
        selected_category=category,
        low_stock_only=low_stock_only,
    )


@inventory_bp.route("/inventory/stock-levels/item/<int:item_id>")
@login_required
@admin_or_permission_required("view_stock_levels")
def stock_levels_by_item(item_id):
    """View stock levels for a specific item across all warehouses"""
    item = StockItem.query.get_or_404(item_id)

    stock_levels = WarehouseStock.query.filter_by(stock_item_id=item_id).join(Warehouse).order_by(Warehouse.code).all()

    return render_template("inventory/stock_levels/item.html", item=item, stock_levels=stock_levels)


# ==================== Stock Movements ====================


@inventory_bp.route("/inventory/movements")
@login_required
@admin_or_permission_required("view_stock_history")
def list_movements():
    """List stock movements"""
    movement_type = request.args.get("type", "")
    stock_item_id = request.args.get("item_id", type=int)
    warehouse_id = request.args.get("warehouse_id", type=int)
    reference_type = request.args.get("reference_type", "")

    query = StockMovement.query

    if movement_type:
        query = query.filter_by(movement_type=movement_type)

    if stock_item_id:
        query = query.filter_by(stock_item_id=stock_item_id)

    if warehouse_id:
        query = query.filter_by(warehouse_id=warehouse_id)

    if reference_type:
        query = query.filter_by(reference_type=reference_type)

    movements = query.order_by(StockMovement.moved_at.desc()).limit(100).all()

    return render_template(
        "inventory/movements/list.html",
        movements=movements,
        movement_type=movement_type,
        stock_item_id=stock_item_id,
        warehouse_id=warehouse_id,
        reference_type=reference_type,
    )


@inventory_bp.route("/inventory/movements/new", methods=["GET", "POST"])
@login_required
@admin_or_permission_required("manage_stock_movements")
def new_movement():
    """Create a stock movement/adjustment"""
    if request.method == "POST":
        try:
            movement_type = request.form.get("movement_type", "adjustment")
            stock_item_id = int(request.form.get("stock_item_id"))
            warehouse_id = int(request.form.get("warehouse_id"))
            quantity = Decimal(request.form.get("quantity"))
            reason = request.form.get("reason", "").strip() or None
            notes = request.form.get("notes", "").strip() or None

            # Optional devaluation for return/waste
            devalue_enabled = request.form.get("devalue_enabled") == "on"
            devalue_method = (request.form.get("devalue_method") or "percent").strip().lower()
            devalue_percent_raw = request.form.get("devalue_percent")
            devalue_unit_cost_raw = request.form.get("devalue_unit_cost")

            lot_type = None
            unit_cost_override = None
            consume_from_lot_id = None

            # Manual devaluation: revalue qty (no stock change)
            if movement_type == "devaluation":
                if quantity <= 0:
                    raise ValueError("Devaluation quantity must be positive")

                item = StockItem.query.get_or_404(stock_item_id)
                base_cost = item.default_cost or Decimal("0")

                if devalue_method == "percent":
                    try:
                        pct = Decimal(devalue_percent_raw) if devalue_percent_raw not in [None, ""] else Decimal("0")
                    except Exception:
                        pct = Decimal("0")
                    if pct < 0:
                        pct = Decimal("0")
                    if pct > 100:
                        pct = Decimal("100")
                    unit_cost_override = (base_cost * (Decimal("100") - pct) / Decimal("100")).quantize(Decimal("0.01"))
                elif devalue_method == "fixed":
                    if devalue_unit_cost_raw in [None, ""]:
                        unit_cost_override = base_cost
                    else:
                        unit_cost_override = Decimal(devalue_unit_cost_raw).quantize(Decimal("0.01"))
                else:
                    unit_cost_override = base_cost

                if unit_cost_override < 0:
                    unit_cost_override = Decimal("0.00")

                StockMovement.record_devaluation(
                    stock_item_id=stock_item_id,
                    warehouse_id=warehouse_id,
                    quantity=quantity,
                    moved_by=current_user.id,
                    new_unit_cost=unit_cost_override,
                    reason=reason or "Manual devaluation",
                    notes=notes,
                )

                safe_commit()
                flash(_("Stock devaluation recorded successfully."), "success")
                return redirect(url_for("inventory.list_movements"))

            if movement_type in ["return", "waste"] and devalue_enabled:
                item = StockItem.query.get_or_404(stock_item_id)
                base_cost = item.default_cost or Decimal("0")

                if devalue_method == "percent":
                    try:
                        pct = Decimal(devalue_percent_raw) if devalue_percent_raw not in [None, ""] else Decimal("0")
                    except Exception:
                        pct = Decimal("0")
                    if pct < 0:
                        pct = Decimal("0")
                    if pct > 100:
                        pct = Decimal("100")
                    unit_cost_override = (base_cost * (Decimal("100") - pct) / Decimal("100")).quantize(Decimal("0.01"))
                elif devalue_method == "fixed":
                    if devalue_unit_cost_raw in [None, ""]:
                        unit_cost_override = base_cost
                    else:
                        unit_cost_override = Decimal(devalue_unit_cost_raw).quantize(Decimal("0.01"))
                else:
                    unit_cost_override = base_cost

                if unit_cost_override < 0:
                    unit_cost_override = Decimal("0.00")

                # Returns: book inbound directly into a devalued lot.
                if movement_type == "return":
                    lot_type = "devalued"

                # Waste: if you want the waste to reflect the devalued cost, revalue that qty first
                # (no stock change), then waste the resulting devalued lot.
                if movement_type == "waste":
                    if quantity >= 0:
                        raise ValueError("Waste movements must use a negative quantity")
                    qty_to_waste = abs(quantity)
                    _deval_move, deval_lot = StockMovement.record_devaluation(
                        stock_item_id=stock_item_id,
                        warehouse_id=warehouse_id,
                        quantity=qty_to_waste,
                        moved_by=current_user.id,
                        new_unit_cost=unit_cost_override,
                        reason=reason or "Devaluation before waste",
                        notes=notes,
                    )
                    consume_from_lot_id = deval_lot.id

            movement, updated_stock = StockMovement.record_movement(
                movement_type=movement_type,
                stock_item_id=stock_item_id,
                warehouse_id=warehouse_id,
                quantity=quantity,
                moved_by=current_user.id,
                reason=reason,
                notes=notes,
                unit_cost=unit_cost_override,
                lot_type=lot_type,
                consume_from_lot_id=consume_from_lot_id,
                update_stock=True,
            )

            safe_commit()

            log_event(
                "stock_movement_created",
                movement_id=movement.id,
                movement_type=movement_type,
                stock_item_id=stock_item_id,
                warehouse_id=warehouse_id,
            )
            flash(_("Stock movement recorded successfully."), "success")
            return redirect(url_for("inventory.list_movements"))

        except Exception as e:
            db.session.rollback()
            flash(_("Error recording stock movement: %(error)s", error=str(e)), "error")

    # Get items and warehouses for form
    stock_items = StockItem.query.filter_by(is_active=True, is_trackable=True).order_by(StockItem.name).all()
    warehouses = Warehouse.query.filter_by(is_active=True).order_by(Warehouse.code).all()

    return render_template("inventory/movements/form.html", stock_items=stock_items, warehouses=warehouses)


# ==================== Stock Transfers ====================


@inventory_bp.route("/inventory/transfers")
@login_required
@admin_or_permission_required("transfer_stock")
def list_transfers():
    """List stock transfers between warehouses"""
    query = StockMovement.query.filter_by(movement_type="transfer")

    # Filter by date range if provided
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(StockMovement.moved_at >= date_from_obj)
        except ValueError:
            pass

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d")
            # Include the entire day
            date_to_obj = date_to_obj.replace(hour=23, minute=59, second=59)
            query = query.filter(StockMovement.moved_at <= date_to_obj)
        except ValueError:
            pass

    # Group transfers by reference_id (transfers have paired movements)
    transfers = query.order_by(StockMovement.moved_at.desc()).limit(100).all()

    # Group by reference_id to show pairs together
    transfer_groups = {}
    for movement in transfers:
        if movement.reference_type == "transfer" and movement.reference_id:
            if movement.reference_id not in transfer_groups:
                transfer_groups[movement.reference_id] = []
            transfer_groups[movement.reference_id].append(movement)

    return render_template(
        "inventory/transfers/list.html", transfer_groups=transfer_groups, date_from=date_from, date_to=date_to
    )


@inventory_bp.route("/inventory/transfers/new", methods=["GET", "POST"])
@login_required
@admin_or_permission_required("transfer_stock")
def new_transfer():
    """Create a stock transfer between warehouses"""
    if request.method == "POST":
        try:
            stock_item_id = int(request.form.get("stock_item_id"))
            from_warehouse_id = int(request.form.get("from_warehouse_id"))
            to_warehouse_id = int(request.form.get("to_warehouse_id"))
            quantity = Decimal(request.form.get("quantity"))
            notes = request.form.get("notes", "").strip() or None

            # Validate warehouses are different
            if from_warehouse_id == to_warehouse_id:
                flash(_("Source and destination warehouses must be different."), "error")
                stock_items = (
                    StockItem.query.filter_by(is_active=True, is_trackable=True).order_by(StockItem.name).all()
                )
                warehouses = Warehouse.query.filter_by(is_active=True).order_by(Warehouse.code).all()
                return render_template("inventory/transfers/form.html", stock_items=stock_items, warehouses=warehouses)

            # Check available stock in source warehouse
            source_stock = WarehouseStock.query.filter_by(
                warehouse_id=from_warehouse_id, stock_item_id=stock_item_id
            ).first()

            if not source_stock or source_stock.quantity_available < quantity:
                flash(_("Insufficient stock available in source warehouse."), "error")
                stock_items = (
                    StockItem.query.filter_by(is_active=True, is_trackable=True).order_by(StockItem.name).all()
                )
                warehouses = Warehouse.query.filter_by(is_active=True).order_by(Warehouse.code).all()
                return render_template("inventory/transfers/form.html", stock_items=stock_items, warehouses=warehouses)

            # Generate transfer reference ID (use timestamp-based ID)
            transfer_ref_id = int(datetime.now().timestamp() * 1000)

            # Create transfer reason
            stock_item = StockItem.query.get(stock_item_id)
            from_warehouse = Warehouse.query.get(from_warehouse_id)
            to_warehouse = Warehouse.query.get(to_warehouse_id)
            reason = f"Transfer from {from_warehouse.code} to {to_warehouse.code}"

            # Create negative movement (from source warehouse)
            out_movement, _unused = StockMovement.record_movement(
                movement_type="transfer",
                stock_item_id=stock_item_id,
                warehouse_id=from_warehouse_id,
                quantity=-quantity,  # Negative for removal
                moved_by=current_user.id,
                reference_type="transfer",
                reference_id=transfer_ref_id,
                reason=reason,
                notes=notes,
                update_stock=True,
            )

            # Create positive movement (to destination warehouse)
            in_movement, _unused = StockMovement.record_movement(
                movement_type="transfer",
                stock_item_id=stock_item_id,
                warehouse_id=to_warehouse_id,
                quantity=quantity,  # Positive for addition
                moved_by=current_user.id,
                reference_type="transfer",
                reference_id=transfer_ref_id,
                reason=reason,
                notes=notes,
                update_stock=True,
            )

            safe_commit()

            log_event(
                "stock_transfer_created",
                transfer_ref_id=transfer_ref_id,
                stock_item_id=stock_item_id,
                from_warehouse_id=from_warehouse_id,
                to_warehouse_id=to_warehouse_id,
                quantity=float(quantity),
            )
            flash(_("Stock transfer completed successfully."), "success")
            return redirect(url_for("inventory.list_transfers"))

        except Exception as e:
            db.session.rollback()
            flash(_("Error creating transfer: %(error)s", error=str(e)), "error")

    # Get items and warehouses for form
    stock_items = StockItem.query.filter_by(is_active=True, is_trackable=True).order_by(StockItem.name).all()
    warehouses = Warehouse.query.filter_by(is_active=True).order_by(Warehouse.code).all()

    return render_template("inventory/transfers/form.html", stock_items=stock_items, warehouses=warehouses)


# ==================== Stock Adjustments ====================


@inventory_bp.route("/inventory/adjustments")
@login_required
@admin_or_permission_required("view_stock_history")
def list_adjustments():
    """List stock adjustments"""
    query = StockMovement.query.filter_by(movement_type="adjustment")

    # Filter by warehouse, item, or date
    warehouse_id = request.args.get("warehouse_id", type=int)
    stock_item_id = request.args.get("stock_item_id", type=int)
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    if warehouse_id:
        query = query.filter_by(warehouse_id=warehouse_id)

    if stock_item_id:
        query = query.filter_by(stock_item_id=stock_item_id)

    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(StockMovement.moved_at >= date_from_obj)
        except ValueError:
            pass

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d")
            date_to_obj = date_to_obj.replace(hour=23, minute=59, second=59)
            query = query.filter(StockMovement.moved_at <= date_to_obj)
        except ValueError:
            pass

    adjustments = query.order_by(StockMovement.moved_at.desc()).limit(100).all()

    # Get warehouses and items for filters
    warehouses = Warehouse.query.filter_by(is_active=True).order_by(Warehouse.code).all()
    stock_items = StockItem.query.filter_by(is_active=True).order_by(StockItem.name).all()

    return render_template(
        "inventory/adjustments/list.html",
        adjustments=adjustments,
        warehouses=warehouses,
        stock_items=stock_items,
        selected_warehouse_id=warehouse_id,
        selected_stock_item_id=stock_item_id,
        date_from=date_from,
        date_to=date_to,
    )


@inventory_bp.route("/inventory/adjustments/new", methods=["GET", "POST"])
@login_required
@admin_or_permission_required("manage_stock_movements")
def new_adjustment():
    """Create a stock adjustment"""
    # Reuse the movements form but force movement_type to 'adjustment'
    if request.method == "POST":
        try:
            stock_item_id = int(request.form.get("stock_item_id"))
            warehouse_id = int(request.form.get("warehouse_id"))
            quantity = Decimal(request.form.get("quantity"))
            reason = request.form.get("reason", "").strip() or None
            notes = request.form.get("notes", "").strip() or None

            movement, updated_stock = StockMovement.record_movement(
                movement_type="adjustment",
                stock_item_id=stock_item_id,
                warehouse_id=warehouse_id,
                quantity=quantity,
                moved_by=current_user.id,
                reason=reason or "Stock adjustment",
                notes=notes,
                update_stock=True,
            )

            safe_commit()

            log_event(
                "stock_adjustment_created",
                adjustment_id=movement.id,
                stock_item_id=stock_item_id,
                warehouse_id=warehouse_id,
                quantity=float(quantity),
            )
            flash(_("Stock adjustment recorded successfully."), "success")
            return redirect(url_for("inventory.list_adjustments"))

        except Exception as e:
            db.session.rollback()
            flash(_("Error recording adjustment: %(error)s", error=str(e)), "error")

    # Get items and warehouses for form
    stock_items = StockItem.query.filter_by(is_active=True, is_trackable=True).order_by(StockItem.name).all()
    warehouses = Warehouse.query.filter_by(is_active=True).order_by(Warehouse.code).all()

    return render_template("inventory/adjustments/form.html", stock_items=stock_items, warehouses=warehouses)


# ==================== Stock Item History ====================


@inventory_bp.route("/inventory/items/<int:item_id>/history")
@login_required
@admin_or_permission_required("view_stock_history")
def stock_item_history(item_id):
    """View movement history for a stock item"""
    item = StockItem.query.get_or_404(item_id)

    # Get filters
    warehouse_id = request.args.get("warehouse_id", type=int)
    movement_type = request.args.get("movement_type", "")
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    query = StockMovement.query.filter_by(stock_item_id=item_id)

    if warehouse_id:
        query = query.filter_by(warehouse_id=warehouse_id)

    if movement_type:
        query = query.filter_by(movement_type=movement_type)

    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(StockMovement.moved_at >= date_from_obj)
        except ValueError:
            pass

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d")
            date_to_obj = date_to_obj.replace(hour=23, minute=59, second=59)
            query = query.filter(StockMovement.moved_at <= date_to_obj)
        except ValueError:
            pass

    movements = query.order_by(StockMovement.moved_at.desc()).limit(200).all()

    # Get warehouses for filter
    warehouses = Warehouse.query.filter_by(is_active=True).order_by(Warehouse.code).all()

    return render_template(
        "inventory/stock_items/history.html",
        item=item,
        movements=movements,
        warehouses=warehouses,
        selected_warehouse_id=warehouse_id,
        selected_movement_type=movement_type,
        date_from=date_from,
        date_to=date_to,
    )


# ==================== Low Stock Alerts ====================


@inventory_bp.route("/inventory/low-stock")
@login_required
@admin_or_permission_required("view_inventory")
def low_stock_alerts():
    """View low stock alerts"""
    items = StockItem.query.filter_by(is_active=True, is_trackable=True).all()

    low_stock_items = []
    for item in items:
        if item.reorder_point:
            stock_levels = WarehouseStock.query.filter_by(stock_item_id=item.id).all()
            for stock in stock_levels:
                if stock.quantity_on_hand < item.reorder_point:
                    low_stock_items.append(
                        {
                            "item": item,
                            "warehouse": stock.warehouse,
                            "quantity_on_hand": stock.quantity_on_hand,
                            "reorder_point": item.reorder_point,
                            "reorder_quantity": item.reorder_quantity or 0,
                            "shortfall": item.reorder_point - stock.quantity_on_hand,
                        }
                    )

    return render_template("inventory/low_stock/list.html", low_stock_items=low_stock_items)


# ==================== Stock Reservations ====================


@inventory_bp.route("/inventory/reservations")
@login_required
@admin_or_permission_required("view_stock_history")
def list_reservations():
    """List stock reservations"""
    status = request.args.get("status", "reserved")

    query = StockReservation.query

    if status != "all":
        query = query.filter_by(status=status)

    reservations = query.order_by(StockReservation.reserved_at.desc()).all()

    return render_template("inventory/reservations/list.html", reservations=reservations, status=status)


@inventory_bp.route("/inventory/reservations/<int:reservation_id>/fulfill", methods=["POST"])
@login_required
@admin_or_permission_required("manage_stock_reservations")
def fulfill_reservation(reservation_id):
    """Fulfill a stock reservation"""
    reservation = StockReservation.query.get_or_404(reservation_id)

    try:
        reservation.fulfill()
        safe_commit()

        log_event("stock_reservation_fulfilled", reservation_id=reservation_id)
        flash(_("Reservation fulfilled successfully."), "success")
    except Exception as e:
        db.session.rollback()
        flash(_("Error fulfilling reservation: %(error)s", error=str(e)), "error")

    return redirect(url_for("inventory.list_reservations"))


@inventory_bp.route("/inventory/reservations/<int:reservation_id>/cancel", methods=["POST"])
@login_required
@admin_or_permission_required("manage_stock_reservations")
def cancel_reservation(reservation_id):
    """Cancel a stock reservation"""
    reservation = StockReservation.query.get_or_404(reservation_id)

    try:
        reservation.cancel()
        safe_commit()

        log_event("stock_reservation_cancelled", reservation_id=reservation_id)
        flash(_("Reservation cancelled successfully."), "success")
    except Exception as e:
        db.session.rollback()
        flash(_("Error cancelling reservation: %(error)s", error=str(e)), "error")

    return redirect(url_for("inventory.list_reservations"))


# ==================== Suppliers ====================


@inventory_bp.route("/inventory/suppliers")
@login_required
@admin_or_permission_required("view_inventory")
def list_suppliers():
    """List all suppliers"""
    search = request.args.get("search", "").strip()
    active_only = request.args.get("active", "true").lower() == "true"

    query = Supplier.query

    if active_only:
        query = query.filter_by(is_active=True)

    if search:
        like = f"%{search}%"
        query = query.filter(or_(Supplier.code.ilike(like), Supplier.name.ilike(like), Supplier.email.ilike(like)))

    suppliers = query.order_by(Supplier.name).all()

    return render_template("inventory/suppliers/list.html", suppliers=suppliers, search=search, active_only=active_only)


@inventory_bp.route("/inventory/suppliers/new", methods=["GET", "POST"])
@login_required
@admin_or_permission_required("manage_inventory")
def new_supplier():
    """Create a new supplier"""
    if request.method == "POST":
        try:
            code = request.form.get("code", "").strip()
            
            # Check for duplicate code
            existing = Supplier.query.filter_by(code=code).first()
            if existing:
                flash(_("Supplier with code '%(code)s' already exists", code=code), "error")
                return render_template("inventory/suppliers/form.html", supplier=None)
            
            supplier = Supplier(
                code=code,
                name=request.form.get("name", "").strip(),
                created_by=current_user.id,
                description=request.form.get("description", "").strip() or None,
                contact_person=request.form.get("contact_person", "").strip() or None,
                email=request.form.get("email", "").strip() or None,
                phone=request.form.get("phone", "").strip() or None,
                address=request.form.get("address", "").strip() or None,
                website=request.form.get("website", "").strip() or None,
                tax_id=request.form.get("tax_id", "").strip() or None,
                payment_terms=request.form.get("payment_terms", "").strip() or None,
                currency_code=request.form.get("currency_code", "EUR"),
                is_active=request.form.get("is_active") == "on",
                notes=request.form.get("notes", "").strip() or None,
            )

            db.session.add(supplier)
            safe_commit()

            log_event("supplier_created", supplier_id=supplier.id, supplier_code=supplier.code)
            flash(_("Supplier created successfully."), "success")
            return redirect(url_for("inventory.view_supplier", supplier_id=supplier.id))

        except Exception as e:
            db.session.rollback()
            flash(_("Error creating supplier: %(error)s", error=str(e)), "error")

    return render_template("inventory/suppliers/form.html", supplier=None)


@inventory_bp.route("/inventory/suppliers/<int:supplier_id>")
@login_required
@admin_or_permission_required("view_inventory")
def view_supplier(supplier_id):
    """View supplier details"""
    supplier = Supplier.query.get_or_404(supplier_id)

    # Get stock items from this supplier
    from sqlalchemy.orm import joinedload

    supplier_items = (
        SupplierStockItem.query.options(joinedload(SupplierStockItem.stock_item))
        .filter_by(supplier_id=supplier_id, is_active=True)
        .all()
    )

    # Sort by preferred, then by stock item name
    supplier_items = sorted(supplier_items, key=lambda x: (not x.is_preferred, x.stock_item.name))

    return render_template("inventory/suppliers/view.html", supplier=supplier, supplier_items=supplier_items)


@inventory_bp.route("/inventory/suppliers/<int:supplier_id>/edit", methods=["GET", "POST"])
@login_required
@admin_or_permission_required("manage_inventory")
def edit_supplier(supplier_id):
    """Edit supplier"""
    supplier = Supplier.query.get_or_404(supplier_id)

    if request.method == "POST":
        try:
            new_code = request.form.get("code", "").strip().upper()

            # Check if code is being changed and if new code exists
            if new_code != supplier.code:
                existing = Supplier.query.filter_by(code=new_code).first()
                if existing:
                    flash(_("Supplier code already exists. Please use a different code."), "error")
                    return render_template("inventory/suppliers/form.html", supplier=supplier)

            supplier.code = new_code
            supplier.name = request.form.get("name", "").strip()
            supplier.description = request.form.get("description", "").strip() or None
            supplier.contact_person = request.form.get("contact_person", "").strip() or None
            supplier.email = request.form.get("email", "").strip() or None
            supplier.phone = request.form.get("phone", "").strip() or None
            supplier.address = request.form.get("address", "").strip() or None
            supplier.website = request.form.get("website", "").strip() or None
            supplier.tax_id = request.form.get("tax_id", "").strip() or None
            supplier.payment_terms = request.form.get("payment_terms", "").strip() or None
            supplier.currency_code = request.form.get("currency_code", "EUR")
            supplier.is_active = request.form.get("is_active") == "on"
            supplier.notes = request.form.get("notes", "").strip() or None
            supplier.updated_at = datetime.utcnow()

            safe_commit()

            log_event("supplier_updated", supplier_id=supplier.id)
            flash(_("Supplier updated successfully."), "success")
            return redirect(url_for("inventory.view_supplier", supplier_id=supplier.id))

        except Exception as e:
            db.session.rollback()
            flash(_("Error updating supplier: %(error)s", error=str(e)), "error")

    return render_template("inventory/suppliers/form.html", supplier=supplier)


@inventory_bp.route("/inventory/suppliers/<int:supplier_id>/delete", methods=["POST"])
@login_required
@admin_or_permission_required("manage_inventory")
def delete_supplier(supplier_id):
    """Delete supplier"""
    supplier = Supplier.query.get_or_404(supplier_id)

    # Check if supplier has associated stock items
    item_count = SupplierStockItem.query.filter_by(supplier_id=supplier_id).count()

    if item_count > 0:
        flash(_("Cannot delete supplier with associated stock items. Remove items first."), "error")
        return redirect(url_for("inventory.view_supplier", supplier_id=supplier_id))

    try:
        code = supplier.code
        db.session.delete(supplier)
        safe_commit()

        log_event("supplier_deleted", supplier_code=code)
        flash(_("Supplier deleted successfully."), "success")
    except Exception as e:
        db.session.rollback()
        flash(_("Error deleting supplier: %(error)s", error=str(e)), "error")

    return redirect(url_for("inventory.list_suppliers"))


# ==================== Purchase Orders ====================


@inventory_bp.route("/inventory/purchase-orders")
@login_required
@admin_or_permission_required("view_inventory")
def list_purchase_orders():
    """List all purchase orders"""
    status = request.args.get("status", "")
    supplier_id = request.args.get("supplier_id", type=int)

    query = PurchaseOrder.query

    if status:
        query = query.filter_by(status=status)

    if supplier_id:
        query = query.filter_by(supplier_id=supplier_id)

    purchase_orders = query.order_by(PurchaseOrder.order_date.desc(), PurchaseOrder.po_number.desc()).limit(100).all()

    # Get suppliers for filter
    suppliers = Supplier.query.filter_by(is_active=True).order_by(Supplier.name).all()

    return render_template(
        "inventory/purchase_orders/list.html",
        purchase_orders=purchase_orders,
        suppliers=suppliers,
        selected_status=status,
        selected_supplier_id=supplier_id,
    )


@inventory_bp.route("/inventory/purchase-orders/new", methods=["GET", "POST"])
@login_required
@admin_or_permission_required("manage_inventory")
def new_purchase_order():
    """Create a new purchase order"""
    if request.method == "POST":
        try:
            # Generate PO number
            last_po = PurchaseOrder.query.order_by(PurchaseOrder.id.desc()).first()
            next_id = (last_po.id + 1) if last_po else 1
            po_number = f"PO-{datetime.now().strftime('%Y%m%d')}-{next_id:04d}"

            purchase_order = PurchaseOrder(
                po_number=po_number,
                supplier_id=int(request.form.get("supplier_id")),
                order_date=datetime.strptime(request.form.get("order_date"), "%Y-%m-%d").date(),
                created_by=current_user.id,
                expected_delivery_date=(
                    datetime.strptime(request.form.get("expected_delivery_date"), "%Y-%m-%d").date()
                    if request.form.get("expected_delivery_date")
                    else None
                ),
                notes=request.form.get("notes", "").strip() or None,
                internal_notes=request.form.get("internal_notes", "").strip() or None,
                currency_code=request.form.get("currency_code", "EUR"),
            )

            db.session.add(purchase_order)
            db.session.flush()

            # Handle items
            item_descriptions = request.form.getlist("item_description[]")
            item_stock_ids = request.form.getlist("item_stock_item_id[]")
            item_supplier_stock_ids = request.form.getlist("item_supplier_stock_item_id[]")
            item_supplier_skus = request.form.getlist("item_supplier_sku[]")
            item_quantities = request.form.getlist("item_quantity[]")
            item_unit_costs = request.form.getlist("item_unit_cost[]")
            item_warehouse_ids = request.form.getlist("item_warehouse_id[]")

            for i, desc in enumerate(item_descriptions):
                if desc.strip():
                    try:
                        stock_item_id = (
                            int(item_stock_ids[i]) if i < len(item_stock_ids) and item_stock_ids[i] else None
                        )
                        supplier_stock_item_id = (
                            int(item_supplier_stock_ids[i])
                            if i < len(item_supplier_stock_ids) and item_supplier_stock_ids[i]
                            else None
                        )
                        warehouse_id = (
                            int(item_warehouse_ids[i])
                            if i < len(item_warehouse_ids) and item_warehouse_ids[i]
                            else None
                        )

                        item = PurchaseOrderItem(
                            purchase_order_id=purchase_order.id,
                            description=desc.strip(),
                            quantity_ordered=(
                                Decimal(item_quantities[i])
                                if i < len(item_quantities) and item_quantities[i]
                                else Decimal("1")
                            ),
                            unit_cost=(
                                Decimal(item_unit_costs[i])
                                if i < len(item_unit_costs) and item_unit_costs[i]
                                else Decimal("0")
                            ),
                            stock_item_id=stock_item_id,
                            supplier_stock_item_id=supplier_stock_item_id,
                            supplier_sku=(
                                item_supplier_skus[i].strip()
                                if i < len(item_supplier_skus) and item_supplier_skus[i]
                                else None
                            ),
                            warehouse_id=warehouse_id,
                            currency_code=purchase_order.currency_code,
                        )
                        db.session.add(item)
                    except (ValueError, InvalidOperation):
                        pass

            purchase_order.calculate_totals()
            safe_commit()

            log_event(
                "purchase_order_created",
                purchase_order_id=purchase_order.id,
                po_number=purchase_order.po_number,
            )
            flash(_("Purchase order created successfully."), "success")
            return redirect(url_for("inventory.view_purchase_order", po_id=purchase_order.id))

        except Exception as e:
            db.session.rollback()
            flash(_("Error creating purchase order: %(error)s", error=str(e)), "error")

    # Get suppliers and warehouses for form
    suppliers = Supplier.query.filter_by(is_active=True).order_by(Supplier.name).all()
    warehouses = Warehouse.query.filter_by(is_active=True).order_by(Warehouse.code).all()
    stock_items = StockItem.query.filter_by(is_active=True).order_by(StockItem.name).all()

    return render_template(
        "inventory/purchase_orders/form.html",
        purchase_order=None,
        suppliers=suppliers,
        warehouses=warehouses,
        stock_items=stock_items,
    )


@inventory_bp.route("/inventory/purchase-orders/<int:po_id>")
@login_required
@admin_or_permission_required("view_inventory")
def view_purchase_order(po_id):
    """View purchase order details"""
    purchase_order = PurchaseOrder.query.get_or_404(po_id)

    return render_template("inventory/purchase_orders/view.html", purchase_order=purchase_order)


@inventory_bp.route("/inventory/purchase-orders/<int:po_id>/edit", methods=["GET", "POST"])
@login_required
@admin_or_permission_required("manage_inventory")
def edit_purchase_order(po_id):
    """Edit purchase order"""
    purchase_order = PurchaseOrder.query.get_or_404(po_id)

    if purchase_order.status == "received":
        flash(_("Cannot edit a purchase order that has been received."), "error")
        return redirect(url_for("inventory.view_purchase_order", po_id=po_id))

    if request.method == "POST":
        try:
            purchase_order.order_date = datetime.strptime(request.form.get("order_date"), "%Y-%m-%d").date()
            purchase_order.expected_delivery_date = (
                datetime.strptime(request.form.get("expected_delivery_date"), "%Y-%m-%d").date()
                if request.form.get("expected_delivery_date")
                else None
            )
            purchase_order.notes = request.form.get("notes", "").strip() or None
            purchase_order.internal_notes = request.form.get("internal_notes", "").strip() or None
            purchase_order.currency_code = request.form.get("currency_code", "EUR")

            # Handle items - remove existing and recreate
            PurchaseOrderItem.query.filter_by(purchase_order_id=purchase_order.id).delete()

            item_descriptions = request.form.getlist("item_description[]")
            item_stock_ids = request.form.getlist("item_stock_item_id[]")
            item_supplier_stock_ids = request.form.getlist("item_supplier_stock_item_id[]")
            item_supplier_skus = request.form.getlist("item_supplier_sku[]")
            item_quantities = request.form.getlist("item_quantity[]")
            item_unit_costs = request.form.getlist("item_unit_cost[]")
            item_warehouse_ids = request.form.getlist("item_warehouse_id[]")

            for i, desc in enumerate(item_descriptions):
                if desc.strip():
                    try:
                        stock_item_id = (
                            int(item_stock_ids[i]) if i < len(item_stock_ids) and item_stock_ids[i] else None
                        )
                        supplier_stock_item_id = (
                            int(item_supplier_stock_ids[i])
                            if i < len(item_supplier_stock_ids) and item_supplier_stock_ids[i]
                            else None
                        )
                        warehouse_id = (
                            int(item_warehouse_ids[i])
                            if i < len(item_warehouse_ids) and item_warehouse_ids[i]
                            else None
                        )

                        item = PurchaseOrderItem(
                            purchase_order_id=purchase_order.id,
                            description=desc.strip(),
                            quantity_ordered=(
                                Decimal(item_quantities[i])
                                if i < len(item_quantities) and item_quantities[i]
                                else Decimal("1")
                            ),
                            unit_cost=(
                                Decimal(item_unit_costs[i])
                                if i < len(item_unit_costs) and item_unit_costs[i]
                                else Decimal("0")
                            ),
                            stock_item_id=stock_item_id,
                            supplier_stock_item_id=supplier_stock_item_id,
                            supplier_sku=(
                                item_supplier_skus[i].strip()
                                if i < len(item_supplier_skus) and item_supplier_skus[i]
                                else None
                            ),
                            warehouse_id=warehouse_id,
                            currency_code=purchase_order.currency_code,
                        )
                        db.session.add(item)
                    except (ValueError, InvalidOperation):
                        pass

            purchase_order.calculate_totals()
            safe_commit()

            log_event("purchase_order_updated", purchase_order_id=po_id)
            flash(_("Purchase order updated successfully."), "success")
            return redirect(url_for("inventory.view_purchase_order", po_id=po_id))

        except Exception as e:
            db.session.rollback()
            flash(_("Error updating purchase order: %(error)s", error=str(e)), "error")

    suppliers = Supplier.query.filter_by(is_active=True).order_by(Supplier.name).all()
    warehouses = Warehouse.query.filter_by(is_active=True).order_by(Warehouse.code).all()
    stock_items = StockItem.query.filter_by(is_active=True).order_by(StockItem.name).all()

    return render_template(
        "inventory/purchase_orders/form.html",
        purchase_order=purchase_order,
        suppliers=suppliers,
        warehouses=warehouses,
        stock_items=stock_items,
    )


@inventory_bp.route("/inventory/purchase-orders/<int:po_id>/send", methods=["POST"])
@login_required
@admin_or_permission_required("manage_inventory")
def send_purchase_order(po_id):
    """Mark purchase order as sent to supplier"""
    purchase_order = PurchaseOrder.query.get_or_404(po_id)

    if request.method == "POST":
        try:
            purchase_order.mark_as_sent()
            safe_commit()

            log_event("purchase_order_sent", purchase_order_id=po_id)
            flash(_("Purchase order marked as sent."), "success")
        except Exception as e:
            db.session.rollback()
            flash(_("Error sending purchase order: %(error)s", error=str(e)), "error")

    return redirect(url_for("inventory.view_purchase_order", po_id=po_id))


@inventory_bp.route("/inventory/purchase-orders/<int:po_id>/cancel", methods=["POST"])
@login_required
@admin_or_permission_required("manage_inventory")
def cancel_purchase_order(po_id):
    """Cancel purchase order"""
    purchase_order = PurchaseOrder.query.get_or_404(po_id)

    if request.method == "POST":
        try:
            purchase_order.cancel()
            safe_commit()

            log_event("purchase_order_cancelled", purchase_order_id=po_id)
            flash(_("Purchase order cancelled successfully."), "success")
        except Exception as e:
            db.session.rollback()
            flash(_("Error cancelling purchase order: %(error)s", error=str(e)), "error")

    return redirect(url_for("inventory.view_purchase_order", po_id=po_id))


@inventory_bp.route("/inventory/purchase-orders/<int:po_id>/delete", methods=["POST"])
@login_required
@admin_or_permission_required("manage_inventory")
def delete_purchase_order(po_id):
    """Delete purchase order"""
    purchase_order = PurchaseOrder.query.get_or_404(po_id)

    if request.method == "POST":
        try:
            if purchase_order.status == "received":
                flash(_("Cannot delete a purchase order that has been received. Cancel it instead."), "error")
                return redirect(url_for("inventory.view_purchase_order", po_id=po_id))

            po_number = purchase_order.po_number
            db.session.delete(purchase_order)
            safe_commit()

            log_event("purchase_order_deleted", po_number=po_number)
            flash(_("Purchase order deleted successfully."), "success")
            return redirect(url_for("inventory.list_purchase_orders"))
        except Exception as e:
            db.session.rollback()
            flash(_("Error deleting purchase order: %(error)s", error=str(e)), "error")

    return redirect(url_for("inventory.view_purchase_order", po_id=po_id))


@inventory_bp.route("/inventory/purchase-orders/<int:po_id>/receive", methods=["POST"])
@login_required
@admin_or_permission_required("manage_inventory")
def receive_purchase_order(po_id):
    """Mark purchase order as received and update stock"""
    purchase_order = PurchaseOrder.query.get_or_404(po_id)

    if request.method == "POST":
        try:
            # Update received quantities
            item_ids = request.form.getlist("item_id[]")
            received_quantities = request.form.getlist("quantity_received[]")

            for i, item_id in enumerate(item_ids):
                if item_id and received_quantities[i]:
                    item = PurchaseOrderItem.query.get(int(item_id))
                    if item and item.purchase_order_id == purchase_order.id:
                        item.quantity_received = Decimal(received_quantities[i])
                        item.updated_at = datetime.utcnow()

            # Mark as received (this will create stock movements)
            received_date_str = request.form.get("received_date", "").strip()
            received_date = (
                datetime.strptime(received_date_str, "%Y-%m-%d").date()
                if received_date_str
                else datetime.utcnow().date()
            )
            purchase_order.mark_as_received(received_date)

            safe_commit()

            log_event("purchase_order_received", purchase_order_id=po_id)
            flash(_("Purchase order marked as received and stock updated."), "success")
        except Exception as e:
            db.session.rollback()
            flash(_("Error receiving purchase order: %(error)s", error=str(e)), "error")

    return redirect(url_for("inventory.view_purchase_order", po_id=po_id))


# ==================== Inventory Reports ====================


@inventory_bp.route("/inventory/reports")
@login_required
@admin_or_permission_required("view_inventory_reports")
def reports_dashboard():
    """Inventory reports dashboard"""
    total_items = StockItem.query.filter_by(is_active=True).count()
    total_warehouses = Warehouse.query.filter_by(is_active=True).count()

    total_value = (
        db.session.query(func.sum(WarehouseStock.quantity_on_hand * StockItem.default_cost))
        .join(StockItem)
        .filter(StockItem.default_cost.isnot(None))
        .scalar()
        or 0
    )

    low_stock_count = 0
    items_with_reorder = StockItem.query.filter(
        StockItem.is_active == True, StockItem.is_trackable == True, StockItem.reorder_point.isnot(None)
    ).all()

    for item in items_with_reorder:
        stock_levels = WarehouseStock.query.filter_by(stock_item_id=item.id).all()
        for stock in stock_levels:
            if stock.quantity_on_hand < item.reorder_point:
                low_stock_count += 1
                break

    return render_template(
        "inventory/reports/dashboard.html",
        total_items=total_items,
        total_warehouses=total_warehouses,
        total_value=float(total_value),
        low_stock_count=low_stock_count,
    )


@inventory_bp.route("/inventory/reports/valuation")
@login_required
@admin_or_permission_required("view_inventory_reports")
def reports_valuation():
    """Stock valuation report"""
    from app.services.inventory_report_service import InventoryReportService

    warehouse_id = request.args.get("warehouse_id", type=int)
    category = request.args.get("category", "")
    currency_code = request.args.get("currency_code", "")

    service = InventoryReportService()
    valuation_data = service.get_stock_valuation(
        warehouse_id=warehouse_id,
        category=category if category else None,
        currency_code=currency_code if currency_code else None,
    )

    warehouses = Warehouse.query.filter_by(is_active=True).order_by(Warehouse.code).all()
    categories = (
        db.session.query(StockItem.category)
        .distinct()
        .filter(StockItem.category.isnot(None))
        .order_by(StockItem.category)
        .all()
    )
    categories = [cat[0] for cat in categories]

    currencies = (
        db.session.query(StockItem.currency_code)
        .distinct()
        .filter(StockItem.currency_code.isnot(None))
        .order_by(StockItem.currency_code)
        .all()
    )
    currencies = [curr[0] for curr in currencies]

    # Extract items_with_value from valuation_data for template compatibility
    items_with_value = []
    for item_detail in valuation_data.get("item_details", []):
        # Get the actual stock and item objects for the template
        stock = WarehouseStock.query.filter_by(
            stock_item_id=item_detail["item_id"], warehouse_id=item_detail["warehouse_id"]
        ).first()
        if stock:
            items_with_value.append({
                "stock": stock, 
                "value": item_detail["value"],
                "quantity": item_detail.get("quantity"),
                "cost": item_detail.get("cost")
            })

    return render_template(
        "inventory/reports/valuation.html",
        valuation_data=valuation_data,
        items_with_value=items_with_value,
        total_value=valuation_data.get("total_value", 0),
        warehouses=warehouses,
        categories=categories,
        currencies=currencies,
        selected_warehouse_id=warehouse_id,
        selected_category=category,
        selected_currency=currency_code,
    )


@inventory_bp.route("/inventory/reports/movement-history")
@login_required
@admin_or_permission_required("view_inventory_reports")
def reports_movement_history():
    """Movement history report"""
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    warehouse_id = request.args.get("warehouse_id", type=int)
    stock_item_id = request.args.get("stock_item_id", type=int)
    movement_type = request.args.get("movement_type", "")

    query = StockMovement.query

    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(StockMovement.moved_at >= date_from_obj)
        except ValueError:
            pass

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d")
            date_to_obj = date_to_obj.replace(hour=23, minute=59, second=59)
            query = query.filter(StockMovement.moved_at <= date_to_obj)
        except ValueError:
            pass

    if warehouse_id:
        query = query.filter_by(warehouse_id=warehouse_id)

    if stock_item_id:
        query = query.filter_by(stock_item_id=stock_item_id)

    if movement_type:
        query = query.filter_by(movement_type=movement_type)

    movements = query.order_by(StockMovement.moved_at.desc()).limit(500).all()

    warehouses = Warehouse.query.filter_by(is_active=True).order_by(Warehouse.code).all()
    stock_items = StockItem.query.filter_by(is_active=True).order_by(StockItem.name).all()

    return render_template(
        "inventory/reports/movement_history.html",
        movements=movements,
        warehouses=warehouses,
        stock_items=stock_items,
        selected_warehouse_id=warehouse_id,
        selected_stock_item_id=stock_item_id,
        selected_movement_type=movement_type,
        date_from=date_from,
        date_to=date_to,
    )


@inventory_bp.route("/inventory/reports/turnover")
@login_required
@admin_or_permission_required("view_inventory_reports")
def reports_turnover():
    """Inventory turnover analysis"""
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    if not date_from:
        date_from = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    if not date_to:
        date_to = datetime.now().strftime("%Y-%m-%d")

    try:
        date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
        date_to_obj = datetime.strptime(date_to, "%Y-%m-%d")
        date_to_obj = date_to_obj.replace(hour=23, minute=59, second=59)
    except ValueError:
        date_from_obj = datetime.now() - timedelta(days=365)
        date_to_obj = datetime.now()

    items_with_sales = (
        db.session.query(StockItem, func.sum(StockMovement.quantity).label("total_sold"))
        .join(StockMovement)
        .filter(
            StockMovement.movement_type == "sale",
            StockMovement.moved_at >= date_from_obj,
            StockMovement.moved_at <= date_to_obj,
            StockMovement.quantity < 0,
        )
        .group_by(StockItem.id)
        .all()
    )

    turnover_data = []
    for item, total_sold in items_with_sales:
        avg_stock = (
            db.session.query(func.avg(WarehouseStock.quantity_on_hand)).filter_by(stock_item_id=item.id).scalar() or 0
        )

        days_in_period = (date_to_obj - date_from_obj).days
        turnover_rate = 0
        if avg_stock > 0:
            turnover_rate = (
                abs(float(total_sold or 0)) / float(avg_stock) * (365 / days_in_period) if days_in_period > 0 else 0
            )

        turnover_data.append(
            {
                "item": item,
                "total_sold": abs(float(total_sold or 0)),
                "avg_stock": float(avg_stock),
                "turnover_rate": turnover_rate,
            }
        )

    turnover_data.sort(key=lambda x: x["turnover_rate"], reverse=True)

    return render_template(
        "inventory/reports/turnover.html", turnover_data=turnover_data, date_from=date_from, date_to=date_to
    )


@inventory_bp.route("/inventory/reports/low-stock")
@login_required
@admin_or_permission_required("view_inventory_reports")
def reports_low_stock():
    """Low stock report"""
    items = StockItem.query.filter_by(is_active=True, is_trackable=True).all()

    low_stock_items = []
    for item in items:
        if item.reorder_point:
            stock_levels = WarehouseStock.query.filter_by(stock_item_id=item.id).all()
            for stock in stock_levels:
                if stock.quantity_on_hand < item.reorder_point:
                    low_stock_items.append(
                        {
                            "item": item,
                            "warehouse": stock.warehouse,
                            "quantity_on_hand": stock.quantity_on_hand,
                            "reorder_point": item.reorder_point,
                            "reorder_quantity": item.reorder_quantity or 0,
                            "shortfall": item.reorder_point - stock.quantity_on_hand,
                        }
                    )

    return render_template("inventory/reports/low_stock.html", low_stock_items=low_stock_items)
