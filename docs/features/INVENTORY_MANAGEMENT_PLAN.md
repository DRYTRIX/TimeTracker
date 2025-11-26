# Inventory Management System - Implementation Plan

## Overview

This document outlines the complete implementation plan for adding a comprehensive Inventory Management System to TimeTracker. The system will manage warehouses, stock items, and integrate seamlessly with quotes, invoices, and projects.

## 1. Core Database Models

### 1.1 Warehouse Model (`app/models/warehouse.py`)

**Purpose**: Store warehouse/location information

**Fields**:
- `id` (Integer, Primary Key)
- `name` (String(200), Required) - Warehouse name
- `code` (String(50), Unique, Indexed) - Warehouse code (e.g., "WH-001")
- `address` (Text, Optional) - Physical address
- `contact_person` (String(200), Optional) - Warehouse manager/contact
- `contact_email` (String(200), Optional)
- `contact_phone` (String(50), Optional)
- `is_active` (Boolean, Default: True) - Whether warehouse is active
- `notes` (Text, Optional) - Internal notes
- `created_at` (DateTime)
- `updated_at` (DateTime)
- `created_by` (Integer, ForeignKey -> users.id)

**Relationships**:
- `stock_items` - One-to-many with StockItem (stock levels per warehouse)
- `stock_movements` - One-to-many with StockMovement (transfers to/from this warehouse)

---

### 1.2 StockItem Model (`app/models/stock_item.py`)

**Purpose**: Define master product/item catalog

**Fields**:
- `id` (Integer, Primary Key)
- `sku` (String(100), Unique, Indexed) - Stock Keeping Unit
- `name` (String(200), Required) - Product name
- `description` (Text, Optional) - Detailed description
- `category` (String(100), Optional) - Product category
- `unit` (String(20), Default: "pcs") - Unit of measure (pcs, kg, m, L, etc.)
- `default_cost` (Numeric(10, 2), Optional) - Default purchase cost
- `default_price` (Numeric(10, 2), Optional) - Default selling price
- `currency_code` (String(3), Default: 'EUR')
- `barcode` (String(100), Optional, Indexed) - Barcode/UPC
- `is_active` (Boolean, Default: True)
- `is_trackable` (Boolean, Default: True) - Whether to track inventory levels
- `reorder_point` (Numeric(10, 2), Optional) - Alert when stock falls below this
- `reorder_quantity` (Numeric(10, 2), Optional) - Suggested reorder amount
- `supplier` (String(200), Optional) - Supplier information
- `supplier_sku` (String(100), Optional) - Supplier's product code
- `image_url` (String(500), Optional) - Product image
- `notes` (Text, Optional)
- `created_at` (DateTime)
- `updated_at` (DateTime)
- `created_by` (Integer, ForeignKey -> users.id)

**Relationships**:
- `warehouse_stock` - One-to-many with WarehouseStock (stock levels per warehouse)
- `quote_items` - Many-to-many with QuoteItem via stock_item_id
- `invoice_items` - Many-to-many with InvoiceItem via stock_item_id
- `project_items` - Many-to-many with Project (items allocated to projects)
- `stock_movements` - One-to-many with StockMovement

**Computed Properties**:
- `total_quantity_on_hand` - Sum of all warehouse stock levels
- `is_low_stock` - Boolean if any warehouse is below reorder point

---

### 1.3 WarehouseStock Model (`app/models/warehouse_stock.py`)

**Purpose**: Track stock levels per warehouse

**Fields**:
- `id` (Integer, Primary Key)
- `warehouse_id` (Integer, ForeignKey -> warehouses.id, Required, Indexed)
- `stock_item_id` (Integer, ForeignKey -> stock_items.id, Required, Indexed)
- `quantity_on_hand` (Numeric(10, 2), Default: 0) - Current stock level
- `quantity_reserved` (Numeric(10, 2), Default: 0) - Reserved for quotes/invoices
- `quantity_available` (Computed) - `quantity_on_hand - quantity_reserved`
- `location` (String(100), Optional) - Bin/shelf location within warehouse
- `last_counted_at` (DateTime, Optional) - Last physical count date
- `last_counted_by` (Integer, ForeignKey -> users.id, Optional)
- `updated_at` (DateTime)
- `created_at` (DateTime)

