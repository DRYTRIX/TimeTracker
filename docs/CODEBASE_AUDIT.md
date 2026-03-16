# TimeTracker — Code-Grounded Audit

**Date:** 2026-03-16  
**Scope:** Gaps beyond existing research (INCOMPLETE_IMPLEMENTATIONS_ANALYSIS, CLIENT_FEATURES_IMPLEMENTATION_STATUS, INVENTORY_MISSING_FEATURES). Validated against current code.

---

## 1. Audit Summary

| Category | Finding |
|----------|--------|
| **Backend route parity** | Settings blueprint exposes `/settings` and `/settings/preferences` but templates `settings/index.html` and `settings/preferences.html` are **missing**; `/settings` is served by `user_bp`, so only `/settings/preferences` 500s when hit. |
| **API parity** | `/api/search`, `/api/health`, `/api/dashboard/*`, `/api/activity/timeline` exist. **Dedicated `read:inventory`/`write:inventory` scopes added** (2026-03-16); backward compatible with `read:projects`/`write:projects`. |
| **Integrations / webhooks** | GitHub and **Jira** webhook **signature verification implemented** (optional `webhook_secret` in Jira config; HMAC-SHA256 of body). |
| **Client portal** | Access enforced via `check_client_portal_access()`. **Reports: date range (`?days=1–365`) and CSV export (`?format=csv`)** added. Real-time (SocketIO) and dashboard preferences implemented. |
| **Inventory** | Transfers, Adjustments, Reports **are in the sidebar** (base.html: inventory dropdown with `list_transfers`, `list_adjustments`, `reports_dashboard`). Docs that said “add menu links” are stale. |
| **Issues permissions** | Non-admin filtering **is implemented** in issues.py via `get_accessible_project_and_client_ids_for_user` and `query.filter(Issue.project_id.in_(...), ...)`. |
| **Silent exceptions** | **PEPPOL (invoices.py)** and **activity_feed date params** addressed: targeted catch, log, and optional warning or 400. Other `except: pass` remain in lower-impact paths. |
| **Tests** | Search API, client portal (preferences, reports, activity, SocketIO), inventory API transfers/reports, keyboard shortcuts covered. Supplier/PO **web** tests still missing per docs. |

---

## 2. Detailed Gaps

### 2.1 Missing template: `settings/preferences.html`

| Field | Content |
|-------|--------|
| **Missing feature** | Settings “Preferences” page template. |
| **Evidence** | `app/routes/settings.py` line 46: `return render_template("settings/preferences.html")`. Only `app/templates/settings/keyboard_shortcuts.html` exists; no `preferences.html` or `index.html` under `settings/`. |
| **Why it matters** | Any request to `/settings/preferences` (bookmark, doc link, or future nav) returns **500 TemplateNotFound**. |
| **Approach** | Add `settings/preferences.html` that either redirects to `user.settings` (canonical user prefs) or renders a minimal page with a link to “Main settings”. |
| **Priority** | **High** (user-facing 500). |

---

### 2.2 Missing template: `settings/index.html`

| Field | Content |
|-------|--------|
| **Missing feature** | Settings hub page template. |
| **Evidence** | `app/routes/settings.py` line 22: `return render_template("settings/index.html")`. Template not present. |
| **Why it matters** | Route is only hit if something links to `url_for('settings.index')`. No such links found; URL `/settings` is taken by `user_bp`. So this is a **latent** 500 if a link is added later. |
| **Approach** | Add `settings/index.html` (e.g. hub with links to keyboard shortcuts and user settings) or redirect to `user.settings`. |
| **Priority** | **Medium** (latent; no current link). |

---

### 2.3 Jira webhook: no signature verification — **Fixed 2026-03-16**

| Field | Content |
|-------|--------|
| **Status** | **Addressed.** Optional `webhook_secret` in Jira integration config; when set, requests are verified via HMAC-SHA256 of body (headers `X-Hub-Signature-256`, `X-Atlassian-Webhook-Signature`, `X-Hub-Signature`). |

---

### 2.4 API scopes: no dedicated inventory scopes — **Fixed 2026-03-16**

| Field | Content |
|-------|--------|
| **Status** | **Addressed.** `read:inventory` and `write:inventory` added; inventory endpoints accept either new or legacy project scopes. See `docs/api/API_TOKEN_SCOPES.md`. |

---

### 2.5 Silent exception: PEPPOL compliance check (invoices) — **Fixed 2026-03-16**

| Field | Content |
|-------|--------|
| **Status** | **Addressed.** Exceptions caught and logged; generic warning “Could not verify PEPPOL compliance” shown when check fails. |

---

### 2.6 Client portal: report export and date range — **Fixed 2026-03-16**

| Field | Content |
|-------|--------|
| **Status** | **Addressed.** Reports support `?days=1–365` and `?format=csv` for CSV download. PDF and saved report params remain future work. |

---

### 2.7 Offline queue: request body and method on replay — **Fixed 2026-03-16**

| Field | Content |
|-------|--------|
| **Status** | **Addressed.** Queue stores `method`, `headers`, and `body` in replay-safe form; replay uses them. Legacy items with `options` only still work via fallback. |

---

### 2.8 Keyboard shortcuts: “Usage statistics” placeholder

