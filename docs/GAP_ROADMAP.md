# Gap Remediation Roadmap

Tracking document for the whole-app gap analysis (implementation, UI/UX, clients, missing features). Archive stale competitive/status docs in favor of this file.

## Status

| Phase | Focus | Status |
|-------|--------|--------|
| 0 | Stabilize: idle feature, dead routes, Alembic single-head CI | Done |
| 1 | Security & backend hygiene | Done (first pass) |
| 2 | Web UI/UX consistency | Done (first pass) |
| 3 | Client parity | Done (first pass) |
| 4 | High-return missing features | Done (first slices) |
| 5 | Strategic / enterprise | Done (foundations / design + stubs) |

## Phase notes

### Phase 0
- Idle unanswered action shipped (migration 195, commit on develop).
- Deleted unregistered dead modules: `timer_refactored.py`, `invoices_refactored.py`, `projects_refactored_example.py`, `offers.py`.
- CI: single Alembic head check in `.github/workflows/migration-check.yml`.

### Phase 1

**Silent `except` / `pass` (hot paths)** — Replace swallowed exceptions with structured logging while keeping the same control flow (still swallow where previously swallowed). Phase 1 scope:

- `app/routes/auth.py`
- `app/routes/admin.py` (high-risk + intentional cleanup at debug)
- `app/routes/expenses.py`
- `app/__init__.py` (optional imports / telemetry at debug)
- `app/utils/scheduled_tasks.py`

**Lint guard:** Ruff rule **S110** (try/except/pass) is enabled in `pyproject.toml` under `[tool.ruff.lint]` (`extend-select = ["S110"]`). Tests and scripts ignore S110 via `[tool.ruff.lint.per-file-ignores]`.

**Verify remaining silent handlers in Phase 1 files:**

```bash
rg -c 'except.*:\n\s+pass' -U \
  app/routes/auth.py app/routes/admin.py app/routes/expenses.py \
  app/__init__.py app/utils/scheduled_tasks.py
```

Expect **0** matches per file when Phase 1 logging work is complete.

See implementation commits and CHANGELOG Unreleased section for other Phase 1 items.

### Phase 2 (Web UI/UX consistency)

**Accessibility & dark mode (sample pass)**

- Icon-only controls: `aria-label` (+ `aria-hidden` on icons) on expense approvals, project/client list filters, project/client delete actions, expense category row actions, dashboard weekly-goal link.
- Dark mode: sample `dark:` fixes on `admin/dashboard.html`, `main/dashboard.html`, `user/settings.html` chevrons, `admin/api_tokens.html` copy (table already themed).

**Forms**

- Flatpickr: `user-date-input` on expense approval filters and quote `valid_until` (timer/invoice due dates were already wired).
- Unsaved changes: new `app/static/js/unsaved-changes.js` in `core-a1` bundle; `data-unsaved-guard` on invoice edit, quote edit, admin invoice/quote PDF layout forms; Konva editors dispatch `tt:unsaved-dirty` / `tt:unsaved-clean` on edit/save.

**Navigation / command palette**

- Expanded Ctrl+K destinations (projects, tasks, invoices, analytics, calendar, expenses, time entries, settings) via `data-*` URLs on `_command_palette.html`.
- Command titles wired to `window.i18n.commandPalette` in `_head.html`.
- Sidebar unchanged structurally; comment notes palette as alternate entry to primary routes.

**i18n quick wins**

- Wrapped hardcoded English on `expense_categories/list.html`, `deals/list.html`, `deals/pipeline.html`, and admin API tokens headers/docs blurb.

**Follow-ups**

- Rebuild JS assets (`node scripts/build-js.mjs`) so `core-a1` and `command-palette` hashes pick up new scripts.
- Broader template pass for remaining icon-only buttons and light-only Tailwind grays.
- Extract new `commandPalette.*` strings into `messages.po` for translators.