**Unique Constraint**: `(warehouse_id, stock_item_id)` - One stock record per item per warehouse

**Relationships**:
- `warehouse` - Many-to-one with Warehouse
- `stock_item` - Many-to-one with StockItem

---

### 1.4 StockMovement Model (`app/models/stock_movement.py`)

**Purpose**: Track all inventory movements (adjustments, transfers, sales, purchases)

**Fields**:
- `id` (Integer, Primary Key)
- `movement_type` (String(20), Required) - 'adjustment', 'transfer', 'sale', 'purchase', 'return', 'waste'
- `stock_item_id` (Integer, ForeignKey -> stock_items.id, Required, Indexed)
- `warehouse_id` (Integer, ForeignKey -> warehouses.id, Required, Indexed) - Source/target warehouse
- `quantity` (Numeric(10, 2), Required) - Positive for additions, negative for removals
- `reference_type` (String(50), Optional) - 'invoice', 'quote', 'project', 'manual', 'purchase_order'
- `reference_id` (Integer, Optional) - ID of related invoice/quote/project
- `unit_cost` (Numeric(10, 2), Optional) - Cost at time of movement (for costing)
- `reason` (String(500), Optional) - Reason for movement
- `notes` (Text, Optional)
- `moved_by` (Integer, ForeignKey -> users.id, Required)
- `moved_at` (DateTime, Default: now)

**Relationships**:
- `stock_item` - Many-to-one with StockItem
- `warehouse` - Many-to-one with Warehouse
- `moved_by_user` - Many-to-one with User

**Indexes**:
- `(reference_type, reference_id)` - For quick lookup of related movements
- `(stock_item_id, moved_at)` - For stock history

---

### 1.5 StockReservation Model (`app/models/stock_reservation.py`)

**Purpose**: Reserve stock for quotes/invoices before actual sale

**Fields**:
- `id` (Integer, Primary Key)
- `stock_item_id` (Integer, ForeignKey -> stock_items.id, Required, Indexed)
- `warehouse_id` (Integer, ForeignKey -> warehouses.id, Required, Indexed)
- `quantity` (Numeric(10, 2), Required)
- `reservation_type` (String(20), Required) - 'quote', 'invoice', 'project'
- `reservation_id` (Integer, Required) - ID of quote/invoice/project
- `status` (String(20), Default: 'reserved') - 'reserved', 'fulfilled', 'cancelled', 'expired'
- `expires_at` (DateTime, Optional) - For quote reservations
- `reserved_by` (Integer, ForeignKey -> users.id, Required)
- `reserved_at` (DateTime, Default: now)
- `fulfilled_at` (DateTime, Optional)
- `cancelled_at` (DateTime, Optional)
- `notes` (Text, Optional)

**Unique Constraint**: Ensure no double-reservations (per item/warehouse/reservation)

**Relationships**:
- `stock_item` - Many-to-one with StockItem
- `warehouse` - Many-to-one with Warehouse

---

## 2. Integration with Existing Models

### 2.1 QuoteItem Enhancements

**Changes to `app/models/quote.py`**:
- Add `stock_item_id` (Integer, ForeignKey -> stock_items.id, Optional, Indexed)
- Add `warehouse_id` (Integer, ForeignKey -> warehouses.id, Optional) - Preferred warehouse
- Add `is_stock_item` (Boolean, Default: False) - Flag to indicate if linked to inventory

**Behavior**:
- When quote item is linked to stock item, show current available quantity
- Allow reserving stock when quote is sent (optional)
- Auto-reserve on quote acceptance (if enabled)
- Release reservation if quote is rejected/expired

---

### 2.2 InvoiceItem Enhancements

**Changes to `app/models/invoice.py`** (InvoiceItem class):
- Add `stock_item_id` (Integer, ForeignKey -> stock_items.id, Optional, Indexed)
- Add `warehouse_id` (Integer, ForeignKey -> warehouses.id, Optional)
- Add `is_stock_item` (Boolean, Default: False)

**Behavior**:
- When invoice item is linked to stock item and invoice is created:
  - Reserve stock if not already reserved
  - Optionally reduce stock when invoice status changes to 'sent' or 'paid'
