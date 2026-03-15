# TimeTracker Performance Optimizations

This document summarizes performance improvements applied to the TimeTracker Flask application, configuration options, follow-up index candidates, benchmark targets, and where async or background processing would help.

## Summary of Changes

| Area | Change | Rationale |
|------|--------|-----------|
| **Instrumentation** | Optional slow-request logging and query-count profiling via `PERF_LOG_SLOW_REQUESTS_MS` and `PERF_QUERY_PROFILE`. | Confirm assumptions and measure impact without production overhead by default. |
| **Task report** | Eager load tasks (project, assignee); single aggregation query for hours/count per task via `TimeEntryRepository.get_task_aggregates()`. Same for Excel export. | Eliminates N+1 (1 + N task queries + N time-entry queries). |
| **Admin dashboard** | Replaced two 30-iteration loops with two GROUP BY queries (user activity by date, daily hours by date). | Cuts ~60 queries to 2. |
| **Gantt** | Load all tasks for selected projects in one query; group by `project_id`. `calculate_project_progress` accepts optional `tasks` to avoid extra query. | One query instead of N per project. |
| **Time entries report** | Pagination (page/per_page, default 50, max 500); summary from COUNT and SUM aggregation. | Prevents unbounded load and timeouts on large date ranges. |
| **ReportingService.get_time_summary** | Use `count_for_date_range()` and `get_total_duration()` instead of loading all entries for count. | Avoids loading full result set to compute totals. |
| **Admin user edit** | Batch load clients: `Client.query.filter(Client.id.in_(assigned_client_ids)).all()`. | One query instead of N for subcontractor assigned clients. |
| **Dashboard last_timer_context** | `joinedload(TimeEntry.project)`, `joinedload(TimeEntry.client)` on the single “last entry” query. | Avoids two lazy loads when rendering. |
| **Caching** | Dashboard: cache `get_dashboard_stats` and `get_time_by_project_chart` per user (TTL 90s). Admin: cache chart data (TTL 10 min). `invalidate_dashboard_for_user()` clears stats, chart, and legacy key. | Reduces repeated DB work on hot paths. |
| **Team chat** | Batch load read receipts for message IDs; build dict and create only missing receipts. | Removes N+1 per message. |
| **Integrations list** | One query for all credentials for listed integration IDs; set of IDs for “has_credentials” check. | Removes N+1 per integration. |
| **Inventory** | Batch load `WarehouseStock` for reorder/low-stock items; group by `stock_item_id`. Use `joinedload(WarehouseStock.warehouse)` where warehouse is rendered. | Removes N+1 per item. |
| **AnalyticsService** | `get_dashboard_top_projects` and `get_time_by_project_chart` use DB GROUP BY + SUM instead of loading all time entries. | Scales with large entry counts. |

## Tradeoffs

- **Dashboard cache**: Stats and chart can be up to 90 seconds stale; invalidated on timer start/stop and time entry changes.
- **Admin chart cache**: Up to 10 minutes stale; no invalidation on time entry/project change (TTL only).
- **Time entries report**: Pagination adds `page` and `per_page` to the URL; exports still fetch full result set (consider a hard limit or background job for very large ranges).
- **Reports summary**: Not cached (return value includes ORM objects); dashboard and admin chart caches are the main wins.

## Configuration

| Env / config | Description |
|--------------|-------------|
| `PERF_LOG_SLOW_REQUESTS_MS` | Log one line when request duration exceeds this many milliseconds (0 = disabled). |
| `PERF_QUERY_PROFILE` | When true, track DB query count per request and include in slow-request logs. |

Instrumentation is in `app/utils/performance.py` and registered in `create_app()`.

## Follow-up: DB Index Candidates

Add via migrations after validating with `EXPLAIN ANALYZE` on real workloads:

- **time_entries**: `(user_id, start_time)`, `(project_id, start_time)`, `(task_id, end_time)`, `(start_time)` or `(start_time, end_time)` for range filters and admin 30-day charts. Consider partial index `WHERE end_time IS NOT NULL` for completed-entry-heavy queries.
- **payments**: `(payment_date, status)` for reporting and last-30-days stats.
- **activities**: `(user_id, created_at)` for activity feed; `(entity_type, action)` if filtered by type.
- **projects**: `(status)` for active lists; `(client_id, status)` for client-scoped lists.
- **tasks**: `(project_id, status)` for Gantt and task lists per project.

## Endpoints and Pages to Benchmark

- **Web**: `GET /`, `GET /dashboard`, `GET /reports`, `GET /reports/tasks`, `GET /reports/time-entries`, `GET /admin`, `GET /admin/dashboard`, `GET /gantt`, `GET /api/gantt/data` (with project_id and date range).
- **API**: `GET /api/v1/time-entries`, `GET /api/v1/clients`, `GET /api/entries`, `GET /api/activities`, and any dashboard/summary endpoints used by the UI.

Measure p50/p95 response time and, where possible, DB query count per request before and after optimizations. Use production-like data (e.g. 10k+ time entries, hundreds of projects/tasks).

## API Pagination Consistency

- List endpoints use `page` and `per_page` (default 50, max 100 in API v1 common). Response shape: resource key (e.g. `time_entries`) plus `pagination` with `page`, `per_page`, `total`, `pages`, `has_next`, `has_prev`, `next_page`, `prev_page`.
- Align any remaining list endpoints with `app/routes/api_v1_common.paginate_query()` and document defaults in OpenAPI and REST_API.md.

## Where Async or Background Processing Would Help

- **Heavy report exports**: Time entries (and similar) CSV/Excel/PDF with large date ranges. Offload to a background job (e.g. APScheduler or Celery), write file to storage or email link; return “report queued” or a poll endpoint. Reduces timeouts and keeps request workers free.
- **Scheduled reports**: Ensure generation runs in a worker/process that does not block the web app.
- **Precomputed rollups (optional)**: Daily/hourly rollup table for `time_entries` filled by a job; dashboard and admin charts could read from rollups at scale.
- **Cache warming**: Optional low-priority job that periodically hits dashboard or reports summary for active users.

## Tests

- **Task report**: `tests/test_reports_task_report.py` – correct hours/entries and repository aggregation.
- **Admin dashboard**: `tests/test_admin_dashboard_charts.py` – chart data present and 30-day series.
- **ReportingService**: `get_time_summary` uses count and duration only (no full fetch).
