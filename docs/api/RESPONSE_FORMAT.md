# API Response Format

## Standard envelope (errors)

All API v1 error responses use a consistent shape from `app.utils.api_responses`:

- **Error response**: `{ "success": false, "error": "<error_code>", "message": "<message>", "errors"?: {...}, "details"?: {...} }`
- **Validation errors**: `error_code` is `"validation_error"`; `errors` contains field-specific messages.
- **Common error codes**: `not_found`, `forbidden`, `unauthorized`, `validation_error`, `error`.

HTTP status codes: 400 (bad request/validation), 401 (unauthorized), 403 (forbidden), 404 (not found), 409 (conflict), 422 (unprocessable), 500 (server error).

## Success responses

- **Preferred (standard envelope)**: `{ "success": true, "data": <payload>, "message"?: "<message>", "meta"?: {...} }`
- **Legacy (resource-keyed)**: Many list/get endpoints return `{ "projects": [...] }`, `{ "project": {...} }`, `{ "invoices": [...], "pagination": {...} }` without a top-level `success` or `data` wrapper. This is kept for backward compatibility.
- New endpoints should use `success_response(data=...)` so the payload is under `data` and `success: true` is set.

## Pagination

When using `paginated_response()`, the response is `{ "success": true, "data": <items>, "meta": { "pagination": { "page", "per_page", "total", "pages", ... } } }`. Some list endpoints still return `{ "<resource>": [...], "pagination": {...} }` for compatibility.
