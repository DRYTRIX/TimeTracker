# TimeTracker Running-Instance Audit Report

**Date:** 2026-10-04  
**Target:** Docker Compose stack at `https://localhost` (`timetracker-app`, `timetracker-db`, `timetracker-nginx`, `timetracker-peppol-bridge`, `timetracker-ollama`)  
**Scope:** Container health, route crawl, browser walkthrough, REST API v1, security probes, pytest  
**Data policy:** Disposable (create/edit/delete allowed)  
**Test accounts:** `audit_admin` (admin), `audit_user` (user) — keep or delete as preferred  

---

## Executive summary

The stack is **up and healthy**. Migrations are at a single head (`198_add_oauth_applications`). Core flows (login, dashboard, timer, projects, clients, invoices, reports, calendar, admin) work in the browser. REST API auth and most list/CRUD operations work.

The audit found **multiple High-severity HTTP 500 pages**, several **security configuration gaps**, and **telemetry noise**. No Critical stored-XSS or open-redirect issues were confirmed. CSRF protection is active but its failure UX is misleading.

| Severity | Count (approx.) |
|----------|-----------------|
| Critical | 0 confirmed |
| High     | 8+ (HTTP 500 clusters + `/metrics` exposure) |
| Medium   | 6+ |
| Low / Info | several |

---

## Phase 1 — Container / config health

### OK
- All primary containers healthy; migrations applied (154 tables); single Alembic head.
- HTTP→HTTPS redirect works; TLS serves a localhost dev cert (expected for local).
- Security response headers present: CSP, HSTS, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`.
- Session cookies: `Secure; HttpOnly; SameSite=Lax`.
- `/static/dist/output.css` serves 200 from the image (230815 bytes). Host working tree CSS is older (176891) — image was built with a fresher frontend build than the uncommitted host tree.
- `SECRET_KEY` is set and non-default (64 hex chars).

### Findings

#### [High] Unauthenticated `/metrics` endpoint
- **Evidence:** `curl -skI https://localhost/metrics` → 200, body ~100KB–1MB Prometheus text. App logs: `METRICS_TOKEN is unset: /metrics is publicly reachable`.
- **Suspected:** metrics route + missing `METRICS_TOKEN` env.
- **Fix:** set `METRICS_TOKEN` and require `X-Metrics-Token` / `?token=` for scrapers.

#### [Medium] `RATELIMIT_STORAGE_URI` is `memory://`
- **Evidence:** startup warning on every `flask` CLI / worker boot.
- **Impact:** limits not shared across workers; reset on restart.
- **Fix:** point at Redis for any multi-worker / production deploy.

#### [Medium] OpenTelemetry metric export failing (429 Mimir series limit)
- **Evidence:** repeating `ERROR: Failed to export batch code: 429 ... err-mimir-max-active-series` about once per minute.
- **Impact:** log noise; metrics not reaching Grafana Cloud; no app crash observed.
- **Fix:** reduce series cardinality, raise tenant limit, or disable OTLP metrics locally.

#### [Medium] Self-registration tip enabled
- **Evidence:** `ALLOW_SELF_REGISTER=true`; login page tip: “Enter a new username to create your account.”
- **Impact:** anyone who can reach `/login` can create accounts (unless other controls apply).
- **Fix:** set `ALLOW_SELF_REGISTER=false` for locked-down instances.

#### [Low] Duplicate security headers
- **Evidence:** some responses list `X-Frame-Options: DENY, DENY` (nginx + app both set headers).
- **Fix:** set headers in one place only.

#### [Low] Host vs image static mismatch / stray backup
- Uncommitted: `app/static/date-picker-init.js`, `app/static/js/unsaved-changes.js`, `tests/test_time_format_display.py`, `app/static/dist.rootbak/`.
- Image CSS newer than host `app/static/dist/output.css`.

---

## Phase 2 — Test users

Created via flask shell:
- `audit_admin` / `Audit!Pass123` (id 6, admin)
- `audit_user` / `Audit!User123` (id 7, user)
- API token `audit-token` (id 3, expires in 1 day) — **revoke after review**

**Note:** CLI `flask create_admin` creates users **without** a password; use `set_password` for local auth.

**Login automation note:** with `WTF_CSRF_SSL_STRICT=true`, POSTs need `Origin`/`Referer`. Missing them triggers CSRFError (see security).

---

## Phase 3 — Route crawl

- Routes dumped: ~1236 lines / ~706 GET rules.
- Checked: 417 static + 150 dynamic samples with authenticated session.
- Status mix included **18× HTTP 500**.

### [High] HTTP 500 pages (grouped by root cause)

