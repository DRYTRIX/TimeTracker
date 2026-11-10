# Raspberry Pi Time Tracker — Software Requirements Document (SRD)

**Version:** 1.0
**Date:** 2025-08-15
**Owner:** (to be assigned)

---

## 1. Purpose & Scope

This SRD defines requirements for a Python application that primarily runs on a Raspberry Pi (RPI) using Docker, with a web-based frontend. The application tracks time across multiple projects with two tracking modes: manual entry and automatic timers that persist even if the browser is closed. The system supports per-user tracking with simple username-only login (no passwords) and provides project overviews, reporting, and per-entry annotations. No external REST API is required.

### In Scope

* Project management (name, client, brief description, billing information)
* Per-user time tracking
* Manual time entry (start/end date & time + project)
* Automatic timers that continue running server-side after browser close
* Project-level overviews of time spent
* Ability to add extra information (notes/metadata) per time entry
* Web-based UI (sleek, modern, and user-friendly)
* Execution on Raspberry Pi via Docker
* Local data storage and backups

### Out of Scope (for v1)

* Public internet exposure (LAN only)
* External integrations (e.g., third-party invoicing, calendars)
* Advanced permissions/roles beyond simple user identification
* Mobile apps (web frontend should be responsive)
* External REST API endpoints

---

## 2. Stakeholders & Users

* **End Users:** Team members who log time per project.
* **Project Managers / Admins:** Configure projects, view summaries, export reports.
* **IT/Ops:** Deploy and maintain the Dockerized application on RPI.

---

## 3. Definitions & Glossary

* **Automatic Timer:** A server-side, long-lived timer associated with a user and project that continues running even if the browser is closed.
* **Entry Notes/Metadata:** Additional text fields or tags recorded with each time entry.
* **Billing Information:** Basic fields such as billing rate, billable flag, PO/Cost center, or invoicing reference stored on the project.

---

## 4. System Overview

A Python backend (Flask recommended) runs inside Docker on a Raspberry Pi. The frontend is a server-rendered web UI with light interactive components and optional WebSocket events for live timers. Data persists locally (SQLite by default) with optional scheduled backups.

---

## 5. Functional Requirements

### 5.1 Authentication & User Identity

1. **Username-only Login:**

   * Users enter a username to start a session; no password.
   * If username does not exist, offer to create it (admin-configurable setting).
   * Persist session via secure cookies.
2. **Access Model:**

   * All logged-in users can create and edit their own time entries.
   * Admin users can manage projects, view all reports, and edit any entry.
   * Admin assignment via config or first user bootstrap.

### 5.2 Project Management

1. **Create/Read/Update/Archive Projects** with fields:

   * Project Name *(required)*
   * Client *(required)*
   * Brief Description *(optional)*
   * Billing Information *(see 5.2.2)*
   * Status: Active/Archived
2. **Billing Information Fields (configurable subset):**

   * Billable (Yes/No)
   * Hourly Rate (currency-aware)
   * Billing Reference (e.g., PO number)
   * Default Time Rounding (e.g., 1/5/15 minutes) *(optional)*

### 5.3 Manual Time Entry

1. **Create Manual Entry:**

   * Required: Project, Start DateTime, End DateTime
   * Optional: Notes/Description (free text), Tags
   * Validation: End must be after Start; no overlaps check (configurable) with warning.
2. **Edit/Delete Entry:** Users can edit or delete their own entries; Admins can edit any.
3. **Bulk Operations:** Optional bulk edit for tags or project reassignment.

### 5.4 Automatic Timer Tracking

1. **Start Timer:** User selects project and clicks **Start**.
2. **Server-Side Persistence:** Timer continues running on the server even if the browser closes, device sleeps, or network drops.
3. **Stop Timer:** User clicks **Stop** from any browser session or device; server finalizes entry (start->stop).
4. **Resilience:** If the RPI restarts, active timers are restored using last known start time and a flag indicating “active”.
5. **Single Active Timer per User:** By default only one running timer per user is allowed; attempting to start another while one is running is rejected until the first is stopped. **System Settings** can disable this to allow multiple concurrent timers. The `SINGLE_ACTIVE_TIMER` environment variable seeds the initial stored value for new deployments; runtime enforcement follows the database setting.
6. **Idle/AFK (optional v1.1):** After N minutes of inactivity, prompt on next visit to confirm whether to subtract idle time.

### 5.5 Time Entry Annotations & Metadata

* **Notes Field:** Rich text (plain text in v1, markdown in v1.1) per entry.
* **Tags:** Freeform comma-separated tags; auto-suggest from existing tags.
* **Edit History (optional):** Keep non-destructive audit trail for edits.

### 5.6 Reporting & Overview

