# TimeTracker Frontend Guide

This document describes the main app frontend stack, component usage, and conventions. It does **not** cover the client portal or kiosk bases.

## Stack

- **Templates**: Jinja2 (Flask)
- **Styles**: Tailwind CSS (built from `app/static/src/input.css` → `app/static/dist/output.css`)
- **Design tokens**: CSS variables and Tailwind theme in `app/static/src/input.css` and `tailwind.config.js`
- **No React/Vue**: The app remains server-rendered with Jinja; use existing macros and minimal JS for behavior.

References: [UI_IMPROVEMENTS_SUMMARY.md](implementation-notes/UI_IMPROVEMENTS_SUMMARY.md), [STYLING_CONSISTENCY_SUMMARY.md](implementation-notes/STYLING_CONSISTENCY_SUMMARY.md).

## Base template and blocks

- **Main app**: `app/templates/base.html` — provides `<html>`, head (meta, CSS, scripts), skip link, sidebar, header, `<main id="mainContentAnchor">`, footer, and mobile bottom nav.
- **Blocks**: `title`, `content`, `extra_css`, `scripts_extra`, `head_extra`, etc. Page templates extend `base.html` and override these blocks.

## Component usage

**Primary source**: `app/templates/components/ui.html` (and `app/templates/components/cards.html` where used). Prefer these over legacy `_components.html`.

### When to use which

| Need | Macro / component | Import from |
|------|-------------------|-------------|
| Page title + subtitle + optional breadcrumbs and actions | `page_header(icon_class, title_text, subtitle_text=None, actions_html=None, breadcrumbs=None)` | `components/ui.html` |
| Breadcrumbs only | `breadcrumb_nav(items)` | `components/ui.html` |
| Summary / stat block | `stat_card(title, value, icon_class, color, trend=None, subtitle=None)` | `components/ui.html` or `components/cards.html` |
| Empty list / no results | `empty_state(...)` or `empty_state_compact(...)` with `type='no-data'` or `type='no-results'` | `components/ui.html` |
| Buttons | Use classes `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-danger`, `.btn-ghost`, `.btn-sm`, `.btn-lg` from design system | `app/static/src/input.css` |
| Modals | `modal(id, title, content_html, footer_html=None, size)` | `components/ui.html` |
| Confirm (destructive) | `confirm_dialog(id, title, message, confirm_text, cancel_text, confirm_class)` | `components/ui.html` |
| Pagination | `pagination_nav(pagination, route_name, url_params=None, aria_label=None)` | `components/ui.html` |
| Forms | `form_group`, `form_select`, `form_textarea`, etc. | `components/ui.html` |

### Empty states

- Use **no-data** when the list is empty and no filters are applied (e.g. “No time entries yet”).
- Use **no-results** when filters are applied but nothing matches (e.g. “No time entries match your filters”).
- Prefer the macro over inline empty markup so messaging and CTAs stay consistent.

## Buttons and forms

- **Buttons**: Use design-system classes (`.btn`, `.btn-primary`, `.btn-secondary`, `.btn-danger`, `.btn-ghost`) so focus states and colors stay consistent. Avoid ad-hoc `bg-*` / `px-*` for primary actions.
- **Forms**: Use `form_group` and related form macros from `ui.html` so labels, `aria-required`, `aria-invalid`, and error blocks are consistent. Shared validation lives in `form-validation.js` / `form-validation.css`.

## Modals

- Use the **modal** or **confirm_dialog** macros from `components/ui.html` for new and refactored flows.
- Custom dialogs must provide:
  - `role="dialog"` and `aria-modal="true"`
  - `aria-labelledby` (and preferably `aria-describedby`) pointing to the title and description
  - Focus trap when open (keep focus inside the dialog until closed).

## Tables and pagination

- **List tables**: Prefer `data-table-enhanced` (see `data-tables-enhanced.js` / `.css`) for sortable headers and consistent ARIA where applicable.
- **Responsive**: Use `responsive-cards` and `data-label` on cells for small screens.
- **Pagination**: Use the `pagination_nav` macro when possible; otherwise wrap pagination in a `<nav aria-label="...">` (e.g. “Time entries pagination”) for accessibility.

## Accessibility

- **Landmarks**: Main content is in `<main id="mainContentAnchor">`; sidebar has `aria-label="{{ _('Main navigation') }}"`.
- **Focus**: Use `focus:ring-2 focus:ring-primary` (or design-system focus classes) on interactive elements; ensure adjust-time, filter toggles, and bulk actions have visible focus.
- **Modals**: Use the shared macros so dialogs have correct ARIA and (where implemented) focus management.

## Legacy components

- **`app/templates/_components.html`** is deprecated for new work. Use `components/ui.html` (and `components/cards.html`) instead. Existing templates that still import from `_components.html` should be migrated when touching those pages.
