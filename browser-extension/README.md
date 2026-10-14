# TimeTracker Browser Extension

Chromium (Chrome, Edge, Brave, etc.) Manifest V3 extension for starting and stopping timers against a self-hosted TimeTracker instance. Apple-inspired redesign (v5.19): a three-tab popup (Timer / Insights / Recents), keyboard shortcuts, right-click tracking, and a redesigned settings page. Same `/api/v1` surface as the [desktop](../desktop/) and [mobile](../mobile/) apps — session cookies and Socket.IO are not used.

## Features

### Timer
- Connect with username/password (supports 2FA) or paste an existing `tt_…` API token
- One search field for projects, tasks, and clients (keyboard-first: `/` to focus, arrows + Enter to pick)
- Recent and favorites chips for one-click starts; last-used project preselected
- Optional task + notes, with note suggestions pulled from your recent entries
- Inline create for projects and tasks
- Running view: large live clock, recording indicator, pause / resume / stop, quick note (updates the running entry)
- Toolbar badge with elapsed time (red while recording, gray while paused; toggleable)

### Insights (new)
- Today: tracked total (including the running timer), billable, entry count
- Weekly goal progress from `/api/v1/weekly-goals`
- Last-7-days bar chart and top projects (from `/api/v1/reports/summary` + `/api/v1/time-entries`)

### Recents (new)
- Entries of the last 7 days grouped by day, with one-click "track again" (restarts the same project/task)
- Link into the full history on your server

### Everywhere
- Global keyboard shortcuts: `Ctrl/Cmd+Shift+S` start/stop timer, `Ctrl/Cmd+Shift+T` open popup (customizable at `chrome://extensions/shortcuts`)
- Right-click any selected text → *Track time: "…"* — starts the last-used project with the selection as note
- Server-authoritative idle flow (Issue #722): the server arms the "Still working?" prompt, all devices share one check (first answer wins), and the extension never stops the timer itself. The idle timeout and unanswered action are **read from the server** and shown read-only in Settings — they are admin-managed, not per-user.
- Auto light/dark design system (Apple-style tokens in `styles/tokens.css`)

## Load unpacked (development)

1. Open Chrome/Edge → **Extensions** → enable **Developer mode**.
2. Click **Load unpacked** and select this `browser-extension/` directory.
3. Open the extension **Options** (or right-click the toolbar icon → Options).
4. Enter your TimeTracker **base URL** (e.g. `https://timetracker.example.com` or `http://localhost:8080`).
5. Either sign in with username + password (2FA code prompt included) or paste an API token from **Admin → API tokens**.
6. Allow host access when the browser prompts you.

### Preview the UI without the extension runtime

The popup and options pages run in a plain browser with demo data via `dev/mock.js` (a no-op inside the real extension):

```bash
cd browser-extension
python -m http.server 8090
# open http://localhost:8090/popup/popup.html
# hash options: #idle (idle view), #paused (paused timer)
```

## Package for distribution

```bash
cd browser-extension
npm run zip
```

Creates `dist/timetracker-extension-vX.Y.Z.zip` ready for Chrome Web Store upload or sideload.

## Required API scopes

Password login mints a broad app token (`read:*` / `write:*` or `admin:all`).

If you create a token manually, include at least:

| Scope | Purpose |
|-------|---------|
| `read:time_entries` / `write:time_entries` | Timer status, start/stop, recents, quick note |
| `read:projects` / `write:projects` | Project list, favorites, quick-create |
| `read:tasks` / `write:tasks` | Task list + quick-create |
| `read:clients` / `write:clients` | Client names, inline create |
| `read:users` | Session check (`users/me`) + weekly goals |
| `read:reports` | Insights tab (summary report) |

Without `read:reports` / `read:users` the Insights tab degrades gracefully (zeros, no goal card).

## How it works

```
Options → request host permission → GET /api/v1/info → login (+2FA) or validate token
Background alarm (~15s unpacked; Chrome may throttle packed builds to ~1 min)
  → GET /api/v1/timer/status → badge text + icon (also returns the server-managed
    idle_timeout_minutes / idle_unanswered_action applied locally)
Popup → timer controls, unified project search, insights, recents
Commands / context menu → start/stop via chrome.commands + contextMenus
```

Credentials are stored in `chrome.storage.local` (`server_url`, `api_token`).

## Idle detection (server-authoritative)

`GET /api/v1/timer/status` returns the install-wide policy: `idle_timeout_minutes`, `idle_unanswered_action` (`review` or `auto_stop`). The extension applies the timeout to `chrome.idle` and renders the server-armed prompt (`idle_notified`) — answers go through `POST /api/v1/timer/idle-response`, the server sweep resolves unanswered checks, and unanswered timers in `review` mode keep running and are flagged (`needs_review`) with a local notification. Heartbeats are only sent while the OS reports user activity, so closing the browser never stops the timer — time keeps accruing server-side.

## Layout

```
browser-extension/
  manifest.json        # MV3, commands, contextMenus
  background.js        # poll, badge, icons, idle grace, heartbeat, shortcuts, context menu
  popup/               # popup.html/css + main.js, timer-tab.js, insights-tab.js,
                       # recents-tab.js, search.js
  options/             # options.html/css/js — connect (password+2FA / token),
                       # read-only server policy, preferences
  styles/tokens.css    # shared Apple-style design tokens (light/dark)
  lib/api.js           # /api/v1 client
  lib/format.js        # formatting/grouping helpers (tested)
  lib/icons.js         # inline SVG icon set
  dev/mock.js          # browser-preview shim with demo data (no-op in production)
  icons/               # toolbar icons (idle + running)
  build/zip.js         # packager
  test/                # node --test suite (api + helpers)
```

## OIDC-only servers

`POST /api/v1/auth/login` requires local username/password. If your install uses OIDC only, create an API token in the admin UI and paste it in the extension settings.

## Not in this version

- Firefox-specific packaging
- Page content scripts / automatic project detection from the active tab
- OIDC device flow inside the extension
