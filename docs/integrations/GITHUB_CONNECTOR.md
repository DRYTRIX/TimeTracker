# GitHub connector (personal, webhook-driven)

> Lives in `app/integrations/github_connector.py` (provider key
> **`github_connector`**). This is **not** the OAuth-based connector at
> `app/integrations/github.py` (provider key `github`) — both can be
> active on the same install; pick the one that suits your workflow.

A small, per-user opt-in connector that turns a GitHub repository into a
TimeTracker task feed. Uses a **personal access token** (no OAuth dance)
and an HMAC-SHA256 webhook secret to drive task creation and (optionally)
auto-start timers when an issue is assigned.

## What it does

| Event | Action |
|-------|--------|
| `issues / opened` | Creates a Task in the configured default project with `external_ref = github_issue_{n}`, mapped priority (see below), `status="todo"`. |
| `issues / assigned` | If `auto_start_timer` is on **and** the assignee's GitHub login matches a TimeTracker user's `github_username`, starts a timer for that user on the default project. |
| `issues / closed` | Marks the existing task (matched by `external_ref`) as `status="done"`. |
| `ping` | Returns 200 `{"ok": true, "message": "Webhook received"}`. |
| Anything else | 422 (unhandled event). |

A manual **Sync now** also pulls the first 50 open issues from
`GET /repos/{owner}/{repo}/issues?state=open` and creates any tasks that
don't already exist.

## Priority mapping

Labels are scanned in order and the **first match** wins:

| GitHub label (lowercase) | TimeTracker priority |
|--------------------------|----------------------|
| `bug`, `critical`        | `high`               |
| `enhancement`            | `medium`             |
| anything else            | `low`                |

## Configuration

Open **Integrations → GitHub** (the personal-connector card under
*Personal connectors*) and fill in:

| Field | Stored as | Required | Notes |
|-------|-----------|----------|-------|
| **Personal access token** | `integration.config.github_token` (encrypted) | Yes | Needs `repo` scope to read issues. |
| **Owner**                 | `integration.config.repo_owner` | Yes | e.g. `octocat` |
| **Repository**            | `integration.config.repo_name`  | Yes | e.g. `Hello-World` |
| **Default project**       | `integration.config.default_project_id` | Yes | Pick a TimeTracker project. |
| **Auto-start timer**      | `integration.config.auto_start_timer`   | No | Off by default. |
| **Label filter**          | `integration.config.label_filter` (lowercased)        | No | If set, manual sync only imports issues that carry this label. |
| **Webhook secret**        | `integration.config.webhook_secret` (encrypted)       | Yes (auto-generated) | Auto-filled with `secrets.token_urlsafe(32)` on first save. |

Tokens and the webhook secret are stored encrypted at rest when
`SETTINGS_ENCRYPTION_KEY` is configured (Fernet key, see the rest of
TimeTracker's secret handling). When the key is absent the connector
falls back to plain text and logs a warning.

## Wiring the GitHub webhook

1. Open the integration card and **Save** — this generates the webhook
   secret if one isn't already stored and shows the receiver URL.
2. In GitHub, go to **Repo Settings → Webhooks → Add webhook** with:
   - **Payload URL:** `{base_url}/api/integrations/github/webhook`
   - **Content type:** `application/json`
   - **Secret:** the webhook secret from the card
   - **Events:** just **Issues** (or use *Send me everything* if you
     prefer — the connector responds 422 to anything it doesn't handle).
3. The first delivery is a `ping`; the connector replies 200 with
   `{"ok": true, "message": "Webhook received"}`.

The receiver verifies `X-Hub-Signature-256` with `hmac.compare_digest`
against `webhook_secret` and the **raw** request body, so don't add a
proxy that rewrites the body.

## Linking a TimeTracker user to a GitHub login

`users.github_username` is the join key. The 155 Alembic migration adds
the column; set it from **Profile → Settings** or by an admin updating
the user row. Auto-start-timer events are skipped silently if no
TimeTracker user matches the GitHub assignee.

## Endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/api/integrations/github/webhook` | Signature (HMAC-SHA256) | Receives GitHub events. |
| POST | `/api/integrations/github/sync`    | `@login_required`, admin only | Manual one-shot sync. |
| POST | `/api/integrations/github/config`  | `@login_required` | Save the UI form. |
| POST | `/api/integrations/github/test`    | `@login_required` | Calls `GET /user` to verify the token. |
| GET  | `/api/integrations/github/status`  | `@login_required` | Returns the current config snapshot (without secrets). |

All HTTP calls to `api.github.com` use a 10-second timeout and are
wrapped in `try/except requests.RequestException`.

## Operational notes

- The connector is **read-only on GitHub** — it never opens issues or
  posts comments.
- `external_ref` on the `tasks` table is indexed; the connector
  de-duplicates by `(project_id, external_ref)` so re-deliveries of the
  same `issues / opened` event are safe.
- Manual sync also writes `integration.last_sync_at` /
  `last_sync_status`, surfaced on the existing Integrations health
  dashboard.
- The connector degrades gracefully: if the integration row is missing
  or `is_active=False`, every method returns
  `{"ok": false, "error": "Integration not configured"}` without
  raising.
- Tokens never appear in logs — they're truncated to `prefix...` via an
  internal helper.
