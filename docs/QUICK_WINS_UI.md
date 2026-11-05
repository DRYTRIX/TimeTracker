# UI Quick Wins (October 2025)

This document summarizes the lightweight improvements applied to the new UI.

## What changed

- Added minimal design tokens, button classes, focus ring utility, table helpers, and chips in `app/static/form-bridge.css`.
- Added an accessible skip link and a main content anchor in `app/templates/base.html`.
- Enhanced `app/templates/tasks/list.html` with sticky header treatment (CSS-only), zebra rows, and numeric alignment for date/progress columns.
- Polished `app/templates/auth/login.html` with primary button styling and an inline user icon for the username field.
- Added smoke tests in `tests/test_ui_quick_wins.py` to ensure presence of these enhancements.

## How to use

- Buttons: use `btn btn-primary`, `btn btn-secondary`, or `btn btn-ghost`. Sizes: add `btn-sm` or `btn-lg`.
- Focus: add `focus-ring` to any interactive element that needs a consistent visible focus.
- Tables: add `table table-zebra` to tables; use `table-compact` for denser rows and `table-number` on numeric cells/headers.
- Chips: use `chip` plus variant like `chip-neutral`, `chip-success`, `chip-warning`, `chip-danger`.

## Notes

- The sticky header effect relies on `position: sticky` applied to the `<th>` elements via `.table` class. Ensure the table is inside a scrolling container (already true for the list view wrapper).
- Token values are minimal fallbacks; prefer Tailwind theme tokens when available. These helpers are safe to remove once the templates are fully converted to Tailwind component primitives.
