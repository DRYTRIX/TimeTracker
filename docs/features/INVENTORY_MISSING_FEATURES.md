# Inventory Management — Remaining Gaps

**Status:** Updated for current implementation. Core inventory flows (items, warehouses, stock levels, transfers, adjustments, reports, suppliers, purchase orders including PDF/email, CSV stock export) are implemented. Navigation for Transfers / Adjustments / Reports is done.

This document lists what is still missing or partial.

---

## 1. API endpoints (optional / partial)

- Optional: tighter least-privilege usage of `read:inventory` / `write:inventory` across all clients
- Optional: `GET /api/v1/inventory/movements` (list movements with filters)
- Supplier and Purchase Order API completeness (verify remaining write paths against web parity)

---

## 2. Tests

- Purchase Order model and route tests (web) beyond basic smoke coverage
- Broader end-to-end receive / transfer / adjustment coverage

---

## 3. Documentation

- User guide polish: `docs/features/INVENTORY_MANAGEMENT.md`
- API documentation: `docs/features/INVENTORY_API.md`
- Keep main README inventory feature list in sync

---

## 4. Configuration and UI improvements

- Configuration settings not fully utilized (e.g. reservation expiry, low-stock alert toggle, approval workflow for adjustments)
- Stock item view: richer supplier management section / quick actions
- Stock levels page: bulk operations and advanced filtering beyond current filters + CSV export

---

## 5. Integration gaps

- **Project cost from PO receive:** `PurchaseOrder` has no `project_id` column today, so receiving a PO cannot create/link a `ProjectCost`. Add `project_id` (migration) before wiring receive → ProjectCost.
- ExtraGood integration: auto-create or link stock items from ExtraGoods

---

## Priority summary

- **Medium:** PO ↔ project cost once `project_id` exists; optional inventory API completeness
- **Low:** Advanced analytics, reservation/approval config, ExtraGood linkage
