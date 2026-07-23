# TimeTracker Browser Extension

Chromium (Chrome, Edge, Brave, etc.) Manifest V3 extension for starting and stopping timers against a self-hosted TimeTracker instance. Implements [issue #700](https://github.com/DRYTRIX/TimeTracker/issues/700).

## Features

- Connect with username/password (`POST /api/v1/auth/login`) or paste an existing `tt_…` API token
- Start / stop the active project timer
- Toolbar badge with elapsed time and a red clock icon while running
- Searchable project list (favorites first when available)
- Optional task + notes on start
- Quick-create task or project (project requires an existing client)

Uses the same `/api/v1` surface as the [desktop](../desktop/) and [mobile](../mobile/) apps. It does **not** use session cookies or Socket.IO.

## Load unpacked (development)

1. Open Chrome/Edge → **Extensions** → enable **Developer mode**.
2. Click **Load unpacked** and select this `browser-extension/` directory.
3. Open the extension **Options** (or right-click the toolbar icon → Options).
4. Enter your TimeTracker **base URL** (e.g. `https://timetracker.example.com` or `http://localhost:8080`).
5. Either:
   - Sign in with username and password, or
   - Paste an API token from **Admin → API tokens** (or a token from a previous app login).
6. Allow host access when the browser prompts you.
7. Use the toolbar popup to start/stop timers.

## Required API scopes

Password login mints a broad app token (`read:*` / `write:*` or `admin:all`).

If you create a token manually, include at least:

| Scope | Purpose |
|-------|---------|
| `read:time_entries` | Timer status |
| `write:time_entries` | Start / stop |
| `read:projects` | Project list + favorites |
| `write:projects` | Quick-create project |
| `read:tasks` / `write:tasks` | Task list + quick-create |
| `read:clients` | Client picker for new projects |
| `read:users` | Preferred for `GET /api/v1/users/me` session check |

## How it works

```
Options → request host permission → GET /api/v1/info → login or validate token
Background alarm (~15s unpacked; Chrome may throttle packed builds to ~1 min)
  → GET /api/v1/timer/status → badge text + idle/running icons
Popup → start/stop/create via /api/v1/timer|projects|tasks|clients
```

Credentials are stored in `chrome.storage.local` (`server_url`, `api_token`).

## OIDC-only servers

`POST /api/v1/auth/login` requires local username/password. If your install uses OIDC only, create an API token in the admin UI and paste it in the extension settings.

## Layout

```
browser-extension/
  manifest.json
  background.js      # alarm poll, badge, icon
  popup.html|js|css  # timer UI + quick create
  options.html|js    # connect / disconnect
  lib/api.js         # /api/v1 client
  icons/             # idle + running PNGs
```

## Not in this version

- Chrome Web Store packaging / signed CRX CI
- Firefox-specific packaging
- Pause / resume UI (API endpoints already exist)
- Page content scripts / automatic project detection
- OIDC device flow inside the extension
