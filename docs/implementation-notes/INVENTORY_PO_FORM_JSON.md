# Inventory: Purchase Order Form JSON Data

## Overview

The purchase order create/edit form (`inventory/purchase_orders/form.html`) embeds `stock_items` and `warehouses` into a `<script>` block so the front-end can build dropdowns and add rows. Jinja’s `tojson` filter is used to serialize these variables.

## Requirement

Variables passed to the template for use with `| tojson` must be **JSON-serializable**. SQLAlchemy model instances (e.g. `StockItem`, `Warehouse`) are not JSON-serializable by default and will raise `TypeError: Object of type StockItem is not JSON serializable` when rendering.

## Solution

In `app/routes/inventory.py`, the **new** and **edit** purchase order handlers convert query results to plain dicts before passing them to the template:

- **Stock items:** `[{"id", "sku", "name", "unit"} for s in stock_items_q]`
- **Warehouses:** `[{"id", "code", "name"} for w in warehouses_q]`

The template’s JavaScript only needs these fields, so the route builds minimal dicts and passes them as `stock_items` and `warehouses`. No template changes are required.

## For Other Forms

Any inventory (or other) form that embeds server data in a script with `| tojson` should receive lists of dicts (or other JSON-serializable types), not ORM objects. Convert in the route before calling `render_template`.