- Track cost at time of sale for profit analysis
- Create StockMovement record when stock is allocated

---

### 2.3 Project Integration

**New Model: ProjectStockAllocation (`app/models/project_stock_allocation.py`)**:
- `id` (Integer, Primary Key)
- `project_id` (Integer, ForeignKey -> projects.id, Required, Indexed)
- `stock_item_id` (Integer, ForeignKey -> stock_items.id, Required, Indexed)
- `warehouse_id` (Integer, ForeignKey -> warehouses.id, Required, Indexed)
- `quantity_allocated` (Numeric(10, 2), Required)
- `quantity_used` (Numeric(10, 2), Default: 0)
- `allocated_by` (Integer, ForeignKey -> users.id, Required)
- `allocated_at` (DateTime, Default: now)
- `notes` (Text, Optional)

**Purpose**: Track which items are allocated to which projects (for project-based inventory)

---

### 2.4 ExtraGood Enhancement

**Changes to `app/models/extra_good.py`**:
- Add `stock_item_id` (Integer, ForeignKey -> stock_items.id, Optional, Indexed)
- Link ExtraGood to StockItem when applicable

---

## 3. Menu Structure

### 3.1 New Menu Group: "Inventory"

Add to `app/templates/base.html` after "Finance & Expenses" section:

```html
<li class="mt-2">
    <button onclick="toggleDropdown('inventoryDropdown')" data-dropdown="inventoryDropdown" 
            class="w-full flex items-center p-2 rounded-lg {% if inventory_open %}bg-background-light dark:bg-background-dark text-primary font-semibold{% else %}text-text-light dark:text-text-dark hover:bg-background-light dark:hover:bg-background-dark{% endif %}">
        <i class="fas fa-boxes w-6 text-center"></i>
        <span class="ml-3 sidebar-label">{{ _('Inventory') }}</span>
        <i class="fas fa-chevron-down ml-auto sidebar-label"></i>
    </button>
    <ul id="inventoryDropdown" class="{% if not inventory_open %}hidden {% endif %}mt-2 space-y-2 ml-6">
        <li>
            <a class="block px-2 py-1 rounded {% if nav_active_stock_items %}text-primary font-semibold bg-background-light dark:bg-background-dark{% else %}text-text-light dark:text-text-dark hover:bg-background-light dark:hover:bg-background-dark{% endif %}" 
               href="{{ url_for('inventory.list_stock_items') }}">
                <i class="fas fa-cubes w-4 mr-2"></i>{{ _('Stock Items') }}
            </a>
        </li>
        <li>
            <a class="block px-2 py-1 rounded {% if nav_active_warehouses %}text-primary font-semibold bg-background-light dark:bg-background-dark{% else %}text-text-light dark:text-text-dark hover:bg-background-light dark:hover:bg-background-dark{% endif %}" 
               href="{{ url_for('inventory.list_warehouses') }}">
                <i class="fas fa-warehouse w-4 mr-2"></i>{{ _('Warehouses') }}
            </a>
        </li>
        <li>
            <a class="block px-2 py-1 rounded {% if nav_active_stock_levels %}text-primary font-semibold bg-background-light dark:bg-background-dark{% else %}text-text-light dark:text-text-dark hover:bg-background-light dark:hover:bg-background-dark{% endif %}" 
               href="{{ url_for('inventory.stock_levels') }}">
                <i class="fas fa-list-ul w-4 mr-2"></i>{{ _('Stock Levels') }}
            </a>
        </li>
        <li>
            <a class="block px-2 py-1 rounded {% if nav_active_movements %}text-primary font-semibold bg-background-light dark:bg-background-dark{% else %}text-text-light dark:text-text-dark hover:bg-background-light dark:hover:bg-background-dark{% endif %}" 
               href="{{ url_for('inventory.list_movements') }}">
                <i class="fas fa-exchange-alt w-4 mr-2"></i>{{ _('Stock Movements') }}
            </a>
        </li>
        <li>
            <a class="block px-2 py-1 rounded {% if nav_active_transfers %}text-primary font-semibold bg-background-light dark:bg-background-dark{% else %}text-text-light dark:text-text-dark hover:bg-background-light dark:hover:bg-background-dark{% endif %}" 
               href="{{ url_for('inventory.list_transfers') }}">
                <i class="fas fa-truck w-4 mr-2"></i>{{ _('Transfers') }}
            </a>
        </li>
        <li>
            <a class="block px-2 py-1 rounded {% if nav_active_reservations %}text-primary font-semibold bg-background-light dark:bg-background-dark{% else %}text-text-light dark:text-text-dark hover:bg-background-light dark:hover:bg-background-dark{% endif %}" 
               href="{{ url_for('inventory.list_reservations') }}">
                <i class="fas fa-bookmark w-4 mr-2"></i>{{ _('Reservations') }}
            </a>
        </li>
        <li>
            <a class="block px-2 py-1 rounded {% if nav_active_adjustments %}text-primary font-semibold bg-background-light dark:bg-background-dark{% else %}text-text-light dark:text-text-dark hover:bg-background-light dark:hover:bg-background-dark{% endif %}" 
               href="{{ url_for('inventory.list_adjustments') }}">
                <i class="fas fa-edit w-4 mr-2"></i>{{ _('Stock Adjustments') }}
            </a>
        </li>
        <li>
            <a class="block px-2 py-1 rounded {% if nav_active_reports %}text-primary font-semibold bg-background-light dark:bg-background-dark{% else %}text-text-light dark:text-text-dark hover:bg-background-light dark:hover:bg-background-dark{% endif %}" 
               href="{{ url_for('inventory.reports') }}">
                <i class="fas fa-chart-pie w-4 mr-2"></i>{{ _('Inventory Reports') }}
            </a>
        </li>
        <li>
            <a class="block px-2 py-1 rounded {% if nav_active_low_stock %}text-primary font-semibold bg-background-light dark:bg-background-dark{% else %}text-text-light dark:text-text-dark hover:bg-background-light dark:hover:bg-background-dark{% endif %}" 
               href="{{ url_for('inventory.low_stock_alerts') }}">
                <i class="fas fa-exclamation-triangle w-4 mr-2"></i>{{ _('Low Stock Alerts') }}
            </a>
        </li>
    </ul>
</li>
```

