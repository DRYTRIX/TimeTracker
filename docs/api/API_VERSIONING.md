# API Versioning Strategy

## Overview

TimeTracker uses URL-based API versioning to ensure backward compatibility while allowing for API evolution.

## Version Structure

```
/api/v1/*  - Current stable API (v1)
/api/v2/*  - Future version (when breaking changes are needed)
```

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

1. **Deprecation Notice:** Deprecated endpoints return `X-API-Deprecated: true` header
2. **Deprecation Period:** Minimum 6 months before removal
3. **Migration Guide:** Documentation provided for migrating to new version
4. **Removal:** Deprecated endpoints removed only in major version bumps

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
├── api.py          # Legacy API (deprecated)
├── api_v1.py       # v1 API (current)
└── api/            # Future versioned structure
    └── v1/
        └── __init__.py
```

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

**Last Updated:** 2025-01-27  
**Current Version:** v1  
**Next Version:** v2 (when needed)

