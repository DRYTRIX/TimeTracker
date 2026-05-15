# API Versioning Strategy

## Overview

TimeTracker uses URL-based API versioning to ensure backward compatibility while allowing for API evolution.

## Version Structure

```
/api/v1/*  - Current stable API (v1)
/api/v2/*  - Future version (when breaking changes are needed)
```

## Session JSON under `/api/*` vs REST under `/api/v1`

| Surface | Auth | Audience | Spec |
|--------|------|----------|------|
| **`/api/v1/*`** | API token (Bearer or `X-API-Key`), scopes | Integrations, mobile, desktop | OpenAPI at `/api/openapi.json`, UI at `/api/docs` |
| **`/api/*`** | Flask-Login **session** (browser cookie) | Logged-in web UI (`app/routes/api.py`) | Not fully documented in OpenAPI; may change with templates/JS |

**Hybrid (session or token):** `/api/version/check` and `/api/version/dismiss` accept either a logged-in admin session or a valid API token (see `app/routes/api.py`).

### Deprecated session routes (overlap with v1)

These **`/api/*`** routes have v1 successors. They remain for the web UI but may send **`X-API-Deprecated: true`** and **`Link: </api/v1/...>; rel="successor-version"`**:

- `GET /api/health` → `GET /api/v1/health`
- `GET /api/search` → `GET /api/v1/search` (same JSON shape, including `partial` and `errors` on degraded per-domain search; see [REST_API.md](REST_API.md#search))
- Timer: `GET /api/timer/status`, `POST /api/timer/start`, `POST /api/timer/stop`, `POST /api/timer/stop_at`, `POST /api/timer/resume` → `/api/v1/timer/*`
- Time entries: `GET|POST /api/entries`, `POST /api/entries/bulk`, `GET|PUT|DELETE /api/entry/<id>` → `/api/v1/time-entries` (and related)
- `GET /api/projects`, `GET /api/projects/<id>/tasks`, `GET /api/tasks` → `/api/v1/projects`, `/api/v1/tasks`
- `GET /api/activities` → `GET /api/v1/activities` (v1 is a simpler list; legacy adds filters/pagination)

### Session AI routes (web UI; partial v1 migration)

| Session route | Notes | v1 successor (planned) |
|---------------|--------|-------------------------|
| `GET /api/ai/context-preview` | Compact context for AI helper | `GET /api/v1/ai/context-preview` |
| `POST /api/ai/chat` | AI helper chat | `POST /api/v1/ai/chat` |
| `POST /api/ai/actions/confirm` | Confirm proposed AI actions | `POST /api/v1/ai/actions/confirm` |
| `GET /api/ai/suggest` | Time entry suggestions (`?q=`, `?rich=true`) | `GET /api/v1/ai/suggest` (deprecation header points here) |

`GET /api/ai/suggest` always returns deterministic suggestions from `AISuggestionService`; optional `rich=true` adds LLM suggestions when the helper is enabled. Failures in the LLM path do not fail the request.

### Internal / UI-only (no v1 equivalent yet)

Examples: `GET /api/notifications`, dashboard stats (`/api/dashboard/*`, `/api/stats*`, `/api/reports/week-comparison`), editor uploads, smart notifications dismiss, many calendar helpers. Treat as **internal** to the web app unless documented otherwise.

## Versioning Policy

### When to Create a New Version

Create a new API version (e.g., v2) when:
- **Breaking changes** are required:
  - Removing or renaming fields
  - Changing response structure
  - Changing authentication method
  - Changing required parameters
  - Changing error response format

### When NOT to Create a New Version

Do NOT create a new version for:
- Adding new endpoints (add to current version)
- Adding optional fields (backward compatible)
- Adding new response fields (backward compatible)
- Bug fixes (fix in current version)
- Performance improvements (no API change)

## Current Versions

### v1 (Current)

**Status:** Stable  
**Base URL:** `/api/v1`  
**Documentation:** See `app/routes/api_v1.py`

**Features:**
- Token-based authentication
- RESTful endpoints
- JSON responses
- Pagination support
- Filtering and sorting

**Endpoints:**
- `/api/v1/projects` - Project management
- `/api/v1/tasks` - Task management
- `/api/v1/time-entries` - Time entry management
- `/api/v1/invoices` - Invoice management
- `/api/v1/clients` - Client management
- And more...

## Version Negotiation

Clients specify API version via:
1. **URL path** (preferred): `/api/v1/projects`
2. **Accept header** (future): `Accept: application/vnd.timetracker.v1+json`
3. **Query parameter** (fallback): `/api/projects?version=1`

## Deprecation Policy

1. **Deprecation notice:** Deprecated **session** JSON routes (see table above) return **`X-API-Deprecated: true`** and optionally **`Link: <path>; rel="successor-version"`** pointing at the **`/api/v1`** equivalent.
2. **Deprecation period:** Minimum 6 months before removal (if removal is ever scheduled for a given route).
3. **Migration guide:** Prefer [REST API](REST_API.md) and OpenAPI for v1 behavior.
4. **Removal:** Deprecated endpoints removed only in coordinated major releases (v1 remains the default integration API).

## Migration Example

### v1 to v2 (Hypothetical)

**v1 Response:**
```json
{
  "id": 1,
  "name": "Project",
  "client": "Client Name"
}
```

**v2 Response (breaking change):**
```json
{
  "id": 1,
  "name": "Project",
  "client": {
    "id": 1,
    "name": "Client Name"
  }
}
```

**Migration:**
- v1 endpoint remains available
- v2 endpoint provides new structure
- Clients migrate at their own pace
- v1 deprecated but not removed

## Best Practices

1. **Always use versioned URLs** in client code
2. **Handle version negotiation** gracefully
3. **Monitor deprecation headers** in responses
4. **Plan migrations** well in advance
5. **Test against specific versions** in CI/CD

## Implementation

### Current Structure

```
app/routes/
├── api.py          # Session JSON for web UI (/api/*); overlapping routes may be deprecated toward v1
├── api_v1.py       # v1 REST API (current)
└── api/            # Future versioned structure
    └── v1/
        └── __init__.py
```

Shared **global search** for `GET /api/search` and `GET /api/v1/search` lives in `app/services/global_search_service.py`. **`X-API-Deprecated`** / **`Link`** headers for overlapping session routes are applied with `app/utils/api_deprecation.py`.

### Future Structure

```
app/routes/api/
├── __init__.py
├── v1/
│   ├── __init__.py
│   ├── projects.py
│   ├── tasks.py
│   └── invoices.py
└── v2/
    ├── __init__.py
    ├── projects.py
    └── ...
```

## Version Detection

```python
from flask import request

def get_api_version():
    """Get API version from request"""
    # Check URL path
    if request.path.startswith('/api/v1'):
        return 'v1'
    elif request.path.startswith('/api/v2'):
        return 'v2'
    
    # Check Accept header
    accept = request.headers.get('Accept', '')
    if 'vnd.timetracker.v1' in accept:
        return 'v1'
    elif 'vnd.timetracker.v2' in accept:
        return 'v2'
    
    # Default to v1
    return 'v1'
```

## Documentation

- **OpenAPI/Swagger:** Available at `/api/docs`
- **Version-specific docs:** `/api/v1/docs` (future)
- **Migration guides:** In `docs/api/migrations/`

---

**Last Updated:** 2026-04-16  
**Current Version:** v1  
**Next Version:** v2 (when needed)

