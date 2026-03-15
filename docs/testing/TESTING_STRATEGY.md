# TimeTracker Testing Strategy

This document defines the testing strategy for the TimeTracker project: goals, test pyramid, business-critical areas, layout, fixtures, quality gates, and anti-patterns. It complements the [CI/CD Testing Workflow Strategy](../cicd/TESTING_WORKFLOW_STRATEGY.md), which describes how tests run in pipelines.

## Goals

- **Fast feedback:** Smoke and unit tests run quickly; developers get results in minutes.
- **Regression protection:** Critical flows (auth, timer, time entries, scope, invoicing, reports) are covered so changes do not break existing behavior.
- **Confidence for refactors:** Clear structure, shared fixtures, and markers make it safe to reorganize or extend code.

## Test pyramid

- **Smoke:** Minimal set of critical-path tests (login, dashboard, key API). Run on every commit; must be fast and stable.
- **Unit:** Single component in isolation; mock external dependencies (DB, services) where appropriate. Fast and numerous.
- **Integration:** Multiple components together (app + DB + routes/services). Use real SQLite or PostgreSQL in CI. Cover cross-module workflows.
- **E2E:** Optional; full browser or API flows against a running app. Not required for every PR.

## Business-critical areas

Tests must cover:

| Area | What to test |
|------|--------------|
| **Auth** | Web login (GET/POST, success, wrong password, redirect); API token extraction, validation, scopes, IP whitelist. |
| **Timer** | Start/stop via web (POST /timer/start, /timer/stop) and API; single active timer; scope (user can only start timer for allowed project). |
| **Time entries** | CRUD and edit (API PATCH, web if applicable); linking to project/client/task; duration and billable. |
| **Project/client linking** | Project belongs to client; scope filter restricts visible projects/clients for subcontractors. |
| **Invoicing** | Create invoice from time entries; recurring invoices; list/detail; payments. |
| **Reports** | Time summary, project summary, week-in-review; **scoping** (subcontractor sees only allowed project data). |
| **API auth and scopes** | 401 without token; 403 with insufficient scope; correct payload (error_code, required_scope, available_scopes). |

## Test layout

- **Root:** Single `tests/conftest.py` for app, client, DB, users, projects, time entries, auth fixtures, and shared API token/client.
- **Grouping:** `test_models/`, `test_routes/`, `test_services/`, `test_utils/`, `test_repositories/`, `test_integration/` for clarity. Root-level `test_*.py` is allowed for legacy or cross-cutting tests.
- **Markers:** Use `smoke`, `unit`, `integration`, `api`, `routes`, `models`, `utils`, `security` consistently so CI can run subsets (e.g. `-m "unit and routes"`).

## Fixtures and factories

- **Conftest:** Prefer `app`, `client`, `user`, `admin_user`, `project`, `time_entry`, `authenticated_client`, `admin_authenticated_client`. Use shared `api_token` and `client_with_token` for API tests; avoid per-module duplicate app creation.
- **Factories (Factory Boy):** Use `factories.py` for User, Client, Project, TimeEntry, Invoice, ApiToken, etc., when building complex graphs. Keeps tests readable and avoids repetitive setup.
- **Anti-pattern:** Do not create a separate Flask app in a test file (e.g. custom `app`/`client` in `test_api_v1.py`) when conftest already provides one; migrate to conftest for consistency and shared fixtures.

## Quality gates

- **Pytest markers:** All tests should have at least one marker so CI jobs (smoke, unit, integration, api) include or exclude them predictably.
- **Coverage:** `--cov-fail-under` is applied only when running the **full** test suite (e.g. on PRs to main). Do not fail coverage on partial runs (e.g. `-m "unit and routes"`).
- **Lint/format:** black, isort, flake8 (and optionally pylint, bandit) run in CI. New and modified code must pass these.
- **Type checking:** mypy is run in CI with tests excluded and `disallow_untyped_defs` false. Optional: enable stricter mypy for a subset of app code in a follow-up.

## Anti-patterns

- **No raw `time.sleep` for ordering:** Use freezegun (`time_freezer` fixture) and deterministic timestamps or `freezer.tick()` so test order and timing are reproducible. Where freezegun is unavailable (e.g. Python 3.14), use `unittest.mock.patch` for `datetime.utcnow` or `os.utime()` for file mtimes.
- **No duplicate login code:** Use `authenticated_client` or `admin_authenticated_client`; for one-off login (e.g. testing login itself), use a small helper that POSTs to `/login` once.
- **No duplicate API token setup:** Use conftest `api_token` and `client_with_token` instead of defining them in each test module.

## Remaining risk areas

These areas are under-covered or hard to test. Add or extend tests when touching the relevant code:

- **OIDC login/logout:** Full flow with a real IdP is not tested; test_oidc_logout covers logout with mocks. Document when changing OIDC.
- **PDF generation:** Real PDF code paths are partially excluded from coverage; many tests mock PDF. Add targeted tests when changing PDF logic.
- **Client lock and workforce:** Timer and some routes depend on client lock; coverage is partial. Add tests when changing lock behavior.
- **Scheduled jobs:** Recurring invoice run and report emails run in workers. Unit test service methods; full scheduler E2E can remain out of scope.
- **test_api_v1.py duplicate app:** That module uses its own SQLite app. Prefer migrating to conftest app so scope_restricted_user and client_with_token can be reused there.