### Phase 3 (Client parity — offline, tests, i18n, versions & auth)

**Versions**

- Source of truth: `setup.py` (`5.17.1`); mirror `VERSION` at repo root.
- Clients aligned: `desktop/package.json`, `browser-extension/package.json` + `manifest.json`, `mobile/pubspec.yaml` (`5.17.1+1`).
- Desktop sidebar label via Vite `__APP_VERSION__` (`desktop/vite.config.mjs` reads `desktop/package.json`).

**API login + 2FA**

- `POST /api/v1/auth/login` — when `user.two_factor_enabled`, **403** with `{ "requires_2fa": true, "temp_token": "…" }`.
- `POST /api/v1/auth/2fa/verify` — TOTP completion → `{ "token": "tt_…" }` (`app/utils/api_auth_2fa.py`, 5-minute signed challenge).
- Desktop/mobile: 2FA sign-in step; API token paste + OIDC notes. Extension: token paste + `requires_2fa` detection in `lib/api.js` (options UI TOTP step still TODO).
- Tests: `tests/test_api_v1_auth_2fa.py`.

**Offline sync**

- **Desktop** (`desktop/src/renderer-react/src/sync/syncEngine.js`): `Idempotency-Key` (UUID) on queued `time_entry_create`; PATCH updates with `if_updated_at` via API client; 409 conflicts drop stale updates; max **8** attempts then queue item status `failed`; sync continues other items instead of aborting the whole batch.
- **Desktop API** (`services/api.js`): `createTimeEntry` sends optional idempotency header; `updateTimeEntry` uses `PATCH` (matches mobile/API v1).
- **Mobile** (`sync_service.dart`, `time_tracking_repository.dart`): offline timer **start** queues `timer_start` (not manual create); offline **stop** queues `timer_stop` and clears local timer with a provisional cached entry.

**Tests**

- **Browser extension**: `node --test` in `browser-extension/test/api.test.js` — `buildAuthHeaders`, timer start/stop fetch wrappers (`npm test` in extension folder).
- **Mobile**: `mobile/test/sync_service_test.dart` for idempotency key shape/uniqueness.

**i18n / UX**

- **Desktop**: `src/renderer-react/src/i18n/` (`en.json`, `t()` helper); Shell sidebar nav labels wired through i18n.
- **Extension**: `popup.css` `prefers-color-scheme: dark` tokens for popup surfaces and form controls.

**Legacy desktop renderer**

- Electron loads **only** `dist-renderer/` (hard error if missing build).
- Splash moved to `src/main/splash/`; deprecated `src/renderer/` HTML/bundle removed; `js/` kept for existing desktop unit tests; excluded from electron-builder package via `!src/renderer/**`.

**Follow-ups**

- Desktop: queue failed-item UI, locale switching, broader string catalog.
- Mobile: widget test for offline timer stop UX; retry/backoff parity with desktop max attempts.
- Extension: options page dark mode; shared i18n if extension strings grow; options TOTP step after password login.
- Rebuild desktop renderer (`npm run build:renderer`) before release; OIDC browser redirect deferred.

### Phase 2

**List components (`empty_state`, `pagination_nav`, table scroll):** Inventory list pages, CRM (leads/contacts/deals), recurring invoices, milestones, audit logs, and admin list pages (roles, link templates, webhooks, custom fields, email templates). Shared list partials `_tasks_list`, `_projects_list`, `_clients_list`, `_invoices_list`, `_quotes_list` wrap tables in `overflow-x-auto`. No shared bulk/filter partial yet (markup differs per page); skeleton macros in `components/ui.html` for future loading states.

**Bootstrap class cleanup (Tailwind migration):** Removed leftover Bootstrap form/layout/pagination classes from **18** Jinja templates (e.g. `form-control` → `form-input`, `form-select` → `form-input`, `card-body` → `p-6`, `col-md-*` → Tailwind `grid`/`col-span`, `page-item`/`input-group` → `btn` nav and icon-in-input patterns). Modal markup (`modal-dialog`) deferred to a dedicated dialogs pass. Remaining hits are mostly `form-group-wrapper` in `components/ui.html` (project component, not Bootstrap).