1. **Project Overview:**

   * Total time spent, grouped by user and by time period (day/week/month).
   * Filters: date range, user, tags, billable/non-billable.
   * Summaries: total hours, billable hours, estimated cost (rate × hours).
2. **User Overview:**

   * Personal dashboard of own entries and totals.
3. **Entry List & Detail:**

   * Paginated list with search, sort by date/project/duration.
4. **Exports:**

   * CSV export for entries and summaries.

### 5.7 Notifications & Feedback

* Inline validations, toasts for success/errors.
* Live timer display (mm\:ss) with WebSocket/SSE updates.

### 5.8 Administration

* User list (usernames), role assignment (User/Admin).
* Project archival/unarchive.
* Configuration page (see 6.4) with authentication mode, rounding rules, timezone, currency.

---

## 6. Non-Functional Requirements

### 6.1 Platform & Runtime

* **Target Hardware:** Raspberry Pi 4 (2GB+) recommended.
* **OS:** Raspberry Pi OS (64-bit) or compatible Linux.
* **Containerization:** Docker + docker-compose.
* **Python:** 3.11+.

### 6.2 Performance

* Support 10–25 concurrent users on LAN with sub-200 ms page actions.
* Timer accuracy within ±1 second over 24 hours.

### 6.3 Reliability & Resilience

* Automatic restart with `restart: unless-stopped` in Compose.
* Graceful shutdown; in-flight timers persisted.
* Periodic health checks and liveness endpoints (internal only).

### 6.4 Configurability

* `.env`/config UI for: timezone (default Europe/Rome), currency, default rounding, allow self-register, single-active-timer, idle timeout, export delimiter.

### 6.5 Security

* LAN-only by default; bind to private IP.
* Reverse proxy optional (Caddy/nginx) for TLS on LAN.
* Username-only login; display clear banner that this is an internal tool.
* CSRF protection disabled for simplified development; secure cookies; session timeout.
* Role-based checks server-side.

### 6.6 Privacy & Data Retention

* Store minimal PII (username only).
* Retain entries indefinitely unless purged. Admin-configurable retention and backup.

### 6.7 Localization & Timezones

* System default timezone configurable; all storage in UTC; UI displays local time.
* Handle DST transitions; prevent overlapping/invalid times via UI validation.

### 6.8 Accessibility

* WCAG 2.1 AA-aligned basics: keyboard navigation, color-contrast, focus states.

---

## 7. Architecture & Design

### 7.1 High-Level Components

* **Web App (Flask):** Server-rendered templates (Jinja2) + HTMX/Alpine.js for interactivity.
* **Background Scheduler:** APScheduler (or asyncio task) for periodic jobs (backups, health checks).
* **Real-Time Layer:** WebSocket or Server-Sent Events for live timer updates.
* **Storage:** SQLite with WAL mode; upgrade path to PostgreSQL.
* **Reverse Proxy (optional):** Caddy/nginx container for TLS and static asset caching.

### 7.2 Data Model (Initial Schema)

**users**

* id (PK)
* username (unique, required)
* role (enum: user, admin)
* created\_at

**projects**

* id (PK)
* name (required)
* client (required)
* description (text)
* billable (bool)
* hourly\_rate (decimal, nullable)
* billing\_ref (text, nullable)
* status (enum: active, archived)
* created\_at, updated\_at

**time\_entries**

* id (PK)
* user\_id (FK → users)
* project\_id (FK → projects)
* start\_utc (datetime)
* end\_utc (datetime, nullable when active)
* duration\_seconds (int, computed on finalize)
* notes (text)
* tags (text)
* source (enum: manual, auto)
* edited\_at

**settings**

* id (singleton)
* timezone, currency, rounding\_minutes, single\_active\_timer, allow\_self\_register, idle\_timeout\_minutes

Indexes on (user\_id, start\_utc), (project\_id, start\_utc), and active entries (end\_utc IS NULL).

### 7.3 Timer Persistence Logic

* On **Start**: create `time_entries` row with `end_utc=NULL` and `source=auto`.
* Heartbeat optional; not required for persistence.
* On **Stop**: set `end_utc`, compute `duration_seconds` applying rounding rules.
* On **Server Restart**: query all `end_utc IS NULL` and treat as still running since `start_utc`.

### 7.4 UI/UX Guidelines

* Clean, modern layout with responsive design.
* Primary views:

  1. **Dashboard:** Active timer status, quick Start/Stop, recent entries.
  2. **Projects:** List, filter, create/edit, archive.
  3. **Log Time:** Manual entry form.
  4. **Reports:** Project and user overviews with filters and CSV export.
  5. **Admin:** Users, settings.
* Components: sticky header timer, toasts, modal dialogs, date/time picker, tag chips.

---

## 8. Deployment & Operations

