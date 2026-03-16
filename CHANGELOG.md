# Changelog

All notable changes to TimeTracker will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Offline queue replay** — Queued requests now store method, headers, and body in a replay-safe form (serializable for localStorage). POST/PUT requests replayed when back online send the same body and method. Legacy queue items (with `options` only) are still replayed via fallback.
- **Inventory API scopes** — New scopes `read:inventory` and `write:inventory` for inventory-only API access. Existing `read:projects` and `write:projects` still grant the same inventory access for backward compatibility.
- **Client portal reports: date range and CSV export** — Reports support optional `days` query param (1–365, default 30). Add `?format=csv` to download a CSV of the same report (summary, hours by project, time by date). Export uses the same access control as the reports page.
- **Jira webhook verification** — When a webhook secret is configured in the Jira integration (Connection Settings → Webhook Secret), incoming webhooks are verified using HMAC-SHA256 of the request body. Supported headers: `X-Hub-Signature-256`, `X-Atlassian-Webhook-Signature`, `X-Hub-Signature`. Requests with missing or invalid signature are rejected. If no secret is set, behavior is unchanged (all webhooks accepted).

### Changed
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