**Menu Variable**: 
```python
{% set inventory_open = ep.startswith('inventory.') %}
```

---

## 4. Routes and Endpoints

### 4.1 Main Routes File (`app/routes/inventory.py`)

**Stock Items**:
- `GET /inventory/items` - List all stock items
- `GET /inventory/items/new` - Create new stock item form
- `POST /inventory/items` - Create stock item
- `GET /inventory/items/<id>` - View stock item details
- `GET /inventory/items/<id>/edit` - Edit stock item form
- `POST /inventory/items/<id>` - Update stock item
- `POST /inventory/items/<id>/delete` - Delete stock item
- `GET /inventory/items/<id>/history` - Stock movement history for item

**Warehouses**:
- `GET /inventory/warehouses` - List all warehouses
- `GET /inventory/warehouses/new` - Create new warehouse form
- `POST /inventory/warehouses` - Create warehouse
- `GET /inventory/warehouses/<id>` - View warehouse details
- `GET /inventory/warehouses/<id>/edit` - Edit warehouse form
- `POST /inventory/warehouses/<id>` - Update warehouse
- `POST /inventory/warehouses/<id>/delete` - Delete warehouse (if no stock)

**Stock Levels**:
- `GET /inventory/stock-levels` - View stock levels (multi-warehouse view)
- `GET /inventory/stock-levels/warehouse/<warehouse_id>` - Stock levels for specific warehouse
- `GET /inventory/stock-levels/item/<item_id>` - Stock levels for specific item across warehouses

**Stock Movements**:
- `GET /inventory/movements` - List all stock movements (with filters)
- `GET /inventory/movements/new` - Create manual movement/adjustment
- `POST /inventory/movements` - Record movement

**Stock Transfers**:
- `GET /inventory/transfers` - List transfers between warehouses
- `GET /inventory/transfers/new` - Create new transfer
- `POST /inventory/transfers` - Create transfer (creates two movements)

**Stock Adjustments**:
- `GET /inventory/adjustments` - List adjustments
- `GET /inventory/adjustments/new` - Create adjustment
- `POST /inventory/adjustments` - Record adjustment