### 8.1 Docker Compose (concept)

* `app` (Flask + Gunicorn)
* `db` (optional Postgres; otherwise SQLite volume in `app`)
* `proxy` (optional Caddy/nginx)
* Volumes for `/data` (DB, exports, backups).

### 8.2 Environment Variables

* `TZ`, `CURRENCY`, `ROUNDING_MINUTES`, `ALLOW_SELF_REGISTER`, `SINGLE_ACTIVE_TIMER`, `IDLE_TIMEOUT_MINUTES`, `ADMIN_USERNAMES`.

### 8.3 Backup & Restore

* Nightly SQLite copy to `/backups/YYYY-MM-DD/` with retention policy.
* Manual on-demand export (zip: DB + CSVs of key tables).

### 8.4 Monitoring

* Health endpoint `/_health` (no auth) for local check.
* Logs to stdout; optional file rotation.

---

## 9. Security Considerations

* Username-only login is weak; mitigate by LAN isolation, optional reverse proxy auth, and kiosk usage.
* CSRF protection disabled; use SameSite cookies; disable framing.
* Rate-limit login attempts by IP to prevent session abuse.

---

## 10. Compliance & Legal

* Internal tool; ensure local employment/time-tracking rules if used formally (outside v1 scope).

---

## 11. Acceptance Criteria (Sample)

1. Users can create projects with client and billing fields.
2. Users can log manual entries with start & end times and notes.
3. Users can start a timer, close the browser, reopen, and see the timer still running.
4. Only one active timer per user (by default).
5. Project overview shows total hours per user for a chosen date range.
6. CSV export contains correct rows and computed durations.
7. System restarts do not lose active timers or historical entries.
8. Admin can archive a project; archived projects cannot be chosen for new entries.
9. UI renders well on desktop and mobile and passes basic keyboard navigation.

---

## 12. Test Cases (Illustrative)

* **TC-01:** Create project with required fields → Project listed as Active.
* **TC-02:** Manual entry with end before start → Validation error displayed.
* **TC-03:** Start timer, close browser, wait 2 minutes, reopen, stop → Duration ≥ 120s.
* **TC-04:** Start timer A, then start timer B → Timer A auto-stops (if configured).
* **TC-05:** Edit entry notes and tags → Changes persist and appear in reports.
* **TC-06:** Archive project, attempt to log time → Not selectable in new entry form.
* **TC-07:** CSV export for project/date range → Matches on-screen totals.
* **TC-08:** RPI reboot → Active timers restored, dashboard reflects running state.
* **TC-09:** CSRF protection disabled - no CSRF validation required.

---

## 13. UI Wireframe Descriptions (Textual)

* **Login:** Username input, “Continue” button, disclaimer about internal use.
* **Dashboard:** Header with current user + active timer (project name, elapsed). Large Start/Stop button, quick project selector, recent entries table with inline edit.
* **Projects:** Card list with name, client, billable badge, actions (Edit, Archive).
* **Log Time:** Form with project dropdown, start/end pickers, notes, tags.
* **Reports:** Filters row (date range, user, project, tags), totals cards, table, export button.
* **Admin:** Users list with role toggles, settings form.

---

## 14. Future Enhancements (Backlog)

> **Superseded.** Most items formerly listed here (idle detection, PWA offline, Kanban, LDAP/OIDC, REST API, PDF invoices) have shipped. Track remaining product gaps in [GAP_ROADMAP.md](GAP_ROADMAP.md) (Phase 6).

---

## 15. Constraints & Assumptions

* LAN-only deployment; minimal threat model.
* No external REST API required.
* SQLite is sufficient for initial scale; PostgreSQL available if needed.

---

## 16. Appendix: Example docker-compose.yml (Skeleton)

```yaml
services:
  app:
    image: timetracker:latest
    build: .
    environment:
      - TZ=Europe/Rome
      - ROUNDING_MINUTES=1
      - SINGLE_ACTIVE_TIMER=true
      - ALLOW_SELF_REGISTER=true
      - ADMIN_USERNAMES=admin
    ports:
      - "8080:8080"
    volumes:
      - app_data:/data
    restart: unless-stopped

  # Optional reverse proxy (TLS on LAN)
  proxy:
    image: caddy:latest
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - app
    restart: unless-stopped

volumes:
  app_data:
  caddy_data:
  caddy_config:
```

---

## 17. Appendix: Data Dictionary (Selected Fields)

* **projects.hourly\_rate:** Decimal(9,2), nullable; interpreted in `settings.currency`.
* **time\_entries.tags:** CSV string; UI presents chips; stored raw for simplicity.
* **time\_entries.duration\_seconds:** Calculated as `round_to(duration, rounding_minutes)` when finalized.

---

**End of Document**
