# Integrations

TimeTracker ships with several built-in integrations that you can
enable per user from **Settings → Integrations**. Each integration is
stored in the existing `Integration` model — there are no
integration-specific tables — and all secrets are encrypted at rest
when `SETTINGS_ENCRYPTION_KEY` is configured.

## Personal connectors (per-user, opt-in)

These are independent of the workspace-wide connectors and can be
enabled or disabled by each user without affecting anyone else.

- **[GitHub](GITHUB_CONNECTOR.md)** — Webhook-driven task creation,
  optional auto-start timer on issue assignment, manual pull of open
  issues. Personal access token + HMAC-signed webhook.
- **[Google Calendar](GOOGLE_CALENDAR.md)** — OAuth2 connector with
  import / export / both directions, auto token refresh, and a 30-minute
  scheduled sync.
- **[Slack](SLACK.md)** — Timer start/stop notifications, `/tt` slash
  command (`start`, `stop`, `status`, `today`), and an optional daily
  summary post.

## Workspace connectors (admin)

- **[Slack Attendance](SLACK_ATTENDANCE.md)** — Workspace-level
  `/in`, `/brb`, `/back`, `/out` slash commands in a dedicated channel
  for clock-in/out and breaks. Maps Slack users by ID or profile email.
  Configured under **Integrations → Workspace integrations**.

## Workspace / project connectors

- **[ActivityWatch](ACTIVITYWATCH.md)** — Local-first automated time
  tracking imported as `source='auto'` time entries.
- **[Linear](LINEAR.md)** — Pull Linear issues as tasks via Personal
  API key.
- **[Xero](XERO.md)** — Sync invoices and clients with Xero.

## Conventions

All connectors subclass `app/integrations/base.py:BaseConnector`,
implement at minimum `sync()` and `handle_webhook()` where applicable,
and follow the same operational guarantees:

- HTTP calls use the `requests` library with a 10-second timeout, all
  wrapped in `try/except requests.RequestException`.
- Secrets are never logged in raw form — they are truncated to a short
  prefix (`xoxb-...`, `ghp_...`).
- When an integration row is missing or `is_active=False`, every
  method returns `{"ok": false, "error": "Integration not configured"}`
  without raising. Existing UI screens (timers, exports, dashboards)
  keep working when a connector is disabled or broken.
- Webhook receivers verify provider signatures before reading the body
  and return 401 on any verification failure.
