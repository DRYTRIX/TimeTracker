# Mobile and Desktop Apps

This directory contains documentation for the TimeTracker mobile (Flutter) and desktop (Electron) applications.

## Overview

The TimeTracker mobile and desktop apps provide native client applications that connect to the TimeTracker backend via REST API.

## Mobile App (Flutter)

Located in `mobile/` directory.

### Features

- Time tracking with start/stop timer
- Project and task management
- Time entries with calendar view
- Offline support with automatic sync
- Secure token-based authentication
- Background timer updates

### Setup

See [mobile/README.md](../../mobile/README.md) for setup instructions.

### Build

- Android: `flutter build apk` or `flutter build appbundle`
- iOS: `flutter build ios` then archive in Xcode

## Desktop App (Electron)

Located in `desktop/` directory.

### Features

- Time tracking with system tray integration
- Project and task management
- Time entries viewing
- Offline support
- Secure token-based authentication
- Global keyboard shortcuts (planned)

### Setup

See [desktop/README.md](../../desktop/README.md) for setup instructions.

### Build

- Windows: `npm run build:win`
- macOS: `npm run build:mac`
- Linux: `npm run build:linux`

## API Integration

Both apps use the TimeTracker REST API v1 (`/api/v1/`). See [API Documentation](../api/REST_API.md) for details.

### Authentication

1. Generate an API token from the web admin panel: Admin > API Tokens
2. Enter the server URL in the app
3. Enter the API token
4. The app will validate the token and store it securely

### Required API Scopes

- `read:time_entries` - View time entries
- `write:time_entries` - Create/update time entries and control timer
- `read:projects` - View projects
- `read:tasks` - View tasks

### API Endpoints Used

- `GET /api/v1/info` - API version and health check
- `GET /api/v1/timer/status` - Get active timer status
- `POST /api/v1/timer/start` - Start timer
- `POST /api/v1/timer/stop` - Stop timer
- `GET /api/v1/time-entries` - List time entries
- `POST /api/v1/time-entries` - Create time entry
- `PUT /api/v1/time-entries/{id}` - Update time entry
- `DELETE /api/v1/time-entries/{id}` - Delete time entry
- `GET /api/v1/projects` - List projects
- `GET /api/v1/tasks` - List tasks

## Offline Support

Both apps support offline operation:

1. **Local Storage**: Time entries, projects, and tasks are cached locally
2. **Sync Queue**: Operations performed offline are queued for sync
3. **Automatic Sync**: When connection is restored, queued operations are processed
4. **Conflict Resolution**: Server data takes precedence on conflict

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

App versions should align with the backend version (currently 4.9.16). Update version numbers in:

- Mobile: `mobile/pubspec.yaml`
- Desktop: `desktop/package.json`
- Backend: `setup.py`

## Support

For issues or questions:

1. Check the main project README
2. Review API documentation
3. Check app-specific README files
4. Open an issue on GitHub
