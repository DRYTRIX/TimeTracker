# ActivityWatch Integration

TimeTracker can import window and web activity from [ActivityWatch](https://activitywatch.net/) as automatic time entries (`source='auto'`). ActivityWatch is an open-source, local-first automated time tracker that runs on your machine.

## How It Works

- **aw-server**: ActivityWatch’s local server (default: `http://localhost:5600`) stores events from watchers.
- **Watchers**: e.g. **aw-watcher-window** (active window) and **aw-watcher-web** (browser tabs) write events into buckets.
- **TimeTracker**: The integration reads from the aw-server REST API and creates `TimeEntry` records with `source='auto'`.

One integration is configured **per user**; `server_url` in the integration config points to that user’s aw-server.

## Requirements

1. **ActivityWatch installed and running**  
   - aw-server must be running (typically on port 5600).  
   - See: https://activitywatch.net/docs/install/

2. **Reachability**  
   - The TimeTracker server must be able to reach the aw-server URL (e.g. `http://localhost:5600` if on the same machine, or `http://hostname:5600` on the same network).  
   - aw-server usually listens on localhost only; for a remote TimeTracker, the machine running ActivityWatch must expose the port (e.g. `--host 0.0.0.0`) and you accept the network/security implications.

## Setup

1. In TimeTracker: **Integrations** → **ActivityWatch** → **Connect** (or **Setup**).
2. Set **ActivityWatch Server URL** (e.g. `http://localhost:5600`).
3. Optionally: **Default Project**, **Lookback days** (1–90), **Bucket IDs** (or leave empty to use all window and web buckets).
4. Save; the connection is tested and the integration is marked active on success.

## Buckets

By default the integration uses buckets whose IDs start with:

- `aw-watcher-window_`
- `aw-watcher-web_`

You can override this by setting **Bucket IDs** (comma-separated or JSON array). If none of the given IDs exist, the integration reports an error and lists some of the available bucket IDs.

## Sync

- **Manual**: Use **Sync Now** on the integration’s detail page.
- **Automatic**: Enable **Auto sync** and choose **Sync schedule** (e.g. hourly, daily) in the setup.

On each sync, the integration fetches events in the configured time range from the selected buckets and creates `TimeEntry` rows. Already-imported events are skipped using `IntegrationExternalEventLink` and an `external_uid` derived from bucket, timestamp, duration, and a hash of the event data.

## Imported Data

| ActivityWatch           | TimeEntry                         |
|-------------------------|-----------------------------------|
| `timestamp` (UTC)       | `start_time` (app-local)          |
| `timestamp + duration`  | `end_time`                        |
| `duration` (seconds)    | `duration_seconds`                |
| `data.app` / `data.title` or `data.url` / `data.title` | `notes` |
| —                       | `source='auto'`                   |
| Config `default_project_id` | `project_id` (or `None`)     |

## Deployment Notes

- **Same machine**: Use `http://localhost:5600`; no extra network setup.
- **Central TimeTracker, user machines run ActivityWatch**: Each user sets `server_url` to their machine (e.g. `http://user-pc:5600`). aw-server must listen on a reachable interface and the network path must allow it; this is off by default for security.
