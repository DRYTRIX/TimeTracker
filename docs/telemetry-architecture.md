# Telemetry Architecture

This document describes the privacy-aware, two-layer telemetry system: **base telemetry** (always-on, minimal) and **detailed analytics** (opt-in only).

## Overview

| Layer | When | Purpose | Events / Data |
|-------|------|---------|----------------|
| **Base telemetry** | Always (when OTLP sink is configured) | Install footprint, version/platform distribution, active installs | `base_telemetry.first_seen`, `base_telemetry.heartbeat` |
| **Detailed analytics** | Only when user opts in | Feature usage, funnels, errors, retention | All product events (e.g. `auth.login`, `timer.started`) |

- **Consent:** Stored in `installation.json` (`telemetry_enabled`) and synced to `settings.allow_analytics`. Source of truth: `installation_config.get_telemetry_preference()` / `is_telemetry_enabled()`.
- **Identifiers:** One **install_id** (random UUID in installation config) used for base telemetry and, when opt-in, sent with product events. Product events use internal `user_id` identity.

## Base Telemetry (Always-On)

- **Schema (no PII):** `install_id`, `app_version`, `platform`, `os_version`, `architecture`, `locale`, `timezone`, `first_seen_at`, `last_seen_at`, `heartbeat_at`, `release_channel`, `deployment_type`.
- **Events:** `base_telemetry.first_seen` (once per install), `base_telemetry.heartbeat` (e.g. daily via scheduler).
- **Sink:** Grafana Cloud OTLP with `identity = install_id`. No user-level linkage.
- **Trigger:** First-seen sent at app startup (idempotent). Heartbeat via scheduled task (e.g. 03:00 daily).
- **Retention:** Configure in Grafana backend (e.g. 12 months for base). No raw IP storage.

## Detailed Analytics (Opt-In Only)

- **Gated by:** `is_telemetry_enabled()` / `allow_analytics`. No product events sent without opt-in.
- **Events:** Existing names (e.g. `auth.login`, `timer.started`, `project.created`). Optional prefix `analytics.*` in future.
- **Properties:** Include `install_id`, app_version, deployment, request context (path, browser, device) only when opted in.
- **Sink:** Grafana Cloud OTLP (`identity = user_id` for events).
- **Retention:** Per Grafana retention policy. Document in privacy policy.

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

## Sink Configuration

- Base and detailed telemetry are emitted through the same OTLP sender in `app/telemetry/service.py`.
- Required configuration:
  - `GRAFANA_OTLP_ENDPOINT`
  - `GRAFANA_OTLP_TOKEN`
