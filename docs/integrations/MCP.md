# MCP server (Model Context Protocol)

TimeTracker ships an optional **MCP sidecar** so AI assistants (Cursor, Claude, ChatGPT, local agents) can read and write data under the same rules as the web UI and REST API.

The server is a separate process (`mcp_server/`), not inside the gunicorn/eventlet worker. It calls `/api/v1` with a Bearer token.

## Security model

- **Toolset from the token owner.** Admins get admin tools; everyone else gets the personal time-tracking toolset. Override with `MCP_TOOLSET=user|admin|admin_readonly`.
- **Narrow scopes for user connections:**  
  `read:users,read:projects,read:tasks,read:time_entries,write:time_entries`  
  (+ `read:time_approvals,write:time_approvals` when using unconfirmed agent entries).
- **No outbound actions.** No tools send email, Peppol/SDI, or charge payments.
- Writes use `confirm: true` (and MCP `destructiveHint` where relevant). `log_time` without confirm returns a **preview** only.
- Agent-written entries use `source=agent`. With `unconfirmed: true`, the server requests approval via the existing time-entry approval flow.
- Audit log includes `X-MCP-Tool` when present.

## Local (stdio)

1. Create a personal API token (`tt_…`) with the scopes above (Admin → API tokens).
2. Configure your MCP client:

```json
{
  "mcpServers": {
    "timetracker": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "/path/to/TimeTracker",
      "env": {
        "TIMETRACKER_BASE_URL": "https://your-timetracker.example",
        "TIMETRACKER_API_TOKEN": "tt_…"
      }
    }
  }
}
```

Install deps once: `pip install -r mcp_server/requirements.txt`.

## Remote (Streamable HTTP)

```bash
docker compose --profile mcp up -d
```

Env (see `env.example`):

- `MCP_API_TOKEN` — token used by the sidecar to call the app (or configure per-client OAuth; see below)
- `MCP_TOOLSET=auto|user|admin|admin_readonly`
- `TIMETRACKER_BASE_URL=http://app:8080`

Nginx proxies `/mcp` to the sidecar when the profile is running. Resource metadata:  
`GET /.well-known/oauth-protected-resource` (RFC 9728).

### OAuth connect

1. Authorization server metadata: `/.well-known/oauth-authorization-server`
2. Limited dynamic client registration: `POST /oauth/register` (public clients, localhost / Cursor / Claude / VS Code redirect URIs)
3. Authorization code + PKCE as usual (`/oauth/authorize`, `/oauth/token`)

Scope presets on register: `user` (default), `admin`, `admin_readonly` (`scope_preset` / `timetracker_scope_preset`).

## User tools

| Tool | Notes |
|------|--------|
| `whoami` | User, timezone, standard hours, modules |
| `list_my_projects` / `find_project` | Favorites first when available |
| `log_time` / `log_time_batch` | Preview unless `confirm`; `source=agent`; optional `unconfirmed` |
| `start_timer` / `stop_timer` / `restart_timer` / `timer_status` | |
| `list_my_time_entries` / `update_my_time_entry` / `delete_my_time_entry` | Own entries |
| `my_week` | Hours vs standard; empty days |

## Admin tools (admin token)

Clients, projects, tasks, expenses, quotes, invoices (create/draft only — no send), reports, and `log_time_for_user`.  
Read-only mode registers only read tools (`MCP_TOOLSET=admin_readonly` or a token with no write scopes).

| Tool | Notes |
|------|--------|
| `list_users` / `list_clients` / `get_client` | |
| `list_projects_admin` / `get_project` / `create_project` / `update_project` | |
| `list_tasks` / `create_task` / `update_task` / `delete_task` | Any project |
| `list_time_entries_admin` / `get_time_entry_admin` | Any user |
| `update_time_entry_admin` / `delete_time_entry_admin` | Confirm; delete refused when invoiced |
| `bulk_update_time_entries` | `billable` / `project_id` / `task_id`; confirm + preview |
| `log_time_for_user` | Preview unless confirm; `source=agent` |
| `list_expenses` / `get_expense` / `create_expense` / `update_expense` | |
| `approve_expense` / `reject_expense` / `list_expense_categories` | |
| `list_quotes` / `get_quote` / `create_quote` / `update_quote` | |
| `list_project_costs` / `create_project_cost` | Non-hourly costs |
| `list_invoices` / `get_invoice` / `create_invoice` / `update_invoice` | Drafts; no send |
| `delete_invoice` | Drafts only; soft-cancel |
| `list_invoice_time_entries` | Entries linked via `invoice_time_links` (line `time_entry_ids` is a cache) |
| `invoice_from_unbilled` / `invoice_generate_from_time` / `update_invoice_items` | No send |
| `get_invoice_pdf` / `get_invoice_pdf_url` | PDF as base64 (or path); no email/Peppol |
| `report_summary` / `report_unbilled` / `report_expenses` | |
| `report_budget` / `report_missing_hours` | Health + estimates + alerts; closing the month |

## API additions used by MCP

- `POST /api/v1/time-entries/preview`
- `POST /api/v1/time-entries/bulk` actions: `set_billable`, `set_project`, `set_task`, …
- `GET /api/v1/reports/unbilled` (`read:reports`, admin)
- `GET /api/v1/reports/expenses` / `GET /api/v1/reports/missing-hours` (admin)
- `GET /api/v1/expense-categories`
- `source=agent` on time entries; list filter `?source=agent`
- Duration-only create: `date` + `duration_seconds` on `POST /api/v1/time-entries`