**Reservations**:
- `GET /inventory/reservations` - List all reservations
- `POST /inventory/reservations/<id>/fulfill` - Fulfill reservation
- `POST /inventory/reservations/<id>/cancel` - Cancel reservation

**Reports**:
- `GET /inventory/reports` - Inventory reports dashboard
- `GET /inventory/reports/valuation` - Stock valuation report
- `GET /inventory/reports/movement-history` - Movement history report
- `GET /inventory/reports/turnover` - Inventory turnover analysis
- `GET /inventory/reports/low-stock` - Low stock alerts

**API Endpoints** (also add to `app/routes/api_v1.py`):
- `GET /api/v1/inventory/items` - List stock items (JSON)
- `GET /api/v1/inventory/items/<id>` - Get stock item details
- `GET /api/v1/inventory/items/<id>/availability` - Check availability across warehouses
- `GET /api/v1/inventory/warehouses` - List warehouses
- `GET /api/v1/inventory/stock-levels` - Get stock levels (filterable)
- `POST /api/v1/inventory/movements` - Create movement via API

---

## 5. Key Features

### 5.1 Standard Inventory Management Features

1. **Multi-Warehouse Support**
   - Manage multiple warehouse locations
   - Track stock levels per warehouse
   - Transfer stock between warehouses

2. **Stock Item Master Data**
   - SKU/barcode management
   - Product categories
   - Unit of measure support
   - Default cost/price tracking
   - Supplier information
   - Product images

3. **Real-Time Stock Tracking**
   - Current stock levels per warehouse
   - Available quantity (on-hand minus reserved)
   - Stock history and movement audit trail

4. **Stock Reservations**
   - Reserve stock for quotes
   - Reserve stock for invoices
   - Reserve stock for projects
   - Automatic expiration for quote reservations
   - Fulfillment tracking

5. **Stock Movements**
   - Record all inventory changes
   - Movement types: adjustment, transfer, sale, purchase, return, waste
   - Link movements to invoices/quotes/projects
   - Cost tracking at movement time

6. **Low Stock Alerts**
   - Configurable reorder points per item
   - Automatic alerts when stock falls below threshold
   - Dashboard widget showing low stock items
   - Email notifications (optional)

7. **Stock Adjustments**
   - Manual stock adjustments
   - Physical count corrections
   - Reason tracking for all adjustments
   - Approval workflow (optional, via permissions)

8. **Transfers Between Warehouses**
   - Create transfer requests
   - Track transfer status (pending, in-transit, completed)
   - Update stock levels automatically

9. **Inventory Reports**
   - Stock valuation report (current stock value)
   - Movement history report
   - Inventory turnover analysis
   - Low stock report
   - Stock level by warehouse
   - Stock level by category
   - ABC analysis (optional future feature)

10. **Barcode Scanning Support**
    - Barcode field per stock item
    - Search by barcode
    - API support for barcode scanners

### 5.2 Integration Features

1. **Quote Integration**
   - Add stock items to quotes
   - Show available quantity when adding items
   - Reserve stock when quote is sent (optional setting)
   - Auto-reserve on quote acceptance
   - Release reservation on rejection/expiration

2. **Invoice Integration**
   - Add stock items to invoices
   - Automatic stock reservation on invoice creation
   - Reduce stock when invoice is marked as sent/paid (configurable)
   - Track cost vs. price for profit analysis
   - Create StockMovement records automatically

3. **Project Integration**
   - Allocate stock items to projects
   - Track quantity used vs. allocated
   - Link project stock to invoices/quotes
   - Project stock consumption reports

4. **ExtraGood Integration**
   - Link ExtraGood records to StockItems
   - Convert ExtraGood to StockItem (migration path)

---

## 6. Permissions

Add to `app/utils/permissions_seed.py`:

