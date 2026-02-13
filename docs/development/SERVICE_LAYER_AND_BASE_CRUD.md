# Service Layer and Base CRUD Pattern

## Chosen pattern

TimeTracker uses a **domain service layer**: route handlers call service classes (e.g. `ProjectService`, `InvoiceService`, `TimeApprovalService`) that encapsulate business logic and data access. Routes are kept thin; validation, permissions, and orchestration live in services or in route-level decorators.

- **Services** live in `app/services/`. Each domain (projects, clients, time entries, invoices, approvals, etc.) has one or more service classes.
- **Repositories** exist for some domains (`app/repositories/`, e.g. `TimeEntryRepository`, `ProjectRepository`, `ClientRepository`, `TaskRepository`) and are used by services or routes to avoid N+1 queries and centralize queries.
- **Routes** use `db.session` and model queries where a dedicated service or repository is not yet introduced; new features and refactors should prefer the service (and optionally repository) pattern.

## BaseCRUDService

`app/services/base_crud_service.py` defines **BaseCRUDService**, a generic base class that provides standard CRUD (get_by_id, create, update, delete, list_all) with consistent `{ "success", "message", "data" / "error" }` result dicts.

- **Current use**: BaseCRUDService is **not** extended by any service today. Domain services implement their own methods and return shapes (e.g. `ProjectService.create()` returns a result dict used by the API).
- **When to use it**: Prefer BaseCRUDService when:
  - You introduce a **new** domain that has a **repository** with `get_by_id`, `create`, `update`, `delete`, and `query()`.
  - The resource is mostly simple CRUD with minimal extra logic.
- **When not to use it**: Existing domain services (projects, clients, invoices, time entries, etc.) have custom logic, validation, and return shapes. Migrating them to BaseCRUDService would require repository implementations and possible API response changes; it is optional and can be done incrementally.

## Summary

| Aspect              | Approach                                                                 |
|---------------------|--------------------------------------------------------------------------|
| New features        | Prefer service class + optional repository; use BaseCRUDService only if CRUD is simple and a repository exists. |
| Existing services   | Keep current pattern; no requirement to extend BaseCRUDService.          |
| Route layer         | Prefer calling services; direct `db.session` / model queries are acceptable where services are not yet used.   |
| API response shape  | Use `app.utils.api_responses` (e.g. `error_response`, `success_response`) for consistent JSON error/success format. |