**Shared confirm/alert dialogs** — `app/static/js/confirm-dialog.js` exposes `window.ttConfirm` / `window.ttAlert` (Promise-based, focus trap, Escape to dismiss, dark-mode styling). Loaded via the `core-a1` bundle in `scripts/build-js.mjs`. Legacy `showConfirm` / `showAlert` alias the same helpers.

Migrated high-traffic templates and JS away from native `alert()` / `confirm()` (pdf layout editor, manual entry, invoice view, dashboard, reports index, timer page, calendar, integration/OIDC/LDAP wizards, context-menu deletes in `ui-enhancements.js`). Remaining call sites should migrate incrementally; search with `rg '\b(alert|confirm)\s*\(' app/templates app/static`.

### Phase 5 (Strategic / enterprise foundations)

Design docs and minimal scaffolding only—no full OAuth server, SAML IdP, or SCIM CRUD yet.

| Area | Deliverable | Location |
|------|-------------|----------|
| OAuth 2.0 API apps | Authlib-oriented design + `OAuthApplication` / `OAuthAuthorizationCode` models | `docs/design/OAUTH2_API_APPS.md`, migration **197** |
| SAML + SCIM | SAML login design; SCIM Users list stub behind `SCIM_ENABLED` | `docs/design/SAML_SCIM.md`, `app/routes/api_scim.py` |
| AI timesheet summaries | `LLMService.summarize_time_entries`, `POST /api/v1/ai/summarize-entries` | `app/services/llm_service.py`, `app/routes/api_v1_ai.py` |
| Teams bot | `/tt` parity plan + stub bot handler | `docs/design/TEAMS_BOT.md`, `MicrosoftTeamsConnector.handle_bot_command` |
| Multi-tenant | Row-level vs schema-per-tenant analysis + recommendation | `docs/design/MULTI_TENANT.md` |
| Zapier / Make | Webhook trigger mapping using existing `WebhookEvent` | `docs/design/ZAPIER_MAKE.md` |

**Follow-ups:** Authlib authorization server routes, SAML ACS, SCIM user CRUD, Bot Framework JWT, `organization_id` rollout, official Zapier OAuth app.

### Phase 4 (high-return missing features — shipped slices)

- **GDPR erasure** — `app/services/user_gdpr_service.py`; `users.anonymized_at` (migration **197**); self-service `POST /api/v1/users/me/erase`, `POST /api/erase-account`, admin `POST /admin/users/<id>/erase`; audit log action `anonymized`; API tokens revoked; username reserved via `DeletedUsername`.
- **API v1** — `api_v1_weekly_goals.py`, `api_v1_recurring_tasks.py`, `api_v1_project_templates.py` (list + get).
- **Estimates vs actuals** — `EstimateActualsService`; `/reports/estimates-vs-actuals`, `/reports/api/estimates-vs-actuals`, `GET /api/v1/reports/estimates-vs-actuals`.
- **Multi-level approvals** — Timesheet period two-step approve when `TimesheetPolicy.enable_multi_level_approval` + two approver IDs; time entry requests can use the same policy chain.
- **Integrations / presets** — Experimental `app/utils/xrechnung.py`; `MollieProvider` in payment registry; Admin → Modules quick presets (Solo = CRM/inventory off); custom field `entity_type` column.

**Tests:** `tests/test_user_gdpr_erase.py`, `tests/test_api_v1_weekly_goals.py`

**Follow-ups**

- Full XRechnung CIUS-DE field mapping and invoice download wiring.
- Admin UI button for GDPR erase on user row; import/export page link for account erasure.
- Custom field rendering on project/task/time entry forms (definitions only extended).
