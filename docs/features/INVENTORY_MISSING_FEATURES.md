# Inventory Management — Remaining Gaps

**Status:** Updated to reflect current implementation. Previously listed "missing" items (stock transfers, adjustments, inventory reports, stock item history, PO edit/send/cancel/delete/receive, supplier code validation, API for transfers and reports) are **now implemented**. See [INVENTORY_IMPLEMENTATION_STATUS.md](INVENTORY_IMPLEMENTATION_STATUS.md) for what is done.

This document lists what is still missing or partial.

---

## 1. Menu and navigation

- Add **Transfers** link to inventory menu
- Add **Adjustments** link to inventory menu
- Add **Reports** link to inventory menu
- Update navigation active states for new routes

---

## 2. API endpoints (optional / partial)

- Optional: `read:inventory` / `write:inventory` scopes for closer alignment with web permissions
- Optional: `GET /api/v1/inventory/movements` (list movements with filters)
- Supplier and Purchase Order API completeness (verify against current API; some CRUD may exist)

---

## 3. Tests

- Supplier model and route tests (web)
- Purchase Order model and route tests (web)
- **Done:** API tests for inventory transfers and inventory reports (see INVENTORY_IMPLEMENTATION_STATUS.md)

---

## 4. Documentation

- User guide: `docs/features/INVENTORY_MANAGEMENT.md`
- API documentation: `docs/features/INVENTORY_API.md`
- Update main README with inventory features

---

## 5. Configuration and UI improvements

- Configuration settings not fully utilized (e.g. reservation expiry, low-stock alert toggle, approval workflow for adjustments)
- Warehouse stock **location** field: implemented in model but not exposed in forms/views
- Stock item view: supplier management section, quick actions (adjust, transfer)
- Purchase order view: print PO, email PO to supplier (future)
- Stock levels page: bulk operations, export CSV/Excel, advanced filtering

---

## 6. Integration gaps

- Project cost integration: link POs to project costs, project-specific inventory tracking
- ExtraGood integration: auto-create or link stock items from ExtraGoods

---

## Priority summary

- **High:** Menu links so users can discover Transfers, Adjustments, Reports
- **Medium:** Supplier and PO web tests; optional API endpoints; location field in UI
- **Low:** User guide and INVENTORY_API.md; advanced analytics; PO print/email