| Field | Content |
|-------|--------|
| **Missing feature** | Real usage data for keyboard shortcuts. |
| **Evidence** | `app/templates/settings/keyboard_shortcuts.html` ~286: “Usage statistics will appear here as you use keyboard shortcuts” with no backend or script feeding data. |
| **Why it matters** | UX promise with no implementation can confuse users. |
| **Approach** | Either implement simple client-side or server-side usage tracking and display, or replace copy with “Not available” / remove the section. |
| **Priority** | **Low**. |

---

### 2.9 Activity feed API: broad exception swallowing — **Fixed 2026-03-16**

| Field | Content |
|-------|--------|
| **Status** | **Addressed.** Date params catch `ValueError` only; API returns 400 for invalid dates; web route skips filter and logs. |

---

## 3. Newly Discovered Gaps (Not in Original Research)

1. **Settings templates missing**  
   Original docs do not mention missing `settings/preferences.html` and `settings/index.html`. These cause or would cause 500 for `/settings/preferences` and for any future link to the settings hub.

2. **Jira webhook unauthenticated**  
   INCOMPLETE_IMPLEMENTATIONS_ANALYSIS only calls out GitHub webhook verification; GitHub is now implemented. **Jira** webhook has no signature or secret verification.

3. **Inventory menu already present**  
   INVENTORY_MISSING_FEATURES and INVENTORY_IMPLEMENTATION_STATUS say “Add Transfers/Adjustments/Reports to menu”. In **base.html** the inventory dropdown already includes these links and `nav_active_*` for them. This is a doc staleness issue, not a code gap.

4. **Issues permission filtering implemented**  
   Original analysis said “permission filtering for non-admin users is incomplete” in issues.py. Current **issues.py** uses `get_accessible_project_and_client_ids_for_user` and filters the query; the gap is closed.

5. **Push subscription storage**  
   Original doc referred to “push_subscription field on User”. The app uses a **PushSubscription** model and persist in push_notifications.py; storage is implemented.

6. **Offline task/project sync implemented**  
   Original doc said “TODO: Implement task sync” and “project sync” in offline-sync.js. **offline-sync.js** contains full `syncTasks()` and `syncProjects()` with fetch to `/api/v1/tasks` and `/api/v1/projects`. The gap is closed; docs are stale.

7. **Search API implemented**  
   `/api/search` exists in `app/routes/api.py` and is tested; frontend uses it. No missing search endpoint.

8. **Client portal report scoping**  
   Reports are built from `get_portal_data(client)` and `build_report_data(client, ...)`; no cross-client data leak found. Real gap is export and date range (see 2.6).

9. **No dedicated inventory API scopes**  
   Not called out in original research; discovered via API_TOKEN_SCOPES and api_auth.

10. **Keyboard shortcuts “usage statistics”**  
    Placeholder UI with no backend; not in original list.

---

## 4. Roadmap

### Quick wins

- Add **settings/preferences.html** so `/settings/preferences` does not 500 (redirect or minimal page with link to main settings).
- Add **settings/index.html** (hub or redirect to `user.settings`) to avoid future 500.
- Replace **invoices.py** PEPPOL `except Exception: pass` with targeted catch + log (and optional generic warning).

### Medium effort / high impact

- **Jira webhook verification**: Add shared-secret or signature check from headers; document in integration config.
- **Client report export**: Add CSV (and optionally PDF) export and optional date range params for client portal reports.
- **Inventory API scopes**: Introduce `read:inventory` / `write:inventory` and gate inventory endpoints; keep project-scope fallback for backward compatibility.
- **Activity feed date params**: Validate date query params and return 400 on invalid input instead of silent `pass`.

### Architectural improvements

- **Centralized exception handling**: Replace high-impact `except: pass` with a small set of helpers (e.g. `safe_log`, structured error response) and use them in routes/api.
- **Offline queue robustness**: Standardize how request body/method are stored and replayed; add tests for offline POST replay.
- **Docs and status sync**: Update INVENTORY_MISSING_FEATURES / INVENTORY_IMPLEMENTATION_STATUS to reflect current menu and API; add a short “verified on &lt;date&gt;” note to INCOMPLETE_IMPLEMENTATIONS_ANALYSIS for items now fixed (GitHub webhook, issues permissions, search API, push storage, offline sync).

---

## 5. Implemented Quick Wins and Audit Gaps

1. **`/settings/preferences` no longer 500s**  
   The route now redirects to `user.settings` with an info flash (“Your preferences are managed on the main Settings page”) instead of rendering a missing template.

2. **`/settings` (settings index) no longer 500s**  
   The settings hub route now redirects to `user.settings`. (In practice `/settings` is already served by `user_bp` since it is registered first; this change makes the settings blueprint safe if registration order changes or anything links to `settings.index`.)

### Implemented 2026-03-16 (audit gaps)

3. **Jira webhook verification** — Optional `webhook_secret` in Jira integration; when set, incoming webhooks are verified via HMAC-SHA256 of the request body.  
4. **Exception handling (invoices, activity_feed)** — PEPPOL block: targeted catch, log, generic warning. Activity feed API: invalid `start_date`/`end_date` return 400; web route skips filter and logs.  
5. **Client portal reports** — Date range `?days=1–365` and CSV export `?format=csv`.  
6. **Inventory API scopes** — `read:inventory` and `write:inventory` added; backward compatible with `read:projects`/`write:projects`.  
7. **Offline queue replay** — Request body and method stored and replayed correctly for POST/PUT.

---

**Last updated:** 2026-03-16