| Route(s) | Error | Likely file(s) |
|----------|-------|----------------|
| `/activity` | Missing template `activity/feed.html` | `app/routes/activity_feed.py` |
| `/admin/geofences`, `/admin/payroll-templates`, `/admin/gamification` | `BuildError: endpoint 'admin.dashboard'` (should be `main.dashboard` or `admin.admin_dashboard`) | templates under `app/templates/admin/` |
| `/api/activities/stats` | SQLAlchemy `ArgumentError` on property object | `app/routes/api.py` `get_activity_stats` |
| `/expenses`, `/expenses/scan-receipt` | Jinja `'min' is undefined` / missing `expenses/scan_receipt.html` | `app/templates/expenses/list.html`, `app/routes/expenses.py` |
| `/inventory/reservations` | `BuildError: inventory.new_reservation` | `app/templates/inventory/reservations/list.html` |
| `/quotes/templates`, `/quotes/templates/create` | Missing templates | `app/routes/quotes.py` |
| `/api/unpaid-hours/by-salesman` | `'str' object has no attribute 'custom_fields'` | unpaid-hours API handler |
| `/settings/profile` | `BuildError: profile.index` (suggests `auth.profile`) | `app/routes/settings.py` |
| `/chat` | `BuildError: team_chat.create_channel` | `app/templates/chat/index.html` |
| `/workflows/create`, `/workflows/templates/create` | Jinja `'task' is undefined` | `app/templates/workflows/_form.html` |
| `/admin/oidc/user/<id>` | User has no `projects` attribute | `app/templates/admin/oidc_user_detail.html` |
| `/api/client-notes/<id>` | 500 wrapping a 404 | client-notes API error handling |

### Other crawl notes
- `/kanban` slow (~2.1–2.3s) — Medium performance.
- Many `/api/v1/*` return 401 without API token (expected; session cookie is not enough).
- Client-portal routes redirect to portal login (expected for staff session).
- Static 404: `/api/goals/current` (Low).

---

## Phase 4 — Browser walkthrough

Logged in as `audit_admin` (after ignoring self-signed cert in the browser).

| Area | Result |
|------|--------|
| Login / logout | OK |
| Dashboard | OK; shows overdue invoices banner (€8,330.85) |
| Timer UI | OK; start/stop verified via API (201/200) |
| Projects / clients / tasks | OK (200) |
| Kanban | OK but slow |
| Invoices list | OK (27 invoices, filters, export links) |
| Expenses | **500** (matches crawl) |
| Activity / Chat | **500** |
| Reports / calendar / focus / quotes / admin / settings | OK |
| Dark theme | OK |
| Self-reg tip on login | Visible (config finding) |

Stored XSS payload in client name rendered **HTML-escaped** on `/clients` (`&#34;&gt;&lt;img ...`).

---

## Phase 5 — REST API v1

| Check | Result |
|-------|--------|
| No token / bad token | 401 with JSON `error_code: unauthorized` |
| `Authorization: Bearer` and `X-API-Key` | Both work for `/api/v1/users/me` |
| List endpoints (projects, clients, tasks, entries, invoices, expenses, mileage, users, quotes, payments, leads, deals, issues, webhooks, search, timer) | 200 |
| Pagination | Present (`page`, `per_page`, `total`, …) |
| Create client | 201 |
| Create client invalid | 400 validation JSON |
| Create project with `status` field | **400** `Unknown field` — omit `status` → 201 |
| Oversized client name | 400 |
| Timer start/stop | 201 / 200 |
| Overlapping time entry | 400 with clear message |

---

## Phase 6 — Security

| Check | Result |
|-------|--------|
| Security headers | Present |
| CSP `script-src 'unsafe-inline'` | **Medium** |
| CSRF without token | Rejected (no client created); redirects back to form (**Medium** UX — easy to mistake for success) |
| CSRF login without Origin/Referer | CSRFError flashes “session expired…” and redirects to `/dashboard`, then bounce to login (**Medium**) |
| Admin routes as `audit_user` | **403** |
| Open redirect via `next=` | Blocked (lands on `/dashboard` or empty) |
| `/metrics` public | **High** |
| Login rate limit | Active (`5 per minute` decorator); observed after failed attempts |
| Logout | Invalidates session |
| Stored XSS (client name) | Escaped |
| Rate-limit backend | memory:// (**Medium**) |

---

## Phase 7 — Pytest

Environment: local venv at `/tmp/timetracker-audit/venv` with `PYTHONPATH=<repo>`. Pytest is **not** installed in the app image.

### Smoke (`-m smoke`)
- Collected **152** selected / 2650 total (138 when ignoring `tests/test_payment_smoke.py`).
- First full smoke attempt: most tests passed through ~55%; **2 failures** in `tests/test_invoice_currency_smoke.py`; then **hung** inside `tests/test_payment_smoke.py` (no progress for 20+ minutes).
- Re-runs with `--timeout=15–30` still hit long stalls; wall-clock `timeout 240` aborted mid-suite (exit 124) after early success through admin/users and an **ERROR** in `tests/test_audit_trail_smoke.py`.
- Parallel `-n auto/4` was unsuitable here: workers crashed en masse (`maximum crashed workers reached: 16`), producing unreliable failure noise.

### Broader suite
- Full `-m "not slow"` not completed (same hang/timeout risk).
- `-m "api or security"` started cleanly (calendar/client-notes/comments API smoke dots) but was wall-clock aborted after early `E` failures in setup-heavy modules (`test_admin_book_for_others`, logo settings, audit activities).

