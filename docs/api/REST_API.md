# TimeTracker REST API Documentation

## Overview

The TimeTracker REST API provides programmatic access to all time tracking, project management, and reporting features. This API is designed for developers who want to integrate TimeTracker with other tools or build custom applications.

**Integrations should use `/api/v1` only** (this document). The web application also exposes same-origin session JSON under **`/api/*`** (for example search and timer helpers used by the browser). Those routes are not the stable integration surface; use tokens and `/api/v1` for scripts, mobile, and desktop clients.

### For maintainers

Ship new HTTP capabilities under **`/api/v1`** first, with OpenAPI updates in `app/routes/api_docs.py`. Add or change **`/api/*`** only for logged-in UI needs or short-lived shims; reuse services from `app/services/` rather than duplicating logic.

## Base URL

```
https://your-domain.com/api/v1
```

## Authentication

All API endpoints require authentication using API tokens. API tokens are managed by administrators through the admin dashboard.

### Creating API Tokens

1. Log in as an administrator
2. Navigate to **Admin > Security & Access > Api-tokens** (`/admin/api-tokens`)
3. Click **Create Token**
4. Fill in the required information:
   - **Name**: A descriptive name for the token
   - **Description**: Optional description
   - **User**: The user this token will authenticate as
   - **Scopes**: Select the permissions this token should have
   - **Expires In**: Optional expiration period in days

5. Click **Create Token**
6. **Important**: Copy the generated token immediately - you won't be able to see it again!

### Using API Tokens

Include your API token in every request using one of these methods:

#### Method 1: Bearer Token (Recommended)

```bash
curl -H "Authorization: Bearer YOUR_API_TOKEN" \
     https://your-domain.com/api/v1/projects
```

#### Method 2: API Key Header

```bash
curl -H "X-API-Key: YOUR_API_TOKEN" \
     https://your-domain.com/api/v1/projects
```

### Token Format

API tokens follow the format: `tt_<32_random_characters>`

Example: `tt_abc123def456ghi789jkl012mno345pq`

### Rate limiting

Authenticated API requests are counted **per API token** using sliding minute and hour windows. Defaults are **100 requests/minute** and **1000/hour** unless overridden in configuration.

- **`API_TOKEN_RATE_LIMIT_PER_MINUTE`** — max requests per token per minute (default `100`).
- **`API_TOKEN_RATE_LIMIT_PER_HOUR`** — max requests per token per hour (default `1000`).