```python
# Inventory Management Permissions
inventory_permissions = [
    Permission('view_inventory', 'View inventory items and stock levels', 'inventory'),
    Permission('manage_stock_items', 'Create, edit, and delete stock items', 'inventory'),
    Permission('manage_warehouses', 'Create, edit, and delete warehouses', 'inventory'),
    Permission('view_stock_levels', 'View current stock levels', 'inventory'),
    Permission('manage_stock_movements', 'Record stock movements and adjustments', 'inventory'),
    Permission('transfer_stock', 'Transfer stock between warehouses', 'inventory'),
    Permission('view_stock_history', 'View stock movement history', 'inventory'),
    Permission('manage_stock_reservations', 'Create and manage stock reservations', 'inventory'),
    Permission('view_inventory_reports', 'View inventory reports', 'inventory'),
    Permission('approve_stock_adjustments', 'Approve stock adjustments (if approval workflow enabled)', 'inventory'),
]
```

**Default Role Assignments**:
- Super Admin: All permissions
- Admin: All permissions
- Manager: view_inventory, view_stock_levels, manage_stock_movements, transfer_stock, view_stock_history, manage_stock_reservations, view_inventory_reports
- User: view_inventory, view_stock_levels
- Viewer: view_inventory (read-only)

---

## 7. Database Migrations

### 7.1 Initial Migration Structure

**Migration File**: `migrations/versions/059_add_inventory_management.py`

**Tables to Create**:
1. `warehouses`
2. `stock_items`
3. `warehouse_stock`
4. `stock_movements`
5. `stock_reservations`
6. `project_stock_allocations`

**Alterations to Existing Tables**:
1. `quote_items` - Add `stock_item_id`, `warehouse_id`, `is_stock_item`
2. `invoice_items` - Add `stock_item_id`, `warehouse_id`, `is_stock_item`
3. `extra_goods` - Add `stock_item_id`

**Indexes**:
- Index on `stock_items.sku`
- Index on `stock_items.barcode`
- Index on `warehouse_stock(warehouse_id, stock_item_id)` (unique)
- Index on `stock_movements(reference_type, reference_id)`
- Index on `stock_movements(stock_item_id, moved_at)`
- Index on `stock_reservations(reservation_type, reservation_id)`

**Foreign Keys**:
- All appropriate foreign key constraints
- Cascade deletes where appropriate
- Set null for optional references

---

## 8. UI/UX Considerations

### 8.1 Stock Items List View
- Table with columns: SKU, Name, Category, Total Qty, Low Stock, Actions
- Filters: Category, Active/Inactive, Low Stock
- Search: By SKU, Name, Barcode
- Quick actions: View, Edit, Adjust Stock, View History

### 8.2 Stock Item Detail View
- Item information
- Stock levels per warehouse (table)
- Recent movements (last 10)
- Related quotes/invoices/projects
- Stock level graph (optional)

### 8.3 Stock Levels Dashboard
- Multi-warehouse view
- Filter by warehouse, category, low stock
- Quick adjust buttons
- Color coding for low stock

### 8.4 Add Stock Item to Quote/Invoice
- Product selector with search/filter
- Show available quantity per warehouse
- Select warehouse for reservation
- Quantity validation (ensure available)

### 8.5 Stock Movement Form
- Movement type selector
- Stock item selector (with search)
- Warehouse selector
- Quantity (positive/negative)
- Reference (link to invoice/quote/project)
- Reason field

### 8.6 Warehouse Management
- List view with active/inactive toggle
- Detail view showing stock levels
- Transfer in/out history

---

## 9. Implementation Phases

### Phase 1: Core Models and Database (Week 1)
- Create all database models
- Create Alembic migration
- Update model __init__.py
- Basic model tests

### Phase 2: Basic CRUD Operations (Week 2)
- Stock Items CRUD routes and templates
- Warehouses CRUD routes and templates
- Basic stock level views
- Integration tests

### Phase 3: Stock Movements and Tracking (Week 3)
- Stock movement recording
- Stock level updates on movements
- Movement history views
- Transfer functionality

### Phase 4: Integration with Quotes/Invoices (Week 4)
- Add stock_item_id to QuoteItem and InvoiceItem
- Stock item selector in quote/invoice forms
- Stock reservation logic
- Stock reduction on invoice creation/update
- Integration tests

### Phase 5: Advanced Features (Week 5)
- Low stock alerts
- Inventory reports
- Project stock allocation
- Barcode support

### Phase 6: Permissions and Polish (Week 6)
- Add permissions
- Update menu
- UI/UX improvements
- Documentation
- Final testing

---

## 10. Testing Requirements

