# API Consistency Audit

This document records the API consistency audit performed for the TimeTracker backend, REST API, and native clients (desktop and mobile). It describes findings and the standardized contracts adopted.

## 1. Response shapes

### 1.1 Success responses

- **Helpers** in `app/utils/api_responses.py` define `success_response()` (returns `{ "success": true, "data"?, "message"?, "meta"? }`) and `paginated_response()` (items in `data`, pagination in `meta.pagination`).
- **Actual API** uses a different convention: list endpoints return **resource-named key + top-level pagination**, e.g. `{ "time_entries": [...], "pagination": {...} }`, `{ "projects": [...], "pagination": {...} }`. Single-resource responses use a **singular key**: `{ "time_entry": {...} }`, `{ "project": {...} }`, `{ "timer": {...} }`.
- **Contract (kept for compatibility)**: List = `{ "<resource_plural>": [...], "pagination": { page, per_page, total, pages, has_next, has_prev, next_page, prev_page } }`. Single = `{ "<resource_singular>": {...} }`. Created (201) = `{ "message"?, "<resource_singular>": {...} }` or similar. Clients depend on these keys; we do not switch to `data`/`meta`.

### 1.2 Error responses (standardized)

- **Contract**: All API v1 error responses (4xx/5xx) include:
  - `error` (string): user-facing message (backward compatible).
  - `message` (string): same or more detail.
  - `error_code` (string, optional): machine-readable code, e.g. `unauthorized`, `forbidden`, `not_found`, `validation_error`, `no_active_timer`.
  - `errors` (object, optional): field-level validation errors, e.g. `{ "field_name": ["message1", "message2"] }`.
  - For 403 scope errors: `required_scope`, `available_scopes` may also be present.

### 1.3 Validation errors

- **Contract**: Any 400 due to invalid input uses the same structure: `error_code: "validation_error"` and, when applicable, an `errors` object with field-level messages. Marshmallow validation uses `handle_validation_error()`; manual validation uses `validation_error_response()`.

## 2. Pagination

- **Contract**: List endpoints support query params `page` (default 1) and `per_page` (default 50, max 100). Response includes `"pagination": { "page", "per_page", "total", "pages", "has_next", "has_prev", "next_page", "prev_page" }`. The list key is resource-specific (e.g. `time_entries`, `projects`), not `items`.

## 3. Auth / token handling

- Token extraction (Bearer, Token, X-API-Key) and `@require_api_token(scope)` are consistent. Auth error responses include `error_code` (`unauthorized`, `forbidden`) for consistent machine-readable handling.

## 4. Date/time

- **Contract**: Dates and datetimes use ISO 8601. Request parsing accepts `YYYY-MM-DD` and `YYYY-MM-DDTHH:MM:SS` / `YYYY-MM-DDTHH:MM:SSZ`. Serialization format (e.g. UTC or server local) is documented in the REST API reference.

## 5. Sort / filter

- Filter query parameters are resource-specific and documented per endpoint. Optional `sort` / `order` conventions may be documented for list endpoints that support them.

## 6. References

- **REST API reference**: [REST_API.md](REST_API.md) — endpoints, request/response formats, pagination, errors.
- **OpenAPI**: `/api/openapi.json` and Swagger UI at `/api/docs` — aligned with this contract where updated.
