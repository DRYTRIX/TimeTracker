# TimeTracker Frontend Guide

This document describes the main app frontend stack, component usage, and conventions. It does **not** cover the client portal or kiosk bases.

## Stack

- **Templates**: Jinja2 (Flask)
- **Styles**: Tailwind CSS (built from `app/static/src/input.css` → `app/static/dist/output.css`)
- **Design tokens**: CSS variables and Tailwind theme in `app/static/src/input.css` and `tailwind.config.js`
- **Scripts**: esbuild bundles (`scripts/build-js.mjs` → `app/static/dist/*.min.js`), referenced via `asset_url()`
- **Third-party libraries**: vendored into `app/static/vendor/` — never loaded from a CDN
- **No React/Vue**: The app remains server-rendered with Jinja; use existing macros and minimal JS for behavior.

## Building assets

```bash
npm install
npm run build:docker     # Tailwind + vendor + JS bundles (what the Dockerfile runs)

# or individually
npm run build:css:once   # Tailwind -> dist/output.css
npm run copy:vendor      # node_modules -> app/static/vendor/
npm run build:js         # esbuild -> dist/*.min.js + manifest.json

# watch during development
npm run build:css        # Tailwind, watch mode
npm run watch:js         # esbuild, watch mode
```

Both `app/static/dist/` and `app/static/vendor/` are build output and are gitignored.

### No external assets — ever

TimeTracker is self-hosted and privacy-focused, so **every** stylesheet, script, font and
icon must be served from the app's own origin. Loading anything from a CDN leaks each
user's IP address to a third party and breaks air-gapped deployments outright.

To add a library:

1. `npm install <package>` (pin the version).
2. Add its files to `ASSETS` in `scripts/copy-vendor.mjs`.
3. Reference it as `{{ url_for('static', filename='vendor/<lib>/<file>') }}`.

Files are copied **verbatim** — never re-minified. Re-minifying a package's own build
output risks correctness for bytes that nginx `gzip` recovers anyway.

**Check the package actually ships a browser build.** Some publish a UMD file that lists
its dependencies as webpack *externals* and `require()`s them at run time; loaded directly
in a browser those resolve to `undefined`. `@toast-ui/editor` is exactly this case — its
`dist/toastui-editor.js` throws `Cannot read properties of undefined (reading 'PluginKey')`
because the eight `prosemirror-*` packages are external. When that happens, add the package
to `VENDOR_BUNDLES` in `scripts/build-js.mjs` instead: esbuild bundles the ESM entry with
its real dependencies inlined and exposes the expected global via `globalName`.

A quick way to tell: open the file and look at the UMD factory. If the header `require()`s
other packages, it is not self-contained.

`tests/test_no_external_assets.py` fails the build if a CDN URL, remote `@import`, or
un-nonced inline `<script>` reappears, and the `frontend-assets` CI job enforces it.

### Stylesheet order matters

Font Awesome **must** be linked before `dist/output.css`. Its
`.fa-solid { display: var(--fa-display, inline-block) }` has the same specificity as
Tailwind's `.hidden { display: none }`, so whichever loads last wins, and Tailwind is not
configured with the `important` strategy. Loading Font Awesome last silently makes `hidden`
a no-op on every icon — which is how the theme switcher ended up showing its light, dark
and system icons simultaneously. `test_font_awesome_loads_before_tailwind` enforces this.

### Adding a script to a page

Scripts loaded on every page belong to a bundle group in `scripts/build-js.mjs`. Note that
groups exist to preserve execution order relative to the Jinja-rendered inline blocks in
`base.html`, and that several source files declare globals other files consume — so
**order within and between groups is load-bearing**. Groups also mirror the Jinja
conditionals around them (e.g. `core-ai` is emitted only when AI is enabled, `core-auth`
only for authenticated users); merging across a conditional changes who receives the code.

Reference a bundle with `{{ asset_url('core-d') }}`. Inline `<script>` blocks must carry
`nonce="{{ csp_nonce() }}"`.

## Base template structure

`base.html` is split into partials under `app/templates/partials/`:

| Partial | Contents |
|---------|----------|
| `_head.html` | Icons, stylesheets, early inline bootstraps (theme, i18n, date formatting) |
| `_sidebar.html` | Primary navigation, gated by `is_module_enabled()` |
| `_topbar.html` | Global search, theme picker, language switcher, user menu |
| `_bottom_nav.html` | Mobile bottom navigation |
| `_command_palette.html` | Ctrl+K palette markup |

> **Jinja blocks cannot live in a partial.** An `{% include %}` renders as a separate
> template, so a child template's `{% block title %}` or `{% block extra_css %}` override
> cannot reach into it — the defaults would silently win. All block declarations stay in
> `base.html`.

References: [UI_IMPROVEMENTS_SUMMARY.md](implementation-notes/UI_IMPROVEMENTS_SUMMARY.md), [STYLING_CONSISTENCY_SUMMARY.md](implementation-notes/STYLING_CONSISTENCY_SUMMARY.md).

## Base template and blocks

- **Main app**: `app/templates/base.html` — provides `<html>`, head (meta, CSS, scripts), skip link, sidebar, header, `<main id="mainContentAnchor">`, footer, and mobile bottom nav.
- **Blocks**: `title`, `content`, `extra_css`, `scripts_extra`, `head_extra`, etc. Page templates extend `base.html` and override these blocks.

## Component usage

**Primary source**: `app/templates/components/ui.html` (and `app/templates/components/cards.html` where used). The legacy `_components.html` duplicate has been removed.

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
