# PDF layout designer (invoice & quote)

## Modules (static)

Pure helpers live under `app/static/js/pdf_editor/`:

- `helpers.mjs` — union selection bounds, smart-guide snap math, distribute horizontal/vertical
- `align.mjs`, `guides.mjs`, `selection.mjs`, `core.mjs` — thin re-exports for discoverability

The Konva editor itself stays in Jinja templates (`pdf_layout.html`, `quote_pdf_layout.html`) because it embeds `{% raw %}` / `{{ … }}` for invoice/quote variables. Templates load helpers via `import()` (see `async function initializePDFEditor`).

## Issue #619 features

- **Multi-select:** Shift/Ctrl/Cmd-click toggles; drag a marquee on the page background; transformer supports multiple nodes; arrow keys move all selected (snap-to-grid aware when enabled).
- **Text alignment:** Properties panel segmented controls for horizontal (left/center/right/justify) and vertical (top/middle/bottom) alignment.
- **Align toolbar:** With one element selected, aligns to the page; with two or more, aligns to the selection bounding box. **Distribute** buttons require three or more elements.
- **Ctrl/Cmd+G** groups selection into a `user-group`; **Ctrl/Cmd+Shift+G** ungroups.
- **Layers panel:** eye (hidden in export), lock (non-selectable), row click to select.
- **Smart guides** and **rulers** toggles in the top toolbar.

## Manual QA checklist

1. Invoice designer `/admin/pdf-layout`: multi-select, move, copy/paste multiple, distribute, group/ungroup, text align + vertical align, save, reload, preview PDF.
2. Quote designer `/admin/quote-pdf-layout`: same smoke test.
3. Hidden element: toggle eye off → save → preview: element absent from PDF.
4. Locked element: cannot select on canvas; unlock from layers panel.
5. Justify + long paragraph: preview renders without crashing.

## `?editor=v2`

Historically discussed as a feature flag; the editor always loads the modular helpers path—no separate legacy bundle is kept in-tree.
