# Google Calendar connector

Lives in `app/integrations/google_calendar_connector.py` (provider key
**`google_calendar_connector`**). Per-user, OAuth2-based, with two-way
sync between Google Calendar events and TimeTracker time entries.

## What it does

Pick one of three sync modes per integration:

| `sync_direction` | Behaviour |
|------------------|-----------|
| `import` (default) | Pulls dated (non all-day) events into TimeTracker as completed time entries on the default project. |
| `export`           | Pushes TimeTracker time entries created since `last_sync_at` to Google Calendar with the title `[TT] {project} — {task or notes}`. |
| `both`             | Runs `import` followed by `export` in a single sync. |

`import` skips:

- All-day events (no `dateTime` start/end).
- Events whose summary contains `[TT]` (avoids ping-pong with `export`).
- Anything already linked, detected by `gcal:{event_id}` appearing in the
  notes of an existing `TimeEntry`.

`export` skips entries whose notes already contain `[gcal:` (entries
that came in via `import`).

Both directions tag the linked row so subsequent syncs don't duplicate
work.

## Configuration

Open **Integrations → Google Calendar** (under *Personal connectors*).
When you connect for the first time you'll be sent through the standard
Google OAuth consent flow with scopes
`https://www.googleapis.com/auth/calendar.readonly` and
`.../calendar.events`.

| Field | Stored as | Notes |
|-------|-----------|-------|
| `access_token`  | `integration.config.access_token` (encrypted) | Refreshed automatically. |
| `refresh_token` | `integration.config.refresh_token` (encrypted) | Required for long-lived access; if Google omits it, the connector keeps the previous one. |
| `token_expiry`  | `integration.config.token_expiry` | ISO datetime in UTC. Refresh kicks in within 5 minutes of expiry. |
| `calendar_id`   | `integration.config.calendar_id` | Defaults to `primary`. |
| `sync_direction`| `integration.config.sync_direction` | `import` / `export` / `both`. |
| `default_project_id` | `integration.config.default_project_id` | Where imported events land. |
| `sync_days_back`| `integration.config.sync_days_back` | Clamped to **1–30** (default `7`). |
| `last_sync_at`  | `integration.config.last_sync_at` | ISO datetime, updated after every successful sync. |

## OAuth setup (admin)

The connector reuses the Flask config that the existing OAuth flows
already use:

| Setting | Required |
|---------|----------|
| `GOOGLE_CLIENT_ID`     | Yes |
| `GOOGLE_CLIENT_SECRET` | Yes |
| The callback URL exposed by TimeTracker is **`/integrations/google/callback`**. Add it to your Google Cloud OAuth client's *Authorized redirect URIs*. |

If either setting is missing the connect button still renders but
returns a clear `oauth_not_configured` error on click.

## Endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET  | `/integrations/google/connect`    | `@login_required` | Builds the Google OAuth URL with `state=` containing the user id (CSRF-protected by the Flask session) and redirects. |
| GET  | `/integrations/google/callback`   | `@login_required` | Exchanges the auth code, encrypts and stores the tokens, redirects to the Integrations page with a success flash. |
| POST | `/integrations/google/disconnect` | `@login_required` | Calls `https://oauth2.googleapis.com/revoke?token=...` (best-effort) and clears the tokens in `integration.config`. |
| POST | `/api/integrations/google/sync`   | `@login_required` | Triggers `sync()` in whichever direction is configured. |
| GET  | `/api/integrations/google/status` | `@login_required` | Returns `connected`, the linked Google email (when available), `calendar_id`, and `last_sync_at`. |

All Google API calls use a **10-second timeout** and are wrapped in
`try/except requests.RequestException`; failed refresh attempts return a
descriptive error and the connector remains `is_active=False` until the
next successful auth.

## Token refresh

`_refresh_token_if_needed()` runs at the top of every API call:

1. If `token_expiry` is missing **or** within 5 minutes of `now()`, POST
   to `https://oauth2.googleapis.com/token` with
   `grant_type=refresh_token`.
2. Update `access_token` and `token_expiry` in `integration.config`
   (still encrypted).
3. Return the live access token.

If Google rejects the refresh token (e.g. user revoked access from
their Google account), the connector logs the failure, marks the
integration unhealthy, and surfaces a *Reconnect required* message in
the UI on the next status check.

## Scheduled sync

`app/utils/scheduled_tasks.py` registers an APScheduler job
`google_calendar_sync` that runs every 30 minutes and iterates over
every active Google Calendar integration. Each user is wrapped in its
own `try/except`, so one broken token cannot block the rest.

## Operational notes

- Times are stored and exported in UTC; `timeZone: "UTC"` is set on
  every event the connector creates.
- The connector never logs raw tokens — only `prefix...` truncations.
- When the integration row is missing or `is_active=False`, every
  method returns `{"ok": false, "error": "Integration not configured"}`
  without raising.
- `revoke()` is best-effort — if Google's revoke endpoint returns 400
  (often because the token was already revoked) the connector still
  wipes the stored tokens locally.
