# TimeTracker REST API

TimeTracker exposes a **REST API** for programmatic access to time tracking, projects, tasks, clients, reports, and more. The API is versioned under `/api/v1`, uses **token-based authentication**, and returns JSON.

## Overview

Use the API to integrate with external tools, build custom dashboards, or drive the mobile and desktop apps. All endpoints require authentication via an API token (Bearer or `X-API-Key` header) unless noted. Pagination, filtering, and error responses are described in the full reference.

## Getting an API Token

1. Log in as an administrator.
2. Go to **Admin → Security & Access → Api-tokens** (or `/admin/api-tokens`).
3. Click **Create Token**, set name, user, and **scopes** (read/write per resource).
4. Copy the token immediately; it is shown only once.

Token format: `tt_` followed by 32 random characters.

## Using the Token

Send the token on every request:

**Bearer (recommended):**

```bash
curl -H "Authorization: Bearer YOUR_API_TOKEN" \
     https://your-domain.com/api/v1/projects
```

**API key header:**

```bash
curl -H "X-API-Key: YOUR_API_TOKEN" \
     https://your-domain.com/api/v1/projects
```

## Main Resources

| Area | Endpoints (examples) | Description |
|------|----------------------|-------------|
| **Projects** | `/api/v1/projects` | List, create, get, update, delete projects |
| **Time entries** | `/api/v1/time-entries` | List, create, get, update, delete time entries; timer start/stop |
| **Tasks** | `/api/v1/tasks` | List, create, get, update, delete tasks |
| **Clients** | `/api/v1/clients` | List, create, get, update, delete clients |
| **Reports** | `/api/v1/reports` | Run reports and export data |
| **Deals & leads** | `/api/v1/deals`, `/api/v1/leads` | CRM deals and leads |
| **Contacts** | `/api/v1/clients/<id>/contacts` | Client contacts |
| **Search** | `/api/v1/search` | Global search across projects, tasks, clients |
| **Time approvals** | `/api/v1/time-entry-approvals` | Approve, reject, request approval for time entries |
| **Admin version check** | `/api/version/check`, `/api/version/dismiss` | Compare install to latest GitHub release; dismiss per version (admin only; session or API token; not under `/api/v1`) |
| **Dashboard (session)** | `/api/stats/value-dashboard`, `/api/productivity/stats`, `/api/projects/<id>/forecast`, `/api/ai/suggest`, … | JSON used by the logged-in web UI (session cookie); see [REST API reference](api/REST_API.md) for fields and caching |

Access is controlled by **scopes** (e.g. `read:projects`, `write:time_entries`) on **`/api/v1`** routes. Create a token with the scopes you need; see [API Token Scopes](api/API_TOKEN_SCOPES.md). The admin version endpoints do not require a specific scope but require an **administrator** user. Legacy **`/api/...`** dashboard JSON routes require a normal **logged-in session**, not API-token scopes.

## Quick Examples

**List projects:**

```bash
curl -H "Authorization: Bearer YOUR_API_TOKEN" \
     https://your-domain.com/api/v1/projects
```

**Create a time entry:**

```bash
curl -X POST -H "Authorization: Bearer YOUR_API_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"project_id": 1, "start_time": "2025-01-27T09:00:00", "end_time": "2025-01-27T17:00:00", "notes": "Work on feature"}' \
     https://your-domain.com/api/v1/time-entries
```

Replace `your-domain.com` with your TimeTracker host and `YOUR_API_TOKEN` with your token.

## Full Documentation

- **[REST API reference](api/REST_API.md)** — All endpoints, request/response formats, pagination, errors
- **[API Consistency Audit](api/API_CONSISTENCY_AUDIT.md)** — Response contracts, error format, pagination
- **[API Token Scopes](api/API_TOKEN_SCOPES.md)** — Scopes and permissions
- **[API Versioning](api/API_VERSIONING.md)** — Versioning policy and usage
