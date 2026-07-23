# Mobile and Desktop Apps

This directory contains documentation for the TimeTracker mobile (Flutter) and desktop (Electron) applications.

## Overview

The TimeTracker mobile and desktop apps provide native client applications that connect to the TimeTracker backend via REST API.

## Mobile App (Flutter)

Located in `mobile/` directory.

### Features

- Time tracking with start/pause/resume/stop timer
- Project and task management
- Time entries with filters and offline queue
- Workday clock-in/out and breaks
- Finance & workforce (invoices, expenses, time-off, timesheets, approvals)
- Offline support with periodic automatic sync
- Secure token-based authentication (username/password login → API token)
- Server discovery via `GET /api/v1/info` (rejects non-TimeTracker hosts and unfinished setup)

### Setup

See [mobile/README.md](../../mobile/README.md) for setup instructions.

### Build

- Android: `flutter build apk` or `flutter build appbundle`
- iOS: `flutter build ios` then archive in Xcode

## Desktop App (Electron)

Located in `desktop/` directory.

### Features

- Time tracking with system tray integration (start/stop/pause/resume)
- Workday clock-in/out and break controls
- Project and task management, Kanban board
- Time entries, reports summary
- Invoices, expenses, payments, mileage, quotes, recurring invoices, credit notes
- CRM: leads, deals, client contacts and notes
- Workforce: timesheets, time-off, approvals
- Offline support for timer and time-entry mutations
- Username/password login → API token (`tt_…`)
- Global keyboard shortcuts (timer toggle, show window)

### Setup

See [desktop/README.md](../../desktop/README.md) for setup instructions.

### Build

- Windows: `npm run build:win`
- macOS: `npm run build:mac`
- Linux: `npm run build:linux`

Gap analysis vs the webapp: [DESKTOP_WEBAPP_GAP.md](DESKTOP_WEBAPP_GAP.md).

## API Integration

Both apps use the TimeTracker REST API v1 (`/api/v1/`). See [API Documentation](../api/REST_API.md) for details.

### Authentication

1. **Mobile app**: Sign in with your web username and password; the server returns an API token (`tt_…`) which is stored securely. Changing the **Server URL** in Settings probes the new host with your saved token before persisting the change.
2. **Desktop app**: Two-step wizard (test server, then username/password). The app calls `POST /api/v1/auth/login` and stores the returned token. Optional long-lived tokens can still be created under **Admin → Security & Access → API tokens**.
3. Clients validate the server with `GET /api/v1/info` (and respect `setup_required` when the installation is not finished) and validate the token with authenticated API calls.

### Required API Scopes

- `read:time_entries` - View time entries and timer status (desktop session check fallback; mobile login token includes this)
- `write:time_entries` - Create/update time entries and control timer
- `read:projects` - View projects
- `read:tasks` - View tasks
- `read:users` - Optional on desktop tokens; preferred so `GET /api/v1/users/me` can be used for session verification
- Additional scopes as needed for invoices, CRM, attendance, etc. (password-login tokens typically include broad app scopes)

### API Endpoints Used

- `GET /api/v1/info` - API metadata (includes `setup_required` when the server install is not complete); used for discovery without auth
- `POST /api/v1/auth/login` - Username/password → token
- `GET /api/v1/timer/status` - Get active timer status
- `POST /api/v1/timer/start` - Start timer
- `POST /api/v1/timer/pause` / `resume` / `stop` - Timer control
- `GET /api/v1/attendance/status`, `POST /api/v1/workday/start|end`, attendance break start/end
- `GET /api/v1/time-entries` - List time entries
- `POST /api/v1/time-entries` - Create time entry
- `PUT /api/v1/time-entries/{id}` - Update time entry
- `GET /api/v1/projects` / `tasks` / `clients` / `reports/summary`
- Finance, CRM, Kanban, and workforce routes as used by the desktop views
- `DELETE /api/v1/time-entries/{id}` - Delete time entry
- `GET /api/v1/projects` - List projects
- `GET /api/v1/tasks` - List tasks

## Offline Support

Both apps support offline operation:

1. **Local Storage**: Time entries, projects, and tasks are cached locally
2. **Sync Queue**: Operations performed offline are queued for sync
3. **Automatic Sync**: When connection is restored, queued operations are processed
4. **Conflict Resolution**: Server data takes precedence on conflict

The mobile app sends an **`Idempotency-Key`** on queued **`POST /api/v1/time-entries`** creates so retries after connectivity drops do not duplicate entries. See [REST API: Idempotent time entry creation](../api/REST_API.md#idempotent-time-entry-creation).

## Development

### Mobile App Development

1. Install Flutter SDK
2. Run `flutter pub get` in `mobile/` directory
3. Run `flutter run` to start development

### Desktop App Development

1. Install Node.js 18+
2. Run `npm install` in `desktop/` directory
3. Run `npm run dev` to start development

## Distribution

### Mobile Apps

- Android: Generate signed APK/AAB and submit to Google Play Store
- iOS: Archive and submit to Apple App Store (requires Apple Developer account)

### Desktop Apps

- Windows: NSIS installer created in `dist/` directory
- macOS: DMG installer (requires code signing for distribution)
- Linux: AppImage and .deb packages

## Version Management

App versions should align with the backend version (see `setup.py` for current version). Update version numbers in:

- Mobile: `mobile/pubspec.yaml`
- Desktop: `desktop/package.json`
- Backend: `setup.py`

## Support

For issues or questions:

1. Check the main project README
2. Review API documentation
3. Check app-specific README files
4. Open an issue on GitHub
