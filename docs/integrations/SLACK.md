# Slack connector

Lives in `app/integrations/slack_connector.py` (provider key
**`slack_connector`**). Per-user, opt-in. Posts notifications when
timers start/stop, handles `/tt` slash commands, and (optionally) posts
a daily summary at a chosen local time.

## What it does

- **Timer notifications** — Fires `chat.postMessage` to the configured
  channel when the linked user starts or stops a timer. Wired into both
  the page route (`app/routes/timer.py`) and the JSON API
  (`app/routes/api.py`) as a fire-and-forget hook — failures only emit
  a debug log; they never break the timer flow.
- **Slash commands** — A single `/tt` command supports:
  - `/tt start [project]` — starts a timer (project is matched by id or
    case-insensitive partial name).
  - `/tt stop` — stops the running timer and replies with the duration.
  - `/tt status` — reports the current timer.
  - `/tt today` — reports today's hours via `notification_service.get_today_summary_for_user`.
  - Anything else — returns the in-place help text.
  Every reply is an *ephemeral* JSON response, so it's only visible to
  the user who invoked the command. The endpoint returns within Slack's
  3-second budget.
- **Daily summary** — Optional once-a-day post at a user-configured
  local time, driven by the `slack_daily_summary` APScheduler job
  (every 30 minutes; the connector matches the configured time against
  the window).

## Configuration

Open **Integrations → Slack** (under *Personal connectors*).

| Field | Stored as | Notes |
|-------|-----------|-------|
| **Bot token**         | `integration.config.bot_token` (encrypted) | `xoxb-...` from your Slack app's **OAuth & Permissions** page. |
| **Signing secret**    | `integration.config.signing_secret` (encrypted) | From **Basic Information**; used to verify slash commands. |
| **Channel ID**        | `integration.config.channel_id` | Either a public channel like `#general` or the raw ID (`C1234567890`). The bot must be in the channel. |
| **Notify on start**   | `integration.config.notify_on_start` | Boolean, default `true`. |
| **Notify on stop**    | `integration.config.notify_on_stop`  | Boolean, default `true`. |
| **Daily summary**     | `integration.config.daily_summary`   | Toggle. |
| **Daily summary time**| `integration.config.daily_summary_time` | `HH:MM` (24h, user's local time). Default `18:00`. |
| **Slack user ID**     | `integration.config.linked_slack_user_id` | Required for slash commands. Looks like `U0ABC1234`. |

The connector degrades gracefully when not configured: if the
integration row is missing or `is_active=False`, all
`notify_for_user(...)` / `post_daily_summary(...)` calls quietly return
`{"ok": false, "error": "Integration not configured"}`.

## Slack app setup

1. Create a Slack app (https://api.slack.com/apps) — *From scratch* is
   fine.
2. **OAuth & Permissions → Bot Token Scopes** add at least:
   `chat:write`, `chat:write.public` (so the bot can post in channels
   it hasn't been invited to), `commands` (for the slash command), and
   `users:read` (optional, for nicer status output).
3. **Slash Commands → Create New Command**:
   - **Command:** `/tt`
   - **Request URL:** `{base_url}/api/integrations/slack/events`
   - **Short description:** *TimeTracker timer control*
4. **Event Subscriptions** is optional — the connector only needs the
   slash command URL today, but the same endpoint will respond to
   Slack's URL verification handshake (returns the `challenge` field
   immediately) if you decide to subscribe to events later.
5. Install the app to your workspace and copy the **Bot User OAuth
   Token** + **Signing Secret** into the TimeTracker card.

## Endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/api/integrations/slack/events` | HMAC-SHA256 signature | Slash command + URL verification handler. |
| POST | `/api/integrations/slack/config` | `@login_required` | Save the UI form. |
| POST | `/api/integrations/slack/test`   | `@login_required` | Posts a test message to the configured channel via `chat.postMessage`. |
| GET  | `/api/integrations/slack/status` | `@login_required` | Returns the current config snapshot (no secrets) plus connection state. |

The `/events` endpoint is `csrf.exempt` and rejects (401) any request
whose `X-Slack-Request-Timestamp` is more than **5 minutes** old or
whose `X-Slack-Signature` doesn't match the HMAC-SHA256 of
`v0:{timestamp}:{raw_body}`.

## Notification format

Timer start:

```
:stopwatch: *{user.display_name or username}* started a timer
 *Project:* {project_name}{ — task_name if any}
 *Started at:* {HH:MM}
```

Timer stop:

```
:white_check_mark: *{user.display_name}* stopped a timer
 *Project:* {project_name}
 *Duration:* {duration}
 *Billable:* Yes|No
```

Daily summary:

```
:bar_chart: *Daily summary for {user.display_name}*
 *Hours logged:* {hours}h across {projects} projects
 Have a great evening!
```

## Operational notes

- Tokens never appear in logs — only `xoxb-...` truncations.
- All Slack Web API calls (`chat.postMessage`, `auth.test`) use a
  **10-second timeout** and are wrapped in `try/except`.
- The notification hook in `start_timer` / `stop_timer` is
  fire-and-forget; Slack outages won't slow down the UI.
- The same Slack app can be installed by multiple TimeTracker users —
  each user gets their own integration row, channel, and command-user
  binding.
