# Frontend Quality Gates and Modernization Milestones

This document tracks frontend modernization phases and how to run quality checks (accessibility, performance, visual consistency) across the web app, desktop app, and mobile app.

## Phased Milestones

### Phase A — Critical reliability and accessibility (done)
- [x] Fix duplicate DOM IDs (header search vs list filters) and scoped selectors
- [x] Fix duplicate `openStartTimer` IDs on dashboard; use class-based bindings
- [x] Normalize timer actions (single "Stop & save" where backend has no pause)
- [x] Desktop renderer: bundle with esbuild for browser context; fix config path and `showError` collision
- [x] Web: accessible labels and safe-area/mobile bottom padding for fixed nav
- [x] Desktop: connection status and notifications use `aria-live` / `role="status"` / `role="alert"`

### Phase B — Script/module refactors and design-system consolidation
- [x] Extract base keyboard/sidebar init into `base-init.js`; single PWA registration in `pwa-enhancements.js`
- [x] Desktop: state and UI notifications in separate modules; bundle remains single entry
- [ ] Web: further split of `base.html` inline scripts into route- or feature-specific modules
- [ ] Unify styling: reduce mixed Bootstrap/Tailwind usage (e.g. `analytics/mobile_dashboard.html`)

### Phase C — Navigation/IA and deeper UX polish
- [x] Mobile: `IndexedStack` for tab state; finance/workforce providers and invalidation on refresh
- [ ] Align mobile IA with web/desktop (e.g. Finance vs Invoices/Expenses/Workforce)
- [ ] Consider `go_router` (or equivalent) on mobile for shell routes and deep links
- [ ] Consistent loading/empty/error and retry patterns across all platforms

## Running quality checks

### Accessibility (web)

1. **Manual**
   - Use browser DevTools (Lighthouse accessibility audit).
   - Test keyboard navigation (Tab, Enter, Escape) and focus visibility on modals and dropdowns.

2. **Automated (optional)**
   - With the app running (e.g. `make dev` and open `http://localhost:3000`):
     - **Pa11y**: `npx pa11y http://localhost:3000` (install: `npm install -g pa11y` or use `npx`).
     - **axe-core**: Use browser extension or `@axe-core/cli`: `npx @axe-core/cli http://localhost:3000`.
   - For CI, add a job that starts the app, runs one of the above, then stops the app.

3. **Make target**
   - `make frontend-a11y` — runs a quick check if the app URL is set (see Makefile).

### Performance

- **Web**: Lighthouse performance audit (DevTools or CLI).
- **Desktop**: Electron DevTools; watch bundle size (`desktop/src/renderer/js/bundle.js`).
- **Mobile**: Flutter DevTools performance and size reports.

### Visual / regression

- Rely on existing CI and manual QA for now.
- Optional: add screenshot or visual regression tests (e.g. Playwright, Percy) in a later phase.

## File reference

| Area | Key files |
|------|-----------|
| Web base layout | `app/templates/base.html`, `app/static/base-init.js`, `app/static/pwa-enhancements.js` |
| Web search/IDs | `app/templates/*/list.html` (unique filter search IDs), `app/static/enhanced-search.js` |
| Desktop renderer | `desktop/src/renderer/js/app.js`, `desktop/src/renderer/js/state.js`, `desktop/src/renderer/js/ui/notifications.js`, `desktop/src/renderer/js/bundle.js` |
| Mobile finance | `mobile/lib/presentation/screens/finance_workforce_screen.dart`, `mobile/lib/presentation/providers/finance_workforce_providers.dart` |
| Mobile home | `mobile/lib/presentation/screens/home_screen.dart` (IndexedStack for tabs) |
