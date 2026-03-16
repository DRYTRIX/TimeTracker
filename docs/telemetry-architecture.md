# Telemetry Architecture

This document describes the privacy-aware, two-layer telemetry system: **base telemetry** (always-on, minimal) and **detailed analytics** (opt-in only).

## Overview

| Layer | When | Purpose | Events / Data |
|-------|------|---------|----------------|
| **Base telemetry** | Always (when PostHog is configured) | Install footprint, version/platform distribution, active installs | `base_telemetry.first_seen`, `base_telemetry.heartbeat` |
| **Detailed analytics** | Only when user opts in | Feature usage, funnels, errors, retention | All product events (e.g. `auth.login`, `timer.started`) |

- **Consent:** Stored in `installation.json` (`telemetry_enabled`) and synced to `settings.allow_analytics`. Source of truth: `installation_config.get_telemetry_preference()` / `is_telemetry_enabled()`.
- **Identifiers:** One **install_id** (random UUID in installation config) used for base telemetry and, when opt-in, sent with product events. Product events use internal `user_id` as distinct_id in PostHog.

## Base Telemetry (Always-On)

- **Schema (no PII):** `install_id`, `app_version`, `platform`, `os_version`, `architecture`, `locale`, `timezone`, `first_seen_at`, `last_seen_at`, `heartbeat_at`, `release_channel`, `deployment_type`.
- **Events:** `base_telemetry.first_seen` (once per install), `base_telemetry.heartbeat` (e.g. daily via scheduler).
- **Sink:** PostHog with `distinct_id = install_id`. No user-level linkage.
- **Trigger:** First-seen sent at app startup (idempotent). Heartbeat via scheduled task (e.g. 03:00 daily).
- **Retention:** Configure in PostHog (e.g. 12 months for base). No raw IP storage.

## Detailed Analytics (Opt-In Only)

- **Gated by:** `is_telemetry_enabled()` / `allow_analytics`. No product events sent without opt-in.
- **Events:** Existing names (e.g. `auth.login`, `timer.started`, `project.created`). Optional prefix `analytics.*` in future.
- **Properties:** Include `install_id`, app_version, deployment, request context (path, browser, device) only when opted in.
- **Sink:** PostHog (`distinct_id = user_id` for events).
- **Retention:** Per PostHog plan (e.g. 24 months). Document in privacy policy.

## Consent Behavior

- **Opt-in:** Setup wizard or Admin → Settings (Privacy & Analytics) or Admin → Telemetry. Enabling triggers one opt-in install ping (`check_and_send_telemetry()`).
- **Opt-out:** Same toggles. Detailed analytics stop immediately; base telemetry continues (minimal footprint).
- **Data minimization:** Base layer is fixed schema. Detailed layer only when user agrees.

## Event Naming

- **Reserved:** `base_telemetry.*` for base layer. Do not use for product events.
- **Product events:** Keep current names (e.g. `timer.started`) or use `analytics.*`; all gated by opt-in.

## Implementation

- **Service:** `app/telemetry/service.py` — `send_base_first_seen()`, `send_base_heartbeat()`, `send_analytics_event()`, `is_detailed_analytics_enabled()`.
- **App entry points:** `app/__init__.py` — `track_event`, `track_page_view`, `identify_user` delegate to telemetry service (consent-aware).
- **Scheduler:** `app/utils/scheduled_tasks.py` — job `send_base_telemetry_heartbeat` (daily).
- **Startup:** In `create_app`, after scheduler start, call `send_base_first_seen()` once per install.

## Self-Hosting / Replacing Vendors

- **Base telemetry:** Currently sent to PostHog. To use a custom backend, add an env var (e.g. `BASE_TELEMETRY_URL`) and in `send_base_telemetry()` POST the same schema to that URL; do not store raw IP; derive country server-side if needed and discard IP.
- **Detailed analytics:** PostHog can be replaced by implementing an analytics sink in `app/telemetry/service.py` (e.g. `send_analytics_event` writing to another provider or your own API).

## PostHog Dashboard Setup (Base Telemetry)

Base telemetry sends two events to PostHog (when `POSTHOG_API_KEY` is set):

- **`base_telemetry.first_seen`** — emitted once per install at first startup.
- **`base_telemetry.heartbeat`** — emitted daily (e.g. 03:00 UTC) per install.

Both use **`distinct_id` = install_id** (UUID). Event properties: `install_id`, `app_version`, `platform`, `os_version`, `architecture`, `locale`, `timezone`, `first_seen_at`, `last_seen_at`, `heartbeat_at`, `release_channel`, `deployment_type`. **Note:** `country` is not sent in the payload; add server-side geo later if needed.

### How to update your PostHog dashboard

1. **Open PostHog** → **Product Analytics** → **Insights** (or **Dashboards**).

2. **Create a new dashboard** (e.g. “TimeTracker installs”) or add tiles to an existing one.

3. **Add these insights:**

| Insight | Type | Event(s) | What to set |
|--------|------|----------|-------------|
| **New installs per day** | Trends | `base_telemetry.first_seen` | Series: Total count. Breakdown: none. Interval: Day. |
| **Active installs over time** | Trends | `base_telemetry.heartbeat` | Series: **Unique users** (this is unique install_id). Interval: Day or Week. |
| **Installs by app version** | Trends or Bar | `base_telemetry.heartbeat` | Series: Unique users. **Breakdown by** → property → `app_version`. |
| **Installs by platform** | Bar or Pie | `base_telemetry.heartbeat` | Series: Unique users. **Breakdown by** → `platform`. |
| **Installs by OS version** | Bar | `base_telemetry.heartbeat` | Breakdown by `os_version`. |
| **Installs by deployment type** | Bar | `base_telemetry.heartbeat` | Breakdown by `deployment_type` (docker vs native). |

4. **Unique users = unique installs:** In PostHog, “Unique users” for these events is “unique distinct_id”, which is **install_id**, so it equals unique installs.

5. **Churned / inactive installs:** Build a **Lifecycle** or custom insight: e.g. “Unique distinct_ids that had `base_telemetry.heartbeat` in the previous 30 days but not in the last 7 days”. Or use a **Stickiness** insight on `base_telemetry.heartbeat` and invert (install_ids that didn’t stick in last N days).

6. **Country (if you add it later):** If you add a `country` property to the base payload (e.g. from server-side IP lookup), add an insight: **Breakdown by** `country` on `base_telemetry.heartbeat` (Unique users).

7. **Retention (optional):** For “install_ids that sent a heartbeat again after 7 days”, use PostHog **Retention** with first event = `base_telemetry.first_seen` and return event = `base_telemetry.heartbeat`.

### Filters

- Restrict to base telemetry only: **Event name** is one of `base_telemetry.first_seen`, `base_telemetry.heartbeat`.
- Exclude test: filter out `app_version` containing `dev` or `test` if you use that convention.
