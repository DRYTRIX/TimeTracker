# Desktop activity autotracker

Privacy-first local activity sampling for the Electron desktop client. Design only in Phase 6; capture implementation is a follow-up.

## Goals

- Sample **active window title / application name** on a configurable interval while the user is opted in.
- Keep raw samples **local-only** until the user reviews and promotes them.
- Feed the **existing ActivityWatch pipeline** (`ActivityWatchRule`, `PendingActivity` inbox) instead of inventing a new server ingestion path.
- Default **off**; no window capture until a later phase wires OS APIs behind the same API.

## Non-goals (this phase)

- No remote keylogging, screenshots, or continuous screen recording.
- No new REST endpoints for raw activity blobs.
- No always-on tracking without explicit opt-in.

## Architecture

```text
Electron main process
  └── activity-tracker.js (feature-flagged)
        ├── interval sampler (future: active window title/app)
        ├── local store (encrypted / app userData)
        ├── exclusion rules (apps, title patterns)
        └── purge / retention
              │
              ▼ (opt-in sync, existing connector shape)
        ActivityWatch-compatible events
              │
              ▼
        Server: ActivityWatch connector → rules → PendingActivity inbox
```

### Why reuse ActivityWatch

The server already maps window/app events through `activitywatch_rule.py` into `PendingActivity` for human review before creating time entries. The desktop agent should emit the **same event shape** the ActivityWatch connector expects (or a thin adapter), so review UX, rules, and audit stay consistent.

## Privacy model

| Control | Behavior |
|---------|----------|
| Opt-in | Disabled by default (`activity_tracker_enabled` false). |
| Local-only | Samples written under Electron `userData`; not uploaded until user syncs / AW pipeline runs. |
| Exclusions | Blocklist of app names / title regexes (e.g. banking, password managers). |
| Purge | User can delete local buffer; retention max (e.g. 7–30 days) auto-prunes. |
| Transparency | Settings UI copy must state what is captured, where it lives, and how to turn it off. |

## Phased implementation

### Phase A — Stub (done in Phase 6)

- Module `desktop/src/main/activity-tracker.js` exports `start`, `stop`, `isEnabled`.
- Wired from `main.js` behind store flag `activity_tracker_enabled` (default false).
- **No** OS window capture yet; `start` is a no-op sampler placeholder.

### Phase B — Local capture

- Implement platform-specific active-window readers (e.g. Windows UI Automation / `GetForegroundWindow`, macOS Accessibility, Linux X11/Wayland best-effort).
- Persist samples locally with interval, app, title, idle flag.
- Exclusion list + purge APIs via IPC.

### Phase C — ActivityWatch bridge

- Map local samples to AW bucket/event JSON.
- Optional push into configured ActivityWatch HTTP API **on localhost**, or direct export file the existing connector can import.
- Prefer localhost AW so the server path remains unchanged.

### Phase D — Product polish

- Desktop settings UI for opt-in, interval, exclusions, purge, sync status.
- Telemetry only for aggregate “enabled/disabled” counts if product telemetry is already consented—never titles/apps.

## Feature flag

- Store key: `activity_tracker_enabled` (boolean, default `false`).
- Additional keys (later): `activity_tracker_interval_sec`, `activity_tracker_exclusions`.

## Security notes

- Treat window titles as sensitive (may contain document names, URLs, PII).
- Do not log titles to console in production builds.
- IPC channels for tracker control must be allowlisted like other store keys.

## Follow-ups

- Actual window capture bindings per OS.
- Settings UI strings and privacy help article.
- Tests for local retention/purge and exclusion matching.