When [Redis](https://redis.io/) is available (`REDIS_URL` and Redis enabled in app config), limits are shared across all app workers. Otherwise a process-local fallback is used (fine for single-worker development; use Redis in production with multiple workers).

### Idempotent time entry creation

For safe retries (mobile offline sync, webhooks, automation), send a unique **`Idempotency-Key`** header (max 128 characters) on **`POST /api/v1/time-entries`**. The server stores the response for that key for **24 hours** (per token). Repeating the same key returns the **same JSON body and HTTP status** without creating a duplicate entry.

## Scopes

API tokens use scopes to control access to resources. When creating a token, select the appropriate scopes:

| Scope | Description |
|-------|-------------|
| `read:projects` | View projects |
| `write:projects` | Create and update projects |
| `read:time_entries` | View time entries |
| `write:time_entries` | Create and update time entries |
| `read:tasks` | View tasks |
| `write:tasks` | Create and update tasks |
| `read:clients` | View clients |
| `write:clients` | Create and update clients |
| `read:quotes` | View quotes |
| `write:quotes` | Create and update quotes |
| `read:reports` | View reports and analytics |
| `read:users` | View user information |
| `admin:all` | Full administrative access (use with caution) |

**Note**: For most integrations, you'll want both `read` and `write` scopes for the resources you're working with.

## Pagination

List endpoints support pagination to handle large datasets efficiently. For performance and benchmark targets, see [PERFORMANCE.md](../PERFORMANCE.md).

### Query Parameters

- `page` - Page number (default: 1)
- `per_page` - Items per page (default: 50, max: 100)

### Response Format

List responses use a **resource-named key** (e.g. `time_entries`, `projects`, `clients`) plus a top-level `pagination` object:

```json
{
  "time_entries": [...],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 150,
    "pages": 3,
    "has_next": true,
    "has_prev": false,
    "next_page": 2,
    "prev_page": null
  }
}
```

## Date/Time Format

All timestamps use ISO 8601 format:

- **Date**: `YYYY-MM-DD` (e.g., `2024-01-15`)
- **DateTime**: `YYYY-MM-DDTHH:MM:SS` or `YYYY-MM-DDTHH:MM:SSZ` (e.g., `2024-01-15T14:30:00Z`)

## Error Handling

### HTTP Status Codes

- `200 OK` - Request successful
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid input
- `401 Unauthorized` - Authentication required or invalid token
- `403 Forbidden` - Insufficient permissions (scope issue)
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

### Error Response Format

All error responses (4xx/5xx) include at least `error` (user-facing message) and `message`. Optional `error_code` (e.g. `unauthorized`, `forbidden`, `not_found`, `validation_error`) allows machine-readable handling. Validation errors include an `errors` object with field-level messages.

Example (401):
```json
{
  "error": "Invalid token",
  "message": "The provided API token is invalid or expired",
  "error_code": "unauthorized"
}
```

For scope errors (403):
```json
{
  "error": "Insufficient permissions",
  "message": "This endpoint requires the 'write:projects' scope",
  "error_code": "forbidden",
  "required_scope": "write:projects",
  "available_scopes": ["read:projects", "read:time_entries"]
}
```

For validation errors (400):
```json
{
  "error": "Validation failed",
  "message": "Validation failed",
  "error_code": "validation_error",
  "errors": { "name": ["Name is required"], "project_id": ["project_id is required"] }
}
```

## API Endpoints

### System

#### Get API Information
```
GET /api/v1/info
```

Returns API version and available endpoints. No authentication required.

`setup_required` is a boolean: when `true`, the installation’s initial web setup is not complete; finish setup in the browser. Desktop and mobile apps use this (and JSON shape) to avoid treating arbitrary HTTP 200 pages as TimeTracker. During that phase, `GET /api/v1/info`, `GET /api/v1/health`, and `POST /api/v1/auth/login` are not redirected to the HTML setup wizard so clients still receive JSON.

**Response:**
```json
{
  "api_version": "v1",
  "app_version": "1.0.0",
  "setup_required": false,
  "documentation_url": "/api/docs",
  "endpoints": {
    "projects": "/api/v1/projects",
    "time_entries": "/api/v1/time-entries",
    "tasks": "/api/v1/tasks",
    "clients": "/api/v1/clients"
  }
}
```

#### Health Check
```
GET /api/v1/health
```

Check if the API is operational. No authentication required.

### Admin version check (web JSON under `/api`)

These routes live on the **legacy session JSON blueprint** (same prefix style as `/api/health` in the app). They are **admin-only** (`User.is_admin`, including RBAC admin roles).

**Authentication:** browser **session cookie** (same-origin `fetch` after login) **or** an **API token** (`Authorization: Bearer tt_…` or `X-API-Key`). No dedicated scope is required; the server checks that the authenticated user is an administrator.

#### Check installed version against latest GitHub release

```
GET /api/version/check
```

Compares the running instance version to the latest published release on GitHub (see [Version management — admin update notification](../admin/deployment/VERSION_MANAGEMENT.md#admin-github-update-notification) for configuration and caching). Returns `update_available: false` when the current install is not a comparable semantic version (for example some `dev-*` tags), when GitHub cannot be reached and no stale cache exists, or when the user has dismissed this release version.

**Responses:** `401` if unauthenticated, `403` if not admin.

**Example (Bearer):**

```bash
curl -s -H "Authorization: Bearer YOUR_API_TOKEN" \
     https://your-domain.com/api/version/check
```

**Response (200):**

```json
{
  "update_available": true,
  "current_version": "4.0.0",
  "latest_version": "4.1.0",
  "release_notes": "…",
  "published_at": "2026-04-01T10:00:00Z",
  "release_url": "https://github.com/DRYTRIX/TimeTracker/releases/tag/v4.1.0"
}
```

#### Dismiss update prompt for a release version

```
POST /api/version/dismiss
```

**Body (JSON):** `{ "latest_version": "4.1.0" }` (with or without a leading `v`; stored normalized).

Persists `dismissed_release_version` for the current user so `GET /api/version/check` returns `update_available: false` until a newer release appears. Returns `{ "ok": true }` on success, `400` if `latest_version` is missing or not a valid semantic version string.

The web UI also mirrors dismissal in `localStorage` (`tt_dismissed_release_version`) as a client-side fallback; the database remains authoritative for `update_available`.

### Dashboard productivity (web JSON under `/api`)

These routes are used by the **web dashboard** after login. They live on the same legacy JSON blueprint as `/api/health` (not under `/api/v1`). **Authentication:** browser **session cookie** (`@login_required`); unauthenticated requests receive **401**.

#### Value dashboard aggregates

```
GET /api/stats/value-dashboard
```

Returns productivity aggregates for the **current user** only (completed time entries: `end_time` is set). Used by the main dashboard “Value insights” widget.

**Caching:** responses may be cached for up to **10 minutes** per user when Redis is available (`REDIS_URL` and working connection). If Redis is unavailable, each request recomputes from the database.

**Response (200):**

```json
{
  "total_hours": 132.5,
  "entries_count": 248,
  "active_days": 18,
  "avg_session_length": 1.4,
  "most_productive_day": "Tuesday",
  "this_week_hours": 24.5,
  "this_month_hours": 110.2,
  "last_7_days": [
    { "date": "2026-04-09", "hours": 2.5 },
    { "date": "2026-04-10", "hours": 0.0 }
  ],
  "estimated_value_tracked": 1234.56,
  "estimated_value_currency": "EUR"
}
```

- **`most_productive_day`:** English weekday name (`Sunday`–`Saturday`) with the highest total tracked time across all history, or **`null`** when there is no qualifying data.
- **`last_7_days`:** seven objects in chronological order for the last seven **local** calendar days (app timezone), including days with **0** hours.
- **`estimated_value_tracked`:** `null` when the estimated billable total is zero or no rate applies; otherwise `hours ×` resolved rate using **`COALESCE(project.hourly_rate, entry client default, project client default)`** (see server implementation in `StatsService`). **`estimated_value_currency`** comes from **Settings → currency** with application default fallback.

#### This week vs last week (hours by day)

```
GET /api/reports/week-comparison
```

Returns a **partial calendar week** (Monday 00:00 local time through **now**) compared with the **same weekdays** in the previous week, for the **current user** only. Completed entries only (`end_time` is set). The week definition matches the main dashboard “Week’s hours” aggregate (`AnalyticsService.get_dashboard_stats`).

**Response (200):**

```json
{
  "current_week": {
    "total_hours": 18.5,
    "by_day": [
      { "day": "2026-04-20", "hours": 6.0 },
      { "day": "2026-04-21", "hours": 4.25 }
    ]
  },
  "last_week": {
    "total_hours": 22.0,
    "by_day": [
      { "day": "2026-04-13", "hours": 5.0 },
      { "day": "2026-04-14", "hours": 7.5 }
    ]
  },
  "change_percent": -15.9
}
```

- **`by_day`:** dense list from week Monday through the comparison end date (this week through today; last week through the parallel weekday). Each **`day`** is an ISO date `YYYY-MM-DD`; **`hours`** is a float (including `0.0` for days with no entries).
- **`change_percent`:** percent change of **`current_week.total_hours`** vs **`last_week.total_hours`**, rounded to one decimal. **`null`** when last week’s total is zero (avoid division by zero).

The main dashboard renders this as a grouped bar chart (Chart.js) with a short summary line; data is loaded by `app/static/dashboard-enhancements.js` on dashboard refresh.

#### Personal productivity stats

```
GET /api/productivity/stats
```

Returns streaks, focus metrics, daily breakdown, project mix, activity heatmap, and insight strings for the **current user** only. Powers the **My productivity** page (`/dashboard/productivity`). See [docs/features/PRODUCTIVITY_DASHBOARD.md](../features/PRODUCTIVITY_DASHBOARD.md).

**Query parameters:**

- `period` (optional, int) — days for focus and project breakdown (default **30**, max **90**). Daily breakdown and heatmap use fixed windows (14 and 84 days).

**Caching:** up to **5 minutes** per user and `period` via `app.utils.cache.get_cache()` when available. Skipped when the user has an **active timer** so today/week stats stay current.

**Response (200):** `{ "ok": true, "period": 30, "summary": {...}, "daily_breakdown": [...], "streak": {...}, "focus": {...}, "projects": [...], "heatmap": [...], "insights": [...] }`

**Errors:** `{ "ok": false, "error": "..." }` with HTTP **500** on server failure.

#### Project forecast (web JSON)

```
GET /api/projects/<project_id>/forecast
```

Deterministic velocity, budget, timeline, and task metrics for a project the user can access. Optional AI narrative when the AI helper is enabled.

**Query parameters:**

- `ai` — when truthy (`1`, `true`, `yes`, `on`), include LLM-generated narrative, risks, and recommendations (requires AI helper enabled).
- `refresh` — when truthy, bypass the in-process cache for this project.

**Caching:** in-memory per process, **10 minutes** per project and mode (`deterministic` vs `ai`), unless `refresh=true`.

**Response (200):** `{ "ok": true, "forecast": {...}, "ai": {...} }` when `ai=true` (`ai` may report `ok: false` with `error_code` while still returning `forecast`).

See [docs/BUDGET_ALERTS_AND_FORECASTING.md](../BUDGET_ALERTS_AND_FORECASTING.md).

#### AI time entry suggestions (web JSON)

```
GET /api/ai/suggest
```

Returns up to five suggested time entries (recent project/task pairs with last notes/tags). Deterministic suggestions always; when `rich=1` and the AI helper is enabled, may merge LLM suggestions.

**Query parameters:**

- `q` (optional) — filter by project name or notes substring.
- `rich` (optional) — request LLM-enhanced suggestions when AI is enabled.

**Response (200):** `{ "ok": true, "suggestions": [{ "project_id", "project_name", "task_id", "task_name", "notes", "tags", "billable", "confidence", "source" }] }`

Used by the Start Timer modal and manual entry **Autofill** when `ai_enabled` is true in the template context.

### Search

#### Global Search
```
GET /api/v1/search
```

Perform a global search across projects, tasks, clients, and time entries.

**Required Scope:** `read:projects`

**Query Parameters:**
- `q` (required) - Search query (minimum 2 characters)
- `limit` (optional) - Maximum number of results per category (default: 10, max: 50)
- `types` (optional) - Comma-separated list of types to search: `project`, `task`, `client`, `entry`

**Example:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "https://your-domain.com/api/v1/search?q=website&limit=10"
```

**Search by specific types:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "https://your-domain.com/api/v1/search?q=website&types=project,task"
```

**Response (200):**
```json
{
  "results": [
    {
      "type": "project",
      "category": "project",
      "id": 1,
      "title": "Website Redesign",
      "description": "Complete website overhaul",
      "url": "/projects/1",
      "badge": "Project"
    },
    {
      "type": "task",
      "category": "task",
      "id": 5,
      "title": "Update homepage",
      "description": "Website Redesign",
      "url": "/tasks/5",
      "badge": "In Progress"
    }
  ],
  "query": "website",
  "count": 2,
  "partial": false,
  "errors": {}
}
```

**Partial results and per-domain errors**

Search runs independently for **projects**, **tasks**, **clients**, and **time entries** (see `app/services/global_search_service.py`). If one domain hits a database error (`SQLAlchemyError`), that domain is skipped, the others still return hits, and the response includes:

- **`partial`:** `true` when any domain failed; otherwise `false`.
- **`errors`:** Object whose keys are `projects`, `tasks`, `clients`, or `entries` (only keys for failed domains are present), each mapping to a short error string. Intended for observability and UI messaging, not as a stable API error code.

**Search Behavior:**
- **Projects**: Searches in name and description (active projects only)
- **Tasks**: Searches in name and description (tasks from active projects only)
- **Clients**: Searches in name, email, and company
- **Time Entries**: Searches in notes and tags (non-admin users see only their own entries)

**Error Responses:**
- `400 Bad Request` - Query is too short (less than 2 characters). Body includes `error`, `results` (empty array), `partial: false`, and `errors: {}`.
- `401 Unauthorized` - Missing or invalid API token
- `403 Forbidden` - Token lacks `read:projects` scope

**Note:** The legacy endpoint **`GET /api/search`** (session cookie, Flask-Login) uses the same search logic and the same **`results` / `query` / `count` / `partial` / `errors`** shape. For queries shorter than two characters it returns **200** with empty `results` and `partial: false`. Overlapping session routes may return **`X-API-Deprecated: true`** and a **`Link`** header pointing at this v1 path; integrations should call **`GET /api/v1/search`** only.

### Projects

#### List Projects
```
GET /api/v1/projects
```

**Required Scope:** `read:projects`

**Query Parameters:**
- `status` - Filter by status (`active`, `archived`, `on_hold`)
- `client_id` - Filter by client ID
- `page` - Page number
- `per_page` - Items per page

**Example:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "https://your-domain.com/api/v1/projects?status=active&per_page=20"
```

**Response:**
```json
{
  "projects": [
    {
      "id": 1,
      "name": "Website Redesign",
      "description": "Complete website overhaul",
      "client_id": 5,
      "hourly_rate": 75.00,
      "estimated_hours": 120,
      "status": "active",
      "created_at": "2024-01-01T10:00:00Z"
    }
  ],
  "pagination": {...}
}
```

#### Get Project
```
GET /api/v1/projects/{project_id}
```

**Required Scope:** `read:projects`

#### Create Project
```
POST /api/v1/projects
```

**Required Scope:** `write:projects`

**Request Body:**
```json
{
  "name": "New Project",
  "description": "Project description",
  "client_id": 5,
  "hourly_rate": 75.00,
  "estimated_hours": 100,
  "status": "active"
}
```

#### Update Project
```
PUT /api/v1/projects/{project_id}
```

**Required Scope:** `write:projects`

#### Archive Project
```
DELETE /api/v1/projects/{project_id}
```

**Required Scope:** `write:projects`

Note: This archives the project rather than permanently deleting it.

### Time Entries

#### List Time Entries
```
GET /api/v1/time-entries
```

**Required Scope:** `read:time_entries`

**Query Parameters:**
- `project_id` - Filter by project
- `user_id` - Filter by user (admin only)
- `start_date` - Filter by start date (ISO format)
- `end_date` - Filter by end date (ISO format)
- `billable` - Filter by billable status (`true` or `false`)
- `include_active` - Include active timers (`true` or `false`)
- `page` - Page number
- `per_page` - Items per page

**Example:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "https://your-domain.com/api/v1/time-entries?project_id=1&start_date=2024-01-01"
```

#### Create Time Entry
```
POST /api/v1/time-entries
```

**Required Scope:** `write:time_entries`

**Request Body:**
```json
{
  "project_id": 1,
  "task_id": 5,
  "start_time": "2024-01-15T09:00:00Z",
  "end_time": "2024-01-15T17:00:00Z",
  "notes": "Worked on feature X",
  "tags": "development,frontend",
  "billable": true
}
```

**Note:** `end_time` is optional. Omit it to create an active timer.

Optional header: **`Idempotency-Key`** — see [Idempotent time entry creation](#idempotent-time-entry-creation) above.

#### Import time entries (CSV)

```
POST /api/v1/time-entries/import-csv
```

**Required Scope:** `write:time_entries`

Accepts a CSV file (same column expectations as the web Import/Export flow) either as:

- **Multipart form**: field name `file`, or  
- **JSON body**: `{ "csv": "..." }` or `{ "data": "..." }`, or  
- **Raw body**: CSV text with `Content-Type: text/csv` (or similar).

Returns a JSON summary (counts, errors) and an appropriate HTTP status.

#### Bulk actions on time entries

```
POST /api/v1/time-entries/bulk
```

**Required Scope:** `write:time_entries`

**Request body (JSON):**

```json
{
  "entry_ids": [1, 2, 3],
  "action": "delete",
  "value": null
}
```

**`action`** (required): one of `delete`, `set_billable`, `set_paid`, `add_tag`, `remove_tag`.  
**`value`**: required for tag actions (string tag); for `set_billable` / `set_paid`, pass a boolean.  
Active (running) entries are skipped for non-delete actions; delete skips active entries.

Same access rules as the web UI: non-admins may only affect their own entries.

#### Update Time Entry
```
PUT /api/v1/time-entries/{entry_id}
```

**Required Scope:** `write:time_entries`

#### Delete Time Entry
```
DELETE /api/v1/time-entries/{entry_id}
```

**Required Scope:** `write:time_entries`

### Timer Control

#### Get Timer Status
```
GET /api/v1/timer/status
```

**Required Scope:** `read:time_entries`

Returns the current active timer for the authenticated user.

#### Start Timer
```
POST /api/v1/timer/start
```

**Required Scope:** `write:time_entries`

**Request Body:**
```json
{
  "project_id": 1,
  "task_id": 5
}
```

**Responses:**
- **`201 Created`** — Timer started; JSON includes `message` and `timer` (time entry fields).
- **`409 Conflict`** — **Allow only one active timer per user** is enabled in **System Settings** (`single_active_timer`) and the user already has a running timer. Response uses the standard error shape with `error_code` set to `timer_already_running`.
- **`400 Bad Request`** — Validation or other errors (e.g. invalid project, inactive project).

Enforcement uses the persisted **Settings** row, not the `SINGLE_ACTIVE_TIMER` env var alone (the env var seeds the setting on first install).

#### Stop Timer
```
POST /api/v1/timer/stop
```

**Required Scope:** `write:time_entries`

Stops the active timer for the authenticated user.

### Tasks

#### List Tasks
```
GET /api/v1/tasks
```

**Required Scope:** `read:tasks`

**Query Parameters:**
- `project_id` - Filter by project
- `status` - Filter by status
- `page` - Page number
- `per_page` - Items per page

#### Create Task
```
POST /api/v1/tasks
```

**Required Scope:** `write:tasks`

**Request Body:**
```json
{
  "name": "Implement login feature",
  "description": "Add user authentication",
  "project_id": 1,
  "status": "todo",
  "priority": 1
}
```

### Clients

#### List Clients
```
GET /api/v1/clients
```

**Required Scope:** `read:clients`

#### Create Client
```
POST /api/v1/clients
```

**Required Scope:** `write:clients`

**Request Body:**
```json
{
  "name": "Acme Corp",
  "email": "contact@acme.com",
  "company": "Acme Corporation",
  "phone": "+1-555-0123"
}
```

### Quotes

#### List Quotes
```
GET /api/v1/quotes
```

**Required Scope:** `read:quotes`

#### Get Quote
```
GET /api/v1/quotes/{quote_id}
```

**Required Scope:** `read:quotes`

#### Create Quote
```
POST /api/v1/quotes
```

**Required Scope:** `write:quotes`

**Request Body (example):**
```json
{
  "client_id": 1,
  "title": "Website maintenance retainer",
  "description": "Monthly maintenance and support",
  "tax_rate": 21.0,
  "currency_code": "EUR"
}
```

#### Update Quote
```
PUT /api/v1/quotes/{quote_id}
```

**Required Scope:** `write:quotes`

#### Delete Quote
```
DELETE /api/v1/quotes/{quote_id}
```

**Required Scope:** `write:quotes`

### Inventory

Inventory endpoints require the **inventory module** to be enabled (Admin settings). They use `read:projects` and `write:projects` scopes.

#### List Transfers
```
GET /api/v1/inventory/transfers
```

**Required Scope:** `read:projects`

**Query Parameters:**
- `date_from` - Filter transfers on or after this date (YYYY-MM-DD)
- `date_to` - Filter transfers on or before this date (YYYY-MM-DD)
- `page` - Page number
- `per_page` - Items per page (max 100)

**Response:** `transfers` (array of transfer objects with `reference_id`, `moved_at`, `stock_item_id`, `from_warehouse_id`, `to_warehouse_id`, `quantity`, `notes`, `movement_ids`) and `pagination`.

#### Create Transfer
```
POST /api/v1/inventory/transfers
```

**Required Scope:** `write:projects`

**Request Body:**
```json
{
  "stock_item_id": 1,
  "from_warehouse_id": 2,
  "to_warehouse_id": 3,
  "quantity": 10,
  "notes": "Optional notes"
}
```

**Response:** `201 Created` with `reference_id`, `transfers` (pair of movements), and success message.

#### Get Transfer by Reference ID
```
GET /api/v1/inventory/transfers/<reference_id>
```

**Required Scope:** `read:projects`

Returns a single transfer (the pair of out/in movements) or `404` if not found.

#### Inventory Reports

**Required Scope:** `read:projects` for all report endpoints.

- **Valuation:** `GET /api/v1/inventory/reports/valuation`  
  Query: `warehouse_id`, `category`, `currency_code`. Returns `total_value`, `by_warehouse`, `by_category`, `item_details`.

- **Movement History:** `GET /api/v1/inventory/reports/movement-history`  
  Query: `date_from`, `date_to`, `stock_item_id`, `warehouse_id`, `movement_type`, `page`, `per_page`. Returns `movements` and optional `pagination`.

- **Turnover:** `GET /api/v1/inventory/reports/turnover`  
  Query: `start_date`, `end_date`, `item_id`. Returns `start_date`, `end_date`, `items` (turnover metrics per item).

- **Low Stock:** `GET /api/v1/inventory/reports/low-stock`  
  Query: `warehouse_id` (optional). Returns `items` (entries below reorder point with `quantity_on_hand`, `reorder_point`, `shortfall`, etc.).

### Reports

#### Get Summary Report
```
GET /api/v1/reports/summary
```

**Required Scope:** `read:reports`

**Query Parameters:**
- `start_date` - Start date (ISO format)
- `end_date` - End date (ISO format)
- `project_id` - Filter by project
- `user_id` - Filter by user (admin only)

**Response:**
```json
{
  "summary": {
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-01-31T23:59:59Z",
    "total_hours": 160.5,
    "billable_hours": 145.0,
    "total_entries": 85,
    "by_project": [
      {
        "project_id": 1,
        "project_name": "Website Redesign",
        "hours": 85.5,
        "entries": 45
      }
    ]
  }
}
```

### Users

#### Get Current User
```
GET /api/v1/users/me
```

**Required Scope:** `read:users`

Returns information about the authenticated user.

### Personal integration connectors

Endpoints for the per-user **GitHub**, **Google Calendar**, and **Slack**
connectors (see [docs/integrations/README.md](../integrations/README.md)).
All `config`/`status`/`test`/`sync` routes are session-authenticated
(`@login_required`); the two webhook receivers are unauthenticated but
verify a provider signature on every request.

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `POST` | `/api/integrations/github/webhook`     | HMAC-SHA256 (`X-Hub-Signature-256`) | Receives GitHub `issues` / `ping` events. |
| `POST` | `/api/integrations/github/sync`        | session, admin | One-shot pull of open issues. |
| `POST` | `/api/integrations/github/config`      | session | Save the GitHub card. |
| `POST` | `/api/integrations/github/test`        | session | Verify the personal access token. |
| `GET`  | `/api/integrations/github/status`      | session | Current config snapshot (no secrets). |
| `GET`  | `/integrations/google/connect`         | session | Start the Google OAuth dance. |
| `GET`  | `/integrations/google/callback`        | session | OAuth callback — stores tokens. |
| `POST` | `/integrations/google/disconnect`      | session | Revokes the token and clears config. |
| `POST` | `/api/integrations/google/sync`        | session | Runs `import`/`export`/`both`. |
| `GET`  | `/api/integrations/google/status`      | session | Linked email, calendar id, last sync. |
| `POST` | `/api/integrations/slack/events`       | HMAC-SHA256 (`X-Slack-Signature`) | Slack URL verification + `/tt` slash commands. |
| `POST` | `/api/integrations/slack/config`       | session | Save the Slack card. |
| `POST` | `/api/integrations/slack/test`         | session | Sends a test message to the channel. |
| `GET`  | `/api/integrations/slack/status`       | session | Current config snapshot (no secrets). |

These endpoints sit under the regular Flask cookie session (not the
`Bearer` token flow used by `/api/v1/...`) because they back the
integrations settings UI, which is browser-based.

## Interactive API Documentation

For interactive API documentation and testing, visit:

```
https://your-domain.com/api/docs
```

This Swagger UI interface allows you to:
- Browse all available endpoints
- Test API calls directly from your browser
- View detailed request/response schemas
- Try out different parameters

## Code Examples

### Python

```python
import requests

API_TOKEN = "tt_your_token_here"
BASE_URL = "https://your-domain.com/api/v1"

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

# List projects
response = requests.get(f"{BASE_URL}/projects", headers=headers)
projects = response.json()

# Create time entry
time_entry = {
    "project_id": 1,
    "start_time": "2024-01-15T09:00:00Z",
    "end_time": "2024-01-15T17:00:00Z",
    "notes": "Development work",
    "billable": True
}
response = requests.post(f"{BASE_URL}/time-entries", json=time_entry, headers=headers)
```

### JavaScript/Node.js

```javascript
const axios = require('axios');

const API_TOKEN = 'tt_your_token_here';
const BASE_URL = 'https://your-domain.com/api/v1';

const headers = {
  'Authorization': `Bearer ${API_TOKEN}`,
  'Content-Type': 'application/json'
};

// List projects
axios.get(`${BASE_URL}/projects`, { headers })
  .then(response => console.log(response.data))
  .catch(error => console.error(error));

// Start timer
axios.post(`${BASE_URL}/timer/start`, 
  { project_id: 1, task_id: 5 }, 
  { headers }
)
  .then(response => console.log('Timer started:', response.data))
  .catch(error => console.error(error));
```

### cURL

```bash
# List projects
curl -H "Authorization: Bearer tt_your_token_here" \
     https://your-domain.com/api/v1/projects

# Create time entry
curl -X POST \
     -H "Authorization: Bearer tt_your_token_here" \
     -H "Content-Type: application/json" \
     -d '{"project_id":1,"start_time":"2024-01-15T09:00:00Z","end_time":"2024-01-15T17:00:00Z"}' \
     https://your-domain.com/api/v1/time-entries
```

## Best Practices

### Security

1. **Store tokens securely**: Never commit tokens to version control
2. **Use environment variables**: Store tokens in environment variables
3. **Rotate tokens regularly**: Create new tokens periodically and delete old ones
4. **Use minimal scopes**: Only grant the permissions needed
5. **Set expiration dates**: Configure tokens to expire when appropriate

### Performance

1. **Use pagination**: Don't fetch all records at once
2. **Filter results**: Use query parameters to reduce data transfer
3. **Cache responses**: Cache data that doesn't change frequently
4. **Batch operations**: Combine multiple operations when possible

### Error Handling

1. **Check status codes**: Always check HTTP status codes
2. **Handle rate limits**: Implement exponential backoff for rate limit errors
3. **Log errors**: Log API errors for debugging
4. **Validate input**: Validate data before sending to API

## Rate Limiting

The API implements rate limiting to ensure fair usage:

- **Per-token limits**: 100 requests per minute, 1000 requests per hour
- **Response headers**: Rate limit information is included in response headers
  - `X-RateLimit-Limit`: Maximum requests allowed
  - `X-RateLimit-Remaining`: Requests remaining in current window
  - `X-RateLimit-Reset`: Unix timestamp when the limit resets

When rate limited, you'll receive a `429 Too Many Requests` response.

## Webhook Support

Webhooks are supported for real-time notifications. You can receive notifications when time entries are created/updated, projects change status, tasks are completed, and timer events occur. See [Webhooks](../features/webhooks.md) for setup and event types.

## Support

For API support:
- **Documentation**: This guide and `/api/docs`
- **GitHub Issues**: Report bugs and request features
- **Community**: Join our community forum

## Changelog

### Version 1.0.0 (Current)
- Initial REST API release
- Full CRUD operations for projects, time entries, tasks, and clients
- Token-based authentication with scopes
- Comprehensive filtering and pagination
- Timer control endpoints
- Reporting endpoints
- Interactive Swagger documentation

