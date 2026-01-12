# TimeTracker Mobile App

Flutter mobile application for Android and iOS that integrates with the TimeTracker REST API.

## Features

- ⏱️ **Time Tracking** - Start, stop, and manage timers
- 📊 **Projects & Tasks** - View and select projects and tasks
- 📝 **Time Entries** - View and manage time entries with calendar
- 🔄 **Offline Support** - Work offline with automatic sync
- 🔐 **Secure Authentication** - Token-based authentication with secure storage

## Setup

### Prerequisites

- Flutter SDK 3.0.0 or higher
- Android Studio / Xcode for platform-specific setup

### Installation

1. Install dependencies:
```bash
flutter pub get
```

2. Run code generation (for Hive adapters):
```bash
flutter pub run build_runner build
```

3. Run the app:
```bash
flutter run
```

## Configuration

### Getting an API Token

Before connecting the mobile app, you need to create an API token:

1. **Log in to TimeTracker Web App** as an administrator
2. Navigate to **Admin > API Tokens** (`/admin/api-tokens`)
3. Click **"Create Token"**
4. Fill in the required information:
   - **Name**: A descriptive name (e.g., "Mobile App - John")
   - **User**: Select the user this token will authenticate as
   - **Scopes**: Select the following permissions:
     - `read:projects` - View projects
     - `read:tasks` - View tasks
     - `read:time_entries` - View time entries
     - `write:time_entries` - Create and update time entries
   - **Expires In**: Optional expiration period (leave empty for no expiration)
5. Click **"Create Token"**
6. **Important**: Copy the generated token immediately - you won't be able to see it again!
   - Token format: `tt_<32_random_characters>`
   - Example: `tt_abc123def456ghi789jkl012mno345pq`

### Connecting the App

1. **Launch the app** on your device
2. On the login screen, enter:
   - **Server URL**: Your TimeTracker server URL (e.g., `https://your-server.com`)
     - Do not include a trailing slash
     - Use `http://` for local development or `https://` for production
   - **API Token**: Paste the token you copied from the web app
3. Tap **"Login"**
4. The app will validate your connection and navigate to the timer screen if successful

### Troubleshooting

**"Invalid API token" error:**
- Verify the token starts with `tt_`
- Check that the token hasn't expired
- Ensure the token has the required scopes
- Try creating a new token in the web app

**"Connection failed" error:**
- Verify the server URL is correct and accessible
- Check your internet connection
- Ensure the server is running and the API is accessible
- For local development, use `http://localhost:5000` or your local IP address

**Offline Mode:**
- The app works offline and will sync when connection is restored
- Time entries created offline are queued and synced automatically
- Timer status is cached locally for offline viewing

## Architecture

The app follows clean architecture principles:

- **Presentation Layer** (`lib/presentation/`) - UI screens and widgets
- **Domain Layer** (`lib/domain/`) - Business logic and use cases
- **Data Layer** (`lib/data/`) - API client, local storage, models
- **Core** (`lib/core/`) - Configuration, themes, constants

## API Integration

The app integrates with the TimeTracker REST API (`/api/v1/`):

- Timer endpoints: `/api/v1/timer/start`, `/api/v1/timer/stop`, `/api/v1/timer/status`
- Time entries: `/api/v1/time-entries`
- Projects: `/api/v1/projects`
- Tasks: `/api/v1/tasks`

See the main project's API documentation for details.

## Building

### Android

```bash
flutter build apk --release
# or
flutter build appbundle --release
```

### iOS

```bash
flutter build ios --release
```

Then open Xcode to archive and distribute.