### Pytest process findings (test infra / flaky suite)
| Issue | Severity | Notes |
|-------|----------|-------|
| Hang in `test_payment_smoke` | High (CI reliability) | Blocks smoke completion without ignore/timeout |
| `test_invoice_currency_smoke` failures | Medium | Both smoke tests fail with `sqlite3.IntegrityError: FOREIGN KEY constraint failed` inserting into `invoices` (project_id/client_id fixtures). See `/tmp/timetracker-audit/pytest_invoice_currency.log` |
| xdist worker crashes under timeout | Medium | Do not use `-n auto` with aggressive timeouts on this suite without investigation |
| Missing `PYTHONPATH` / app not installed editable | Low | Local runs need `PYTHONPATH=.` or `pip install -e .` |

Artifacts: `/tmp/timetracker-audit/pytest_smoke.log`, `pytest_full.log`, `pytest_invoice_currency.log`.

---

## Recommended priority fixes

1. **Set `METRICS_TOKEN`** (and document scraper auth).
2. **Fix High 500s** that share one root cause:
   - Replace dead endpoint names (`admin.dashboard`, `profile.index`, `team_chat.create_channel`, `inventory.new_reservation`).
   - Fix expenses list Jinja (`min` filter / import).
   - Restore or ship missing templates (`activity/feed.html`, quote templates, scan receipt).
   - Fix workflows `_form.html` undefined `task`.
3. **Turn off or fix OTLP metrics** to stop 429 spam.
4. **Disable self-registration** if this instance is not meant to be open.
5. **Use Redis for rate limits** if running multiple workers.
6. **Improve CSRFError handler** so login CSRF failures do not redirect to `/dashboard`.

---

## Cleanup

- Throwaway scripts/logs: `/tmp/timetracker-audit/` (creds, pytest venv, crawl/recrawl outputs).
- API token id **3** (`audit-token`) **revoked**.
- Users `audit_admin` / `audit_user` could not be hard-deleted (FK from `integrations`); passwords rotated and accounts **deactivated** after re-verification.

See **Resolved (same-day follow-up)** below for what was fixed in application code and config.
---

## Resolved (same-day follow-up)

Fixes landed after this audit; verified against the rebuilt Docker stack on **2026-10-04**.

### Application / config
| Finding | Resolution |
|---------|------------|
| HTTP 500 cluster (`admin.dashboard`, missing templates, Jinja `min` / `{{task.name}}`, etc.) | Endpoint aliases, new templates (`activity/feed`, quote templates, `expenses/scan_receipt`), Jinja fixes, `team_chat.create_channel`, inventory reservation link, OIDC `project_count` |
| `/api/activities/stats` | Query `User.full_name` instead of non-column `display_name` |
| `/api/unpaid-hours/by-salesman` | Use `project.client_obj` |
| `/api/client-notes/<id>` | Return JSON 404 instead of turning `get_or_404` into 500 |
| Project create rejects `status` | `ProjectCreateSchema` accepts optional `status` |
| CSRF login failure UX | Unauthenticated / login CSRF failures redirect to `auth.login` |
| Public `/metrics` | `METRICS_TOKEN` set in `.env` |
| Self-registration tip | `ALLOW_SELF_REGISTER=false` |
| OTLP 429 spam | `OTEL_EXPORTER_OTLP_*` commented out in `.env` |
| Duplicate security headers | nginx `https.conf` keeps HSTS only; app sets the rest |

### Re-verification
- `docker compose up --build -d app` — healthy.
- Focused re-crawl of the 18 previously-500 paths: **all non-500** (client-notes correctly **404**). See `/tmp/timetracker-audit/recrawl_summary.txt`.
- `/metrics` without token → **401**.
- Pytest: `tests/test_audit_regressions.py`, `tests/test_invoice_currency_smoke.py`, `tests/test_payment_smoke.py` — **36 passed**.

### Test infra
- Invoice currency smoke: create real user/client/project, commit before Settings, build `Invoice` without fragile factory SubFactory / numbering.
- Payment smoke: direct `Invoice` create; autouse mocks for email / survey / paid workflow.
- New `tests/test_audit_regressions.py` (`@pytest.mark.smoke`) GETs fixed routes as admin.

### Cleanup after verify
- Audit users `audit_admin` / `audit_user` deactivated (hard delete blocked by `integrations` FK); API token remains revoked.

---

## Appendix — Evidence locations

| Artifact | Path |
|----------|------|
| Route dump | `/tmp/timetracker-audit/flask_routes.txt` |
| Crawl CSV / summary | `/tmp/timetracker-audit/crawl_results.csv`, `crawl_summary.txt` |
| Re-crawl after fixes | `/tmp/timetracker-audit/recrawl_results.csv`, `recrawl_summary.txt` |
| Verify pytest | `/tmp/timetracker-audit/pytest_verify.log` |
| API results | `/tmp/timetracker-audit/api_results.json`, `api_timer.json` |
| Security results | `/tmp/timetracker-audit/security_results.json` |
| Exception snippets | `/tmp/timetracker-audit/exceptions.txt` |
| Pytest logs | `/tmp/timetracker-audit/pytest_smoke.log`, `pytest_full.log` |
| Creds (chmod 600) | `/tmp/timetracker-audit/creds.env` |