### 10.1 Model Tests (`tests/test_models/test_inventory_models.py`)
- Warehouse model creation and validation
- StockItem model creation and validation
- WarehouseStock stock level calculations
- StockMovement creation and stock updates
- StockReservation lifecycle (reserve, fulfill, cancel)

### 10.2 Route Tests (`tests/test_routes/test_inventory_routes.py`)
- Stock items CRUD operations
- Warehouses CRUD operations
- Stock movement recording
- Stock level queries
- Permission checks

### 10.3 Integration Tests (`tests/test_integration/test_inventory_integration.py`)
- Quote with stock items (reservation)
- Invoice with stock items (stock reduction)
- Project stock allocation
- Stock transfer between warehouses
- Low stock alert triggering

### 10.4 Smoke Tests
- Create stock item
- Add stock item to quote
- Create invoice with stock item
- Record stock adjustment
- View stock levels

---

## 11. Configuration Settings

Add to Settings model or environment:
- `INVENTORY_AUTO_RESERVE_ON_QUOTE_SENT` (Boolean, Default: False)
- `INVENTORY_REDUCE_ON_INVOICE_SENT` (Boolean, Default: True)
- `INVENTORY_REDUCE_ON_INVOICE_PAID` (Boolean, Default: False)
- `INVENTORY_QUOTE_RESERVATION_EXPIRY_DAYS` (Integer, Default: 30)
- `INVENTORY_LOW_STOCK_ALERT_ENABLED` (Boolean, Default: True)
- `INVENTORY_REQUIRE_APPROVAL_FOR_ADJUSTMENTS` (Boolean, Default: False)

---

## 12. Future Enhancements (Post-MVP)

1. **Advanced Costing Methods**
   - FIFO (First In, First Out)
   - LIFO (Last In, First Out)
   - Average Cost
   - Specific Identification

2. **Purchase Orders**
   - Create purchase orders
   - Receive goods (update stock)
   - Supplier management

3. **Stocktaking/Physical Counts**
   - Schedule physical counts
   - Count sheets
   - Variance reports

4. **Serial Number Tracking**
   - Track individual items by serial number
   - Lot/batch tracking

5. **ABC Analysis**
   - Classify items by value
   - Focus management on high-value items

6. **Demand Forecasting**
   - Analyze historical sales
   - Predict future demand
   - Auto-generate reorder suggestions

7. **Multi-Currency Support**
   - Track costs in different currencies
   - Currency conversion for valuations

8. **Barcode Scanner Integration**
   - Mobile barcode scanning
   - Real-time stock updates via scanner

9. **Inventory Templates**
   - Pre-defined stock item templates
   - Quick add from templates

10. **Email Notifications**
    - Low stock alerts via email
    - Daily/weekly inventory summaries

---

## 13. Documentation

Create the following documentation:
1. `docs/features/INVENTORY_MANAGEMENT.md` - User guide
2. `docs/features/INVENTORY_API.md` - API documentation
3. Update main README with inventory features
4. Video tutorial (optional)

---

## 14. Migration Strategy

### 14.1 Existing Data
- ExtraGood records with SKUs can be migrated to StockItems
- Create default warehouse "Main Warehouse" if none exists
- Set initial stock levels (if known)

### 14.2 Backward Compatibility
- Quotes/Invoices without stock_item_id continue to work
- ExtraGood remains functional
- Gradual migration path for existing data

---

## 15. Success Criteria

1. ✅ Can create and manage warehouses
2. ✅ Can create and manage stock items
3. ✅ Can track stock levels per warehouse
4. ✅ Can add stock items to quotes and see availability
5. ✅ Can add stock items to invoices and reduce stock
6. ✅ Stock reservations work correctly
7. ✅ Stock movements are recorded and auditable
8. ✅ Low stock alerts function properly
9. ✅ Inventory reports generate correctly
10. ✅ All tests pass
11. ✅ Permissions work correctly
12. ✅ Integration with quotes/invoices/projects is seamless

---

## Conclusion

This comprehensive inventory management system will provide TimeTracker with professional-grade inventory tracking capabilities while maintaining seamless integration with existing quote, invoice, and project workflows. The phased implementation approach ensures steady progress while maintaining code quality and test coverage.

