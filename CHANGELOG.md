# Changelog

All notable changes to TimeTracker will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **Invoice PDF designer Items Table alignment (#622, follow-up)** — Fixed the regression where exported tables were still misaligned after the color fix: text and images use page-absolute coordinates on the PDF canvas, but tables were laid out in the margin-adjusted flow area (`left_offset = x − margin`), so a table at `x=40` appeared at the content edge (~57pt) while the preview showed 40pt. Items/expenses tables are now drawn on the canvas at template `(x, y)` via `wrap`/`drawOn`, with width capped to the remaining page width. The template editor serializes table groups with `getClientRect()` so moved/scaled tables match saved JSON. **Generate Preview** for invoice and quote PDFs now returns the same ReportLab PDF bytes as export (HTML preview remains fallback). Header/row colors and column alignment continue to use per-cell `ParagraphStyle`; `hAlign = LEFT` is retained (`app/utils/pdf_generator_reportlab.py`, `app/routes/admin.py`, `app/templates/admin/pdf_layout.html`, `app/templates/admin/quote_pdf_layout.html`).

### Tests

- **Invoice PDF template Items Table** — `tests/test_invoice_pdf_template_table.py` covers colors, alignment, `rowBackground`, canvas story collection, page-bound width capping, and PDF generation when table `x` is below the left margin.

## [5.6.1] - 2026-05-20

### Fixed

- **Docker / PDF build** — Bumped `pydyf` to 0.12.1 for compatibility with WeasyPrint 68 in container builds.
- **Security** — Upgraded `PyJWT` to 2.12.1 (RFC 7515 `crit` validation, CVE-2026-32597) and `markdown` to 3.8.1 (DoS fixes).

### Changed

- **Docker build context** — Added `.dockerignore` to exclude local `.venv` and shrink image build context.

### Documentation

- **Version** — Documented release **5.6.1** to match `setup.py` (single source of truth for the application version).

## [5.6.0] - 2026-05-15

### Added

- **Personal integration connectors — GitHub, Google Calendar, Slack** — Three new per-user, opt-in connectors that subclass `app/integrations/base.py` and persist their config inside the existing `Integration.config` JSONB (no new tables, all secrets encrypted at rest). The new `app/routes/integrations_webhooks.py` blueprint exposes signature-verified webhook receivers (`POST /api/integrations/github/webhook` with `X-Hub-Signature-256`, `POST /api/integrations/slack/events` with `X-Slack-Signature`), the Google OAuth flow (`/integrations/google/{connect,callback,disconnect}`), and a uniform `config`/`status`/`test`/`sync` API surface for each provider. GitHub auto-creates tasks on `issues.opened`, marks them done on `issues.closed`, and (optionally) starts a timer on `issues.assigned` for the linked TimeTracker user (`users.github_username`). Google Calendar supports `import` / `export` / `both` directions with token refresh inside a 5-minute window and a 30-minute scheduled sync (`google_calendar_sync` APScheduler job). Slack posts a stopwatch/checkmark message on every timer start/stop (fire-and-forget hook in `app/routes/timer.py` and `app/routes/api.py`), implements the `/tt` slash command (`start [project]` / `stop` / `status` / `today`), and posts a configurable daily summary (`slack_daily_summary` APScheduler job, every 30 minutes). Three new cards in **Settings → Integrations → Personal connectors** drive the UI (`app/templates/integrations/_connector_cards.html`, vanilla JS + Tailwind). New migration `155_add_integration_columns` adds `users.github_username` and an indexed `tasks.external_ref` for de-duplicating webhook events. Every connector degrades gracefully — when the `Integration` row is missing or `is_active=False` all methods return `{"ok": false, "error": "Integration not configured"}` without raising. See [docs/integrations/GITHUB_CONNECTOR.md](docs/integrations/GITHUB_CONNECTOR.md), [docs/integrations/GOOGLE_CALENDAR.md](docs/integrations/GOOGLE_CALENDAR.md), and [docs/integrations/SLACK.md](docs/integrations/SLACK.md).
- **Custom themes** — Per-user theme picker under **Settings → Custom theme**. Eight built-in themes (`default`, `ocean`, `forest`, `sunset`, `lavender`, `rose`, `slate`, `high-contrast`) plus four independent overrides: accent colour (10 presets or any `#RRGGBB`), sidebar style (default/compact/minimal hover-expand), text size (sm/base/lg) and corner radius (sharp/rounded/pill). Live preview swaps a `<style id="tt-theme-vars">` block via `GET` / `POST /api/user/theme`; preferences persist on the `users` table via migration `156_add_user_theme_columns`. Default theme injects no CSS at all so existing users see zero visual change until they opt in. Backed by `ThemeService` (`app/services/theme_service.py`) and the self-contained `components/theme_picker.html` component (vanilla JS, no framework). See [docs/features/CUSTOM_THEMES.md](docs/features/CUSTOM_THEMES.md).
- **Personal productivity dashboard** — New **My productivity** page at `/dashboard/productivity` (sidebar link) with today/week summary, streaks, 14-day hours chart, project doughnut, focus stats, 12-week activity heatmap, and insight cards. Backed by `ProductivityService` (user-timezone-aware) and `GET /api/productivity/stats` (`period` 1–90 days, 5-minute cache when no active timer). See [docs/features/PRODUCTIVITY_DASHBOARD.md](docs/features/PRODUCTIVITY_DASHBOARD.md).
- **AI time entry suggestions** — `GET /api/ai/suggest` returns deterministic (and optional LLM-rich) project/task/notes suggestions. Wired into the Start Timer modal (`components/ai_suggestions.html`) and manual entry **Autofill** (`js/ai_autocomplete.js`) when the AI helper is enabled.
- **Project forecast panel** — `ForecastService` and `GET /api/projects/<id>/forecast` (deterministic metrics plus optional `?ai=true` narrative; 10-minute in-process cache). Self-contained card on active projects with estimated hours or budget. Documented in [docs/BUDGET_ALERTS_AND_FORECASTING.md](docs/BUDGET_ALERTS_AND_FORECASTING.md) and [docs/features/PROJECT_DASHBOARD.md](docs/features/PROJECT_DASHBOARD.md).
- **Smart reminders: break, end-of-day, and idle toasts** — Extends smart in-app notifications with optional **break reminder** (Pomodoro-style nudge every N minutes while a timer runs, 15–240 min) and **end-of-day wrap-up** (hours logged today in a configurable hour window). New kinds `break_reminder` and `end_of_day_reminder` in `NotificationService`; user prefs under **Settings → Notifications**; migration `154_add_smart_notify_break_and_eod`. [`app/static/idle.js`](app/static/idle.js) shows blue/purple/green toasts for no-tracking, break, and end-of-day (alongside existing idle stop-timer prompt). APScheduler job `smart_reminder_push` (every 15 min) sends browser push for eligible users when VAPID and push subscriptions are available. Env default `SMART_NOTIFY_END_OF_DAY_AT` (`17:00`). See [docs/features/SMART_NOTIFICATIONS.md](docs/features/SMART_NOTIFICATIONS.md).

### Documentation

- **Version** — Documented release **5.6.0** to match `setup.py` (single source of truth for the application version).

## [5.5.7] - 2026-05-14

### Fixed

- **Invoice PDF designer layout** — Restored the missing canvas-area wrapper in the invoice PDF designer so the properties panel sits in the third grid column beside the canvas instead of stacking below it (`app/templates/admin/pdf_layout.html`).
- **Invoice PDF preview vs export (#622)** — The JSON-to-HTML preview path now uses the same table style keys as export (header and row text, row background, border width) so the preview matches generated PDFs.

### Changed

- **Designer template JSON and ReportLab export** — Saving template JSON from the designer reads items-table and expenses-table width, colors, and separator line settings from the Konva group children; column widths scale to the chosen table width and a style block is emitted for ReportLab (`app/routes/admin.py`, `pdf_layout.html`).
- **ReportLab invoice tables** — Column widths scale to `element.width`; tables are wrapped in a two-column outer table so horizontal offset from the left margin is honored; `borderColor` and `borderWidth` from template style are applied (`app/utils/pdf_generator_reportlab.py`).

### Documentation

- **Version** — Documented release **5.5.7** to match `setup.py` (single source of truth for the application version).

## [5.5.6] - 2026-05-14

### Documentation

- **Uninstall / AI** — Expanded [UNINSTALL.md](UNINSTALL.md) with a dedicated **Disabling or removing the AI helper** section (admin UI, `.env`, Docker `ai` profile, `ollama_data` volume vs full `down -v`, API token scopes `read:ai` / `write:ai`, hosted provider keys).
- **Version** — Documented release **5.5.6** to match `setup.py` (single source of truth for the application version).

## [5.5.5] - 2026-05-12

### Fixed

- **Main column layout and footer alignment** — Removed an extra closing `</div>` in `{% block content %}` on admin backups, admin API tokens, and quote detail templates. Invalid HTML caused the browser to recover by closing ancestor nodes early (including `#mainContent`), leaving modals and page chrome mis-nested so the authenticated “Built by an independent developer” line no longer lined up with the content column.

### Changed

- **App shell uses full main-column width** — `base.html` no longer caps `<main id="mainContentAnchor">` or the attribution line with `max-w-7xl`; the main area and support banner inner row span the width beside the sidebar (padding unchanged). `<main>` and the footer line sit in a shared `flex-1 flex flex-col min-w-0 w-full` wrapper so the column grows vertically with the layout.

## [5.5.4] - 2026-05-11

### Fixed

- **Full database restore** — Admin restore cleanup no longer uses `current_app` from a background thread outside Flask application context. While `restore_backup` runs (archive extract through Alembic upgrade), the app sets `_database_restore_in_progress`; the client portal global context processor skips non-essential database reads during that window and rolls back the session on `SQLAlchemyError` so login and error pages can render when PostgreSQL schema is briefly torn during `pg_restore --clean`.

### Documentation

- **Backup and restore** — Added [docs/admin/BACKUP_AND_RESTORE.md](docs/admin/BACKUP_AND_RESTORE.md) and cross-links from the admin index, [DATABASE_RECOVERY.md](DATABASE_RECOVERY.md), and import/export guides for operational behaviour during restore.

## [5.5.3] - 2026-05-06

### Fixed
- **Approvals status values stored correctly** — `ClientApprovalStatus` values are now bound to the Postgres enum values (not the Python enum member names), preventing mismatches between API payloads/UI state and the persisted status.
- **Clients view delete-note confirmation** — Removed a nested `<script>` tag that could orphan `confirmDeleteNote`, causing delete confirmation to break in the clients view.

## [5.5.2] - 2026-04-30

### Fixed
- **Quote edit redirect for delegated editors** — Users with `edit_quotes` permission could save changes on draft quotes they did not create but were redirected to an empty/“not found” flow because quote detail/list visibility was still filtered by `created_by`. Quote list/detail scope now matches edit capability for users with `edit_quotes` across web and API quote reads. Added a regression test for edit-then-redirect view loading and updated quote comment edit context links.

## [5.5.0] - 2026-04-27

### Added
- **LDAP authentication** — Optional directory login via `AUTH_METHOD=ldap` or combined `AUTH_METHOD=all` (with local + OIDC). New `LDAP_*` settings in `app/config.py`, `LDAPService` (`app/services/ldap_service.py`), login and password-reset behaviour keyed off `users.auth_provider` (`local` | `oidc` | `ldap`), admin **System Settings** LDAP panel and `POST /admin/ldap/test`, production env validation for required LDAP variables, Alembic `153_add_user_auth_provider`, and tests in `tests/test_ldap_auth.py`. Dependency: `ldap3`. Documentation: [docs/admin/configuration/LDAP_SETUP.md](docs/admin/configuration/LDAP_SETUP.md); OIDC and getting-started guides updated for `ldap` / `all`.

### Fixed
- **Admin “Allow only one active timer per user” ignored at runtime** — Timer start and related flows always blocked a second running entry and never read `Settings.single_active_timer` from the database. Enforcement now uses `Settings.get_settings()` via `TimeTrackingService.can_start_timer` (web timer routes, REST v1, kiosk start, legacy session `POST /api/timer/resume`). `POST /api/v1/timer/start` returns **409** with `error_code: timer_already_running` when the setting is on and a timer is already running. `SINGLE_ACTIVE_TIMER` still seeds new installs only. Tests: `tests/test_single_active_timer_setting.py`.
- **API integration test for project tasks** — `tests/test_api_comprehensive.py` now matches `GET /api/projects/<id>/tasks`, which returns **all** tasks (including done and cancelled) for the time-entry UI.
- **Quote create returned HTTP 500 after save (#583)** — The quote was saved, but the redirect to the quote detail page crashed when **Valid until** was set: the template compared `valid_until` to `now()`, and `now` was never defined in the Jinja context. The expired badge now uses `Quote.is_expired` (same rule, app timezone). Regression coverage in `tests/test_routes/test_quotes_web.py` posts `valid_until` so the view path is exercised.
- **Desktop app navigation guard** — `will-navigate` no longer mis-classifies `file:` loads (opaque `"null"` origin) as external navigation. Allowed in-app protocols include `file:`, `about:`, and `devtools:`; `http:` / `https:` are still blocked from the embedded window.
- **Desktop offline UI (bundle)** — Shared helpers load before dependent modules; timesheet period and time-off request lists expose **Delete** where allowed (with `currentUserProfile.id` for ownership); approve/reject controls read approval state from `state.currentUserProfile`; API client includes `deleteTimesheetPeriod` and `deleteTimeOffRequest`.

### Added
- **Mobile bottom navigation (web)** — On viewports below the `md` breakpoint (768px), signed-in users get a fixed bottom bar with tabs for Dashboard, Timer, Time entries, Projects, and **More**. **More** opens a slide-up drawer (backdrop, close control, Escape) linking to Invoices, Clients, Reports, and **My Settings** (`user.settings`), respecting module enablement where applicable. Implementation: [`app/templates/partials/_bottom_nav.html`](app/templates/partials/_bottom_nav.html) included from [`app/templates/base.html`](app/templates/base.html); [`app/static/mobile.js`](app/static/mobile.js) drives the drawer. **Safe area:** `pb-safe` utility in [`app/static/src/input.css`](app/static/src/input.css) and safelist in [`tailwind.config.js`](tailwind.config.js). Main content uses `pb-16` on small screens so it is not covered by the bar. Layout breakpoint for sidebar visibility, main margin, mobile menu, and RTL `#mainContent` margin is aligned to `md` (768px).
- **Smart in-app notifications** — Opt-in under **Settings → Notifications → In-app reminders**: nudge when no time is logged today (configurable hour window, user timezone), alert when an active timer exceeds a configurable duration, and end-of-day summary of hours logged. Server-driven via `GET /api/notifications` and `POST /api/notifications/dismiss`; per-day dismissals stored in `user_smart_notification_dismissals`. Environment defaults: `SMART_NOTIFY_MAX_PER_DAY`, `SMART_NOTIFY_NO_TRACKING_AFTER`, `SMART_NOTIFY_SUMMARY_AT`, `SMART_NOTIFY_LONG_TIMER_HOURS`, `SMART_NOTIFY_SCHEDULER_SLOT_MINUTES` (see `app/config.py` and [docs/features/SMART_NOTIFICATIONS.md](docs/features/SMART_NOTIFICATIONS.md)). Migration `150_add_smart_notifications`. The dashboard client polls the API and shows toasts (optional browser notifications when enabled and permission granted). `toastManager.show` supports an optional `onDismiss` callback.
- **Value dashboard widget** — Dashboard productivity block backed by `StatsService` and `GET /api/stats/value-dashboard` (short-TTL Redis cache when available). Wired from `dashboard-enhancements.js` with the existing real-time dashboard refresh.
- **Quote line item reorder (Issue #584)** — Non-null `quote_items.position` (migration `146_add_quote_item_position`); `Quote.items` is ordered by `position`, then `id`. Create, edit, duplicate, bulk duplicate, API item payloads, and quote-template apply assign positions from the submitted row order. **Create quote** and **edit quote** forms include per-row **Move up** / **Move down** controls on **Quote line items**, **Costs**, and **Extra goods** so rows can be reordered without deleting and re-entering data; PDFs and detail views follow the saved order. New translatable UI strings: **Order**, **Move up**, **Move down** (run `pybabel extract` / `update` per [docs/CONTRIBUTING_TRANSLATIONS.md](docs/CONTRIBUTING_TRANSLATIONS.md)).
- **Offline queue replay** — Queued requests now store method, headers, and body in a replay-safe form (serializable for localStorage). POST/PUT requests replayed when back online send the same body and method. Legacy queue items (with `options` only) are still replayed via fallback.
- **Inventory API scopes** — New scopes `read:inventory` and `write:inventory` for inventory-only API access. Existing `read:projects` and `write:projects` still grant the same inventory access for backward compatibility.
- **Client portal reports: date range and CSV export** — Reports support optional `days` query param (1–365, default 30). Add `?format=csv` to download a CSV of the same report (summary, hours by project, time by date). Export uses the same access control as the reports page.
- **Jira webhook verification** — When a webhook secret is configured in the Jira integration (Connection Settings → Webhook Secret), incoming webhooks are verified using HMAC-SHA256 of the request body. Supported headers: `X-Hub-Signature-256`, `X-Atlassian-Webhook-Signature`, `X-Hub-Signature`. Requests with missing or invalid signature are rejected. If no secret is set, behavior is unchanged (all webhooks accepted).
- **Crowdin integration (maintainers)** — Root [`crowdin.yml`](crowdin.yml) maps `translations/en/LC_MESSAGES/messages.po` to per-locale `messages.po` paths (with `nb` → `no` for Norwegian). Manual [`.github/workflows/crowdin-sync.yml`](.github/workflows/crowdin-sync.yml) uploads sources and downloads translations when `CROWDIN_PROJECT_ID` and `CROWDIN_PERSONAL_TOKEN` are set. [docs/CONTRIBUTING_TRANSLATIONS.md](docs/CONTRIBUTING_TRANSLATIONS.md) includes a Crowdin setup section; [docs/TRANSLATION_SYSTEM.md](docs/TRANSLATION_SYSTEM.md) and contributor docs cross-link it.

### Changed
- **Documentation (API)** — Documented session-auth `GET /api/stats/value-dashboard` (response fields, Redis TTL, rate resolution) in [`docs/api/REST_API.md`](docs/api/REST_API.md) and linked dashboard session JSON from [`docs/API.md`](docs/API.md).
- **API v1 search scoping** — Project, task, and client branches of token search use shared `apply_project_scope` and `apply_client_scope` query helpers in [`app/utils/scope_filter.py`](app/utils/scope_filter.py) for consistent subcontractor restrictions.
- **Documentation (translations)** — Added [docs/CONTRIBUTING_TRANSLATIONS.md](docs/CONTRIBUTING_TRANSLATIONS.md) for contributors without Git (issue template, optional spreadsheet or hosted platform, maintainer workflow). Root [CONTRIBUTING.md](CONTRIBUTING.md) links to it; [docs/TRANSLATION_SYSTEM.md](docs/TRANSLATION_SYSTEM.md) defers the enabled locale list to `app/config.py` (`LANGUAGES`) and points translators at the new guide.
- **Factur-X / PDF/A-3 invoice PDFs (export and email)** — Download and email attachments use the same embed-and-normalize path. Embedded CII uses Associated File relationship **Data** and MIME **text/xml**. PDF/A-3 normalization embeds sRGB via `app/resources/icc/` (override with `INVOICE_SRGB_ICC_PATH`). Added `app/utils/invoice_pdf_postprocess.py` and tests; [PEPPOL e-Invoicing](docs/admin/configuration/PEPPOL_EINVOICING.md) updated (veraPDF note, pytest command).
- **Documentation sync** — CODEBASE_AUDIT.md: marked gaps 2.3–2.7 and 2.9 as fixed; added “Implemented 2026-03-16” summary. CLIENT_FEATURES_IMPLEMENTATION_STATUS: report date range and CSV export noted as implemented. INCOMPLETE_IMPLEMENTATIONS_ANALYSIS: added “Verified 2026-03-16” for webhook verification, issues permissions, search API, offline queue.
- **Activity feed API date params** — `/api/activity` now returns 400 with a clear message when `start_date` or `end_date` are invalid (e.g. not ISO 8601). Invalid dates on the web route `/activity` are logged and the filter is skipped (no 500).
- **Invoice PEPPOL compliance check** — Exceptions in the PEPPOL compliance block are no longer silently ignored: specific and generic exceptions are caught, logged, and a generic warning (“Could not verify PEPPOL compliance; check configuration.”) is shown to the user so the view still renders.
- **Documentation and i18n audit** — Updated docs and translations to match current implementation: removed stale "coming soon" claims; marked INCOMPLETE_IMPLEMENTATIONS_ANALYSIS as historical and added still-relevant summary; rewrote INVENTORY_MISSING_FEATURES as "Remaining Gaps" (transfers, adjustments, reports, PO management, API are implemented); updated GETTING_STARTED (PDF export, project permissions, REST API); REST_API (webhooks supported); KEYBOARD_SHORTCUTS_SUMMARY (customization implemented); BULK_TASK_OPERATIONS (bulk due date/priority implemented); INVENTORY_IMPLEMENTATION_STATUS (report templates done); activity_feed (invoices/clients/comments status clarified). Removed orphaned translation strings "Bulk due date update feature coming soon!" and "Bulk priority update feature coming soon!" from 10 locale `.po` files.

### Added
- **Mileage and Per Diem export and filter (Issue #564)** — Mileage and Per Diem now support CSV and PDF export using the same filter set as the list view, matching Time Entries behavior. **Mileage**: Export CSV and Export PDF buttons in the filter card; exports use current filters (search, status, project, client, date range). Routes: `GET /mileage/export/csv`, `GET /mileage/export/pdf`. PDF report via [app/utils/mileage_pdf.py](app/utils/mileage_pdf.py) (ReportLab, landscape A4, totals row). **Per diem**: Client filter added to the list form (with client-lock/single-client handling); Export CSV and Export PDF buttons; routes `GET /per-diem/export/csv`, `GET /per-diem/export/pdf`. PDF via [app/utils/per_diem_pdf.py](app/utils/per_diem_pdf.py). Export links are built from the current filter form (JS), so applied filters apply to both the list and the downloaded file.
- **Break time for timers and manual time entries (Issue #561)** — Pause/resume running timers so time while paused counts as break; on stop, stored duration = (end − start) − break (with rounding). Manual time entries and edit form have an optional **Break** field (HH:MM); effective duration is (end − start) − break. Optional default break rules in Settings (e.g. >6 h → 30 min, >9 h → 45 min) power a **Suggest** button on the manual entry form; users can override. New columns: `time_entries.break_seconds`, `time_entries.paused_at`; Settings: `break_after_hours_1`, `break_minutes_1`, `break_after_hours_2`, `break_minutes_2`. API: `POST /api/v1/timer/pause`, `POST /api/v1/timer/resume`; timer status and time entry create/update accept and return `break_seconds`. See [docs/BREAK_TIME_FEATURE.md](docs/BREAK_TIME_FEATURE.md).
- **Architecture refactor** — API v1 split into per-resource sub-blueprints (projects, tasks, clients, invoices, expenses, payments, mileage, deals, leads, contacts) under `app/routes/api_v1_*.py`; bootstrap slimmed by moving `setup_logging` to `app/utils/setup_logging.py` and legacy migrations to `app/utils/legacy_migrations.py`. Dashboard aggregations (top projects, time-by-project chart) moved into `AnalyticsService` (`get_dashboard_top_projects`, `get_time_by_project_chart`); dashboard route simplified to call services only. ARCHITECTURE.md updated with module table, API structure, and data flow; DEVELOPMENT.md with development workflow and build steps.

### Fixed
- **Xero integration for apps created after March 2026 (Issue #567)** — OAuth no longer fails with "Invalid scope for client" for Xero Developer apps created on or after March 2, 2026. Replaced deprecated `accounting.transactions` scope with granular `accounting.invoices` and `accounting.payments`. Expense sync now uses the correct `/api.xro/2.0/ExpenseClaims` endpoint (replacing the non-existent `/api.xro/2.0/Expenses`) and reads `ExpenseClaimID` from the response. `_api_request` now accepts an optional request body so invoice and expense payloads are sent to the Xero API. See [docs/integrations/XERO.md](docs/integrations/XERO.md).
- **Time Entries date filter and export (Issue #555)** — Start/End date filters were hard to discover and exports ignored them. The Time Entries overview now has a visible **Apply filters** button in the filter header (next to Clear Filters and Export) so users can apply date and other filters without scrolling. CSV and PDF export links always use the current filter parameters: export href is set from the page URL on load and updated whenever filter form values change, so left-click export, right-click "Open in new tab", and "Save link as" all produce filtered exports. The in-form Apply filters button and the header button both trigger the same filter logic; clicking the header button expands the filter panel if it is collapsed.
- **Log Time / Edit Time Entry on mobile (Issue #557)** — Opening the manual time entry ("Log Time") or edit time entry page on mobile could freeze or crash the browser. The Toast UI Editor (WYSIWYG markdown editor) for the notes field is heavy and causes freezes on mobile Safari/Chrome. On viewports ≤767px we now skip loading the editor and show a plain textarea for notes instead; desktop behavior is unchanged. Manual entry and edit timer templates load Toast UI only when not in mobile view.
- **Stop & Save error (Issue #563)** — Fixed error after clicking "Stop & Save" on the dashboard. The post-timer toast was building the "View time entries" URL with the wrong route name (`timer.time_entries`); the correct endpoint is `timer.time_entries_overview`. Time entries were already saved; the error occurred when rendering the dashboard redirect.
- **Dashboard cache (Issue #549)** — Removed dashboard caching that caused "Instance not bound to a Session" and "Database Error" on second visit. Cached template data contained ORM objects (active_timer, recent_entries, top_projects, templates, etc.) that become detached when served in a different request.
- **Task description field (Issue #535)** — When creating or editing a task, the description field could appear missing or broken if the Toast UI Editor (loaded from CDN) failed to load (e.g. reverse proxy, CSP, Firefox, or offline). A fallback now shows a plain textarea so users can always enter a description; Markdown is still supported when the rich editor loads.
- **ZUGFeRD / PDF/A-3 and PEPPOL (Discussion #433)** — ZUGFeRD embedding no longer silently succeeds without XML when the embed step fails; export is aborted with an actionable error. XMP metadata is created when missing so validators recognize the document. Optional PDF/A-3 normalization (XMP identification and output intent) and optional veraPDF validation gate added. Native PEPPOL transport (SML/SMP + AS4) and strict sender/recipient identifier validation added.

### Added
- **Dashboard time-by-project chart** — "Time by project (last 7 days)" horizontal bar chart on the dashboard (Chart.js); link to Summary report.
- **Summary report charts** — Time-by-project (last 30 days) bar chart and daily trend (last 14 days) line chart on the Summary report page.
- **Summary report PDF export** — New route `/reports/summary/export/pdf`; one-page PDF with today/week/month hours and top projects table ([app/utils/summary_report_pdf.py](app/utils/summary_report_pdf.py)).
- **Post-timer toast** — After stopping the timer, a success toast shows "Logged Xh on [Project]" with an action link "View time entries"; toast manager supports optional `actionLink` and `actionLabel`.
- **Remind to log** — User setting "Remind me to log time at end of day" with time picker (Settings); scheduled task runs hourly and sends one email per day to users who have the reminder enabled and have logged &lt; 0.5h that day (in their timezone). Migration `135_add_remind_to_log_settings` adds `notification_remind_to_log` and `reminder_to_log_time` to users.
- **Migration merge 133** — Merge heads 132 (timesheet governance) and 129 (task tags) so `flask db upgrade` runs without conflicts.
- **PEPPOL native transport** — Transport mode can be set to **Native** (SML/SMP participant discovery + AS4 send) in addition to **Generic** (HTTP JSON access point). Sender and recipient identifiers are validated before send. New settings: `peppol_transport_mode`, `peppol_sml_url`, `peppol_native_cert_path`, `peppol_native_key_path` (Admin → Peppol e-Invoicing).
- **PDF/A-3 and validation** — Option **Normalize ZUGFeRD PDFs to PDF/A-3** and optional **Run veraPDF after export** with configurable path. Migration `130_add_peppol_transport_mode_and_native` adds the new columns.
- **Dashboard timer widget** — Pause and Stop buttons while a timer is running (Pause saves the segment so you can resume later). When no timer is active, a prominent "Resume (project name)" button restarts tracking with the same project/task/notes as your last entry. Quick time adjustment buttons (−15 / −5 / +5 / +15 minutes) let you correct the current session without leaving the dashboard. New route `POST /timer/adjust` for start-time adjustment.

### Changed
- **UI/UX redesign** — Consolidated component system: single `page_header`, `empty_state` / `empty_state_compact`, and `loading_overlay` in `components/ui.html`; migrated overdue tasks page from Bootstrap to Tailwind; added form error and disabled states in design tokens. Base layout: main content max-width (1280px) and centered; first-class **Timer** and **Time entries** in sidebar; reduced nav label weight. Timer flow: single adjust-time form with one submit; dashboard hero is the Timer card (start/stop, quick start, repeat last); post-stop toast with “View time entries” unchanged. Dashboard: Timer as hero block first, then Today/Week/Month stats, then Recent entries (last 5, columns Project/Duration/Date/Actions) with “View all” link to Time entries overview. Empty and loading states use shared macros; toasts used for errors and success. New [UI Guidelines](docs/UI_GUIDELINES.md); README and ARCHITECTURE updated with UI overview and UI layer section.
- **Dashboard** — Weekly goal widget already showed progress bar; added time-by-project (7d) chart and chart data from main route.
- **Summary report** — Added Chart.js time-by-project and daily-trend charts; added Export PDF button; backend passes chart and trend data from AnalyticsService.
- **Toast notifications** — Optional `actionLink` and `actionLabel` in toast manager for action links in toasts.
- **Documentation** — README updated with new features (dashboard chart, summary charts/PDF, post-timer toast, remind to log); daily workflow note in Screenshots section.
- **Log Time Manually page** — Redesigned for a more professional layout: form grouped into sections (Project & task, Date & time, Details) with clear headings and icons; main card uses rounded-xl and shadow-lg; unified label and helper text styling; primary "Log Time" and secondary "Clear" buttons aligned with dashboard button styles; duplicate-entry banner uses rounded-xl.

## [4.20.6] - 2025-02-20

### Changed
- **Version Update** — Updated to version 4.20.6.

## [4.20.5] - 2025-02-17

### Changed
- **Version Update** — Updated to version 4.20.5.

## [4.20.0] - 2025-02-16

### Fixed
- **PDF layout: decorative image persistence and PDF preview (Issue #432)** — Decorative images now survive save/load: image URLs are synced onto groups before generating the template, injected into the saved design JSON using position-based matching, and restored from the saved JSON onto the canvas on load. Empty decorative image elements are no longer added to the ReportLab template, and the PDF generator skips empty or invalid image sources and validates base64 data URIs, preventing a mostly-black or broken PDF preview.
- **Header Start Timer button** — Fixed manual entry URL (`/timer/manual_entry` → `/timer/manual`); timer now correctly opens manual entry when starting from the header button.

### Added
- **Header quick access buttons** — Chat, Timer, and Help are grouped in the header as round icon buttons, vertically aligned and evenly spaced. One-click timer start/stop from any page; Help links to documentation; Chat opens team chat when enabled.
- **ZugFerd / Factur-X support for invoice PDFs** — When enabled in Admin → Settings → Peppol e-Invoicing, exported invoice PDFs embed EN 16931 UBL XML as `ZUGFeRD-invoice.xml`, producing hybrid human- and machine-readable invoices. Uses the same UBL as Peppol; these PDFs can be sent via Peppol or email. New setting `invoices_zugferd_pdf`, migration `128_add_invoices_zugferd_pdf`, dependency `pikepdf`, and [docs/admin/configuration/PEPPOL_EINVOICING.md](docs/admin/configuration/PEPPOL_EINVOICING.md) updated for both Peppol and ZugFerd.
- **Subcontractor role and assigned clients** — Users with the Subcontractor role can be restricted to specific clients and their projects. Admins assign clients in Admin → Users → Edit user (section "Assigned Clients (Subcontractor)"). Scope is applied to clients, projects, time entries, reports, invoices, timer, and API v1; direct access to other clients/projects returns 403. New table `user_clients`, migration `127_add_user_clients_table`, and docs in [docs/SUBCONTRACTOR_ROLE.md](docs/SUBCONTRACTOR_ROLE.md).

### Changed
- **Version Update** — Updated to version 4.20.0.

## [4.19.0] - 2025-02-13

### Added
- **REST API v1** - CRM and time approvals: `/api/v1/deals`, `/api/v1/leads`, `/api/v1/clients/<id>/contacts`, `/api/v1/contacts/<id>`, `/api/v1/time-entry-approvals` (list, get, approve, reject, cancel, request-approval, bulk-approve). New API token scopes: `read:deals`, `write:deals`, `read:leads`, `write:leads`, `read:contacts`, `write:contacts`, `read:time_approvals`, `write:time_approvals`.
- **Documentation** - Service layer and BaseCRUD pattern ([docs/development/SERVICE_LAYER_AND_BASE_CRUD.md](docs/development/SERVICE_LAYER_AND_BASE_CRUD.md)); RBAC permission model ([docs/development/RBAC_PERMISSION_MODEL.md](docs/development/RBAC_PERMISSION_MODEL.md)).

### Changed
- **API responses** - Projects and new CRM/approvals API v1 routes use standardized `error_response` / `forbidden_response` / `not_found_response` from `app.utils.api_responses`.
- **Templates** - All templates consolidated under `app/templates/`; root `templates/` removed and extra Jinja loader removed.
- **Version** - README, FEATURES_COMPLETE.md, and docs reference `setup.py` as single source of truth for version (4.19.0).
- **Refactored examples** - `projects_refactored_example.py`, `timer_refactored.py`, `invoices_refactored.py` marked as reference-only in module docstrings.

## [4.14.0] - 2025-01-27

### Changed
- **Version Update** - Updated to version 4.14.0
- **Documentation** - Comprehensive README and documentation updates for clarity and completeness
- **Technology Stack** - Added complete technology stack overview to README
- **Quick Start** - Enhanced with prerequisites, clearer instructions, and troubleshooting links
- **System Requirements** - Added detailed system requirements section
- **Documentation Organization** - Improved organization by use case and user type

### Fixed
- **Version Consistency** - Fixed version inconsistencies across all documentation files
- **Documentation Links** - Fixed broken links and improved navigation
- **Feature Documentation** - Added comprehensive links to feature guides throughout README

## [4.13.2] - 2025-01-27

### Changed
- **Version Update** - Updated to version 4.13.2
- **Documentation** - Comprehensive README and documentation updates for clarity and completeness

### Fixed
- **Version Consistency** - Fixed version inconsistencies across all documentation files

## [4.8.8] - 2025-01-27

### Changed
- **Version Update** - Updated to version 4.8.8
- **Documentation** - Comprehensive project analysis and documentation updates

### Fixed
- **Version Consistency** - Fixed version inconsistencies across documentation files

## [4.6.0] - 2025-12-14

### Added
- **Comprehensive Issue/Bug Tracking System** - Complete issue and bug tracking functionality with full lifecycle management

## [4.5.1] - 2025-12-13

### Changed
- **Performance Optimization** - Optimized task listing queries and improved version management
- **Version Management** - Enhanced version management system

## [4.5.0] - 2025-12-12

### Added
- **Advanced Report Builder** - Iterative report generation with email distribution capabilities
- **Quick Task Creation** - Create tasks directly from the Start Timer modal for faster workflow
- **Kanban Board Enhancements** - Added user filter and flexible column layout options
- **PWA Install UI** - Improved Progressive Web App installation user interface

### Fixed
- **Permission and Role Management** - Fixed bugs in permission and role management system

### Changed
- **Error Handling** - Improved error handling throughout the application
- **Performance Logging** - Enhanced performance logging and monitoring

## [4.4.1] - 2025-12-08

### Added
- **Custom Reports Enhancement** - Enhanced custom reports and scheduled reports functionality

### Fixed
- **Dashboard Cache Invalidation** - Fixed dashboard cache invalidation when editing timer entries (#342)
- **Custom Field Definitions** - Fixed graceful handling of missing custom_field_definitions table (#344)

## [4.4.0] - 2025-12-03

### Added
- **Project Custom Fields** - Add custom fields to projects for enhanced project tracking
- **File Attachments** - File attachment support for projects and clients
- **Salesman-Based Report Splitting** - Report splitting and email distribution based on salesperson assignments

### Changed
- **Performance Optimization** - Optimized task queries and fixed N+1 performance issues
- **Version Update** - Updated setup.py version to 4.4.0

## [4.3.2] - 2025-12-02

### Added
- **Custom Field Filtering** - Custom field filtering and display for clients, projects, and time entries
- **Client Count Tracking** - Client count tracking and cleanup for custom field definitions
- **Unpaid Hours Report** - New unpaid hours report with Ajax filtering and Excel export
- **Time Entries Overview** - New time entries overview page with AJAX filters and bulk mark as paid
- **Configurable Duplicate Detection** - Configurable duplicate detection fields for CSV client import
- **Enhanced Audit Logging** - Improved error handling and diagnostic tools for audit logging

### Changed
- **Offline Sync** - Enhanced offline sync functionality and performance improvements
- **Error Handling** - Improved error handling throughout the application
- **Docker Healthchecks** - Enhanced Docker healthcheck functionality

## [4.3.1] - 2025-12-01

### Changed
- **Offline Sync** - Enhanced offline sync functionality and performance improvements

## [4.3.0] - 2025-12-01

### Added
- **Custom Field Filtering** - Custom field filtering and display for clients, projects, and time entries
- **Client Count Tracking** - Client count tracking and cleanup for custom field definitions
- **Unpaid Hours Report** - New unpaid hours report with Ajax filtering and Excel export
- **Time Entries Overview** - New time entries overview page with AJAX filters and bulk mark as paid
- **Configurable Duplicate Detection** - Configurable duplicate detection fields for CSV client import
- **Enhanced Audit Logging** - Improved error handling and diagnostic tools for audit logging

### Changed
- **Error Handling** - Improved error handling throughout the application
- **Docker Healthchecks** - Enhanced Docker healthcheck functionality
- **Offline Sync** - Enhanced offline sync functionality

## [4.2.1] - 2025-12-01

### Fixed
- **AUTH_METHOD=none** - Fixed authentication method when set to none
- **Schema Verification** - Added comprehensive schema verification

## [4.2.0] - 2025-11-30

### Added
- **CSV Import/Export** - CSV import/export for clients with custom fields and contacts
- **Global Custom Field Definitions** - Global custom field definitions with link template support
- **Paid Status Tracking** - Paid status tracking for time entries with invoice reference
- **OAuth Credentials Dropdown** - Converted OAuth credentials section to dropdown in System Settings

---

## Release notes format

This changelog follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Section headings used:

- **Added** — New features
- **Changed** — Changes in existing functionality
- **Deprecated** — Soon-to-be removed features
- **Removed** — Removed features
- **Fixed** — Bug fixes
- **Security** — Security-related changes

For release artifacts and tags, see [GitHub Releases](https://github.com/drytrix/TimeTracker/releases).
