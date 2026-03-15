# Architecture Audit

This document captures a concise architecture audit of the TimeTracker repository (Flask app with server-rendered templates, REST API, and desktop/mobile clients). It is used to drive incremental refactors toward thin routes, reusable services, and a predictable repository layer.

---

## Current strengths

- **Clear intended layering**: Routes → services → repositories/models is documented in [ARCHITECTURE.md](../ARCHITECTURE.md) and [Architecture Migration Guide](implementation-notes/ARCHITECTURE_MIGRATION_GUIDE.md).
- **Existing repository layer**: `app/repositories/` provides `BaseRepository` and dedicated repos for TimeEntry, Project, Task, Client, Invoice, Expense, Payment, User, Comment with sensible methods (e.g. `TimeEntryRepository.get_active_timer`, `get_by_date_range`, `get_total_duration`).
- **Central API response helpers**: `app/utils/api_responses.py` defines `success_response`, `error_response`, `validation_error_response`, `paginated_response`, etc.; error handlers in `app/utils/error_handlers.py` use them for JSON/API.
- **Blueprint registry**: Single registration point in `app/blueprint_registry.py` keeps app init clean.
- **Refactor examples**: The migration guide gives a clear "after" pattern. (Historical note: previously unregistered modules `timer_refactored.py`, `projects_refactored_example.py`, `invoices_refactored.py` have been merged or removed.)
- **Validation and schemas**: Marshmallow used for time-entry API v1; `app/utils/validation.py` and `app/utils/time_entry_validation.py` exist; `app/schemas/` has schemas for several resources (underused in routes).

---

## Main architectural risks

1. **Business logic in routes**: Heavy logic in `app/routes/reports.py` (comparison, project_report, unpaid_hours), `app/routes/invoices.py` (many direct queries), `app/routes/recurring_invoices.py`, `app/routes/expenses.py`, `app/routes/deals.py`, `app/routes/gantt.py`, `app/routes/comments.py`, `app/routes/client_notes.py`, `app/routes/audit_logs.py`, and others.
2. **Duplicated query patterns**: "User's distinct project IDs" from TimeEntry appears in budget_alerts, reports, data_export, gantt, timer, api with no shared repo method. Same for "user project IDs + accessible client IDs" in issues.py (4 blocks). Sum(TimeEntry.duration_seconds) repeated in analytics, reports, reporting_service, models, and utils despite `TimeEntryRepository.get_total_duration`.
3. **Inconsistent API contract**: Most api_v1 resource routes return resource-keyed payloads (`{"invoices": [...]}`, `{"invoice": {...}}`) and ad-hoc errors instead of the standard envelope (`success`, `data`, `error`, `error_code`) from `api_responses`.
4. **Validation inconsistency**: Only time-entry API v1 uses Marshmallow; other api_v1_* and all web forms use manual checks. Schemas exist for Invoice, Project, Client, Expense, etc. but are not used in corresponding routes.
5. **God files and tight coupling**: `app/routes/api_v1.py`, `app/routes/timer.py`, `app/routes/api.py`, `app/routes/reports.py`, `app/routes/invoices.py` are very large. Large route files mix many endpoints and inline queries.
6. **Logic in models**: `app/models/recurring_invoice.py` `generate_invoice()` does full workflow. `app/models/expense.py`, `app/models/lead.py`, `app/models/issue.py`, `app/models/project.py` contain state transitions and query/aggregation methods that belong in services/repositories.
7. **Template logic**: Budget and status rules in project view/list templates; task counts via `selectattr` in tasks list/my_tasks/kanban; totals and filters in inventory, client portal, expense_categories. Better to precompute in views.
8. **Missing repositories**: No repository for FocusSession, Activity, AuditLog, StockItem/inventory, RecurringInvoice, and others; services and routes use `Model.query` / `db.session` directly.
9. **Unused/refactor-only code**: (Historical: `timer_refactored.py`, `projects_refactored_example.py`, `invoices_refactored.py` are no longer present; refactors were merged or removed.)

---

## Top 10 refactor targets (ranked by impact and risk)

| # | Target | Impact | Risk | Action |
|---|--------|--------|------|--------|
| 1 | **Centralize "user's distinct project IDs"** | High | Low | Add `TimeEntryRepository.get_distinct_project_ids_for_user(user_id)`; replace 6+ call sites. |
| 2 | **Move RecurringInvoice.generate_invoice to service** | High | Medium | Create `RecurringInvoiceService.generate_invoice(recurring_invoice)`; keep model for state only; add tests. |
| 3 | **Thin reports routes** | High | Medium | Move comparison_view, project_report, unpaid_hours_report (and export) logic into `ReportingService`. |
| 4 | **Standardize API v1 response envelope** | High | Medium | Use `success_response`/`error_response` in api_v1_* routes; document contract. |
| 5 | **Recurring invoices: service + repository** | Medium–High | Medium | Add `RecurringInvoiceRepository` and `RecurringInvoiceService`; move list/create/edit/delete and generate from routes. |
| 6 | **Invoices route thinning (incremental)** | High | High | Move one invoice handler at a time into `InvoiceService` using existing `InvoiceRepository`; add tests per batch. |
| 7 | **Issues: shared "accessible projects/clients" helper** | Medium | Low | Add repository or scope helper; use in all four places in `app/routes/issues.py`. |
| 8 | **API v1 validation and api_responses** | Medium | Low | Use existing schemas + `handle_validation_error` and `success_response`/`error_response` in api_v1_* modules. |
| 9 | **Gantt: extract data and progress to service** | Medium | Low | Add `GanttService` for `get_gantt_data` and progress calculation; route only delegates. |
| 10 | **Precompute task counts and budget in views** | Medium | Low | In tasks/project routes, compute task_counts and budget fields; pass to templates. |

---

## Refactor progress

| # | Target | Status |
|---|--------|--------|
| 1 | Centralize "user's distinct project IDs" | Done |
| 2 | RecurringInvoiceService.generate_invoice | Done |
| 3 | Thin reports routes | Done |
| 4 | Standardize API v1 response envelope | Done (documented) |
| 5 | Recurring invoices service + repository | Done |
| 6 | Invoices incremental | Done (get_unbilled_data_for_invoice) |
| 7 | Issues accessible IDs helper | Done |
| 8 | API v1 validation and api_responses | Done (api_v1_projects) |
| 9 | Gantt service | Done |
| 10 | Precompute task counts and budget in views | Done |

*(Update status to Done as refactors are completed.)*
