# Desktop App Settings Configuration

The TimeTracker desktop app stores connection and preference settings via Electron's `electron-store`.

## First sign-in (connection wizard)

On first launch (or whenever credentials are missing), the app shows a **two-step** flow:

1. **Step 1 — Server**  
   Enter the base URL of your TimeTracker server (e.g. `https://timetracker.example.com` or `http://192.168.1.50:5000`). If you omit the scheme, `https://` is assumed when validating. Use **Test server** to confirm the host speaks the TimeTracker API (`GET /api/v1/info` must return JSON with `api_version: "v1"`).

2. **Step 2 — Sign in**  
   Enter your TimeTracker **username and password**. The app calls `POST /api/v1/auth/login`, stores the returned `tt_…` API token, and verifies the session (`GET /api/v1/users/me` or timer status fallback).

Command-line `--server-url` / `TIMETRACKER_SERVER_URL` can pre-fill the stored server URL and skip typing it in step 1; you still complete username/password sign-in unless a valid token is already saved.

## Settings Location

Settings are stored using Electron's secure storage (`electron-store`), which saves data in a JSON file in the user's application data directory:

- **Windows**: `%APPDATA%\timetracker-desktop\config.json`
- **macOS**: `~/Library/Application Support/timetracker-desktop/config.json`
- **Linux**: `~/.config/timetracker-desktop/config.json`

## Settings Access

Users can access settings in two ways:

### 1. Settings Screen (In-App)

1. Open the TimeTracker desktop app
2. Click on "Settings" in the navigation menu
3. The settings screen will display:
   - **Server URL**: Current server URL (editable)
   - **Username**: Account used for desktop login
   - **Password**: Optional; enter to re-authenticate and refresh the API token
   - **Theme** and **offline sync** controls
   - **Save Settings** button

### 2. Command Line Arguments

The server URL can be set via command line when launching the app:

```bash
# Windows
TimeTracker.exe --server-url https://your-server.com

# Linux/macOS
./TimeTracker --server-url https://your-server.com
```

### 3. Environment Variable

The server URL can also be set via environment variable:

```bash
# Windows
set TIMETRACKER_SERVER_URL=https://your-server.com
TimeTracker.exe

# Linux/macOS
export TIMETRACKER_SERVER_URL=https://your-server.com
./TimeTracker
```

## Settings Features

### Server URL Configuration

- **Validation**: URLs are normalized (trailing slashes removed). If you type a host without a scheme (e.g. `internal.company.com:8443`), `https://` is prepended for validation.
- **Persistence**: Server URL is saved to secure storage and persists across app restarts
- **Change Detection**: The app reinitializes the API client when you re-authenticate after changing the server URL

### Authentication

- Login uses username/password against `POST /api/v1/auth/login`
- The returned Bearer token (`tt_…`) is stored securely and sent on `/api/v1` requests
- Long-lived tokens created in **Admin → Security & Access → API tokens** remain valid for API use; the React desktop UI prefers password login

### Connection Testing

- **Test server** probes `GET /api/v1/info` without auth
- After sign-in, the app validates the session and polls periodically
- Diagnostics explain common failures (TLS, DNS, refused connection, unauthorized)

## Renderer stack

The primary UI is **React + Vite** under `desktop/src/renderer-react/`, built to `desktop/dist-renderer/`. The legacy vanilla renderer under `desktop/src/renderer/` is retained only as a fallback.
