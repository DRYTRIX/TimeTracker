# TimeTracker Mobile App

Flutter mobile application for Android and iOS that integrates with the TimeTracker REST API.

## Features

- ⏱️ **Time Tracking** - Start, stop, and manage timers
- 📊 **Projects & Tasks** - View and select projects and tasks
- 📝 **Time Entries** - View and manage time entries with calendar
- 🔄 **Offline Support** - Work offline with automatic sync
- 🔐 **Secure Authentication** - Sign in with your web username and password; the app obtains an API token in the background for the same basics access as the web app

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

### Signing in

Use the same **username and password** you use to log in to the TimeTracker web app. The mobile app signs you in via the API and obtains an API token in the background, giving you the same basics access (timer, time entries, projects, tasks) as on the web.

1. **Launch the app** on your device
2. On the login screen, enter:
   - **Server URL**: The base URL of your TimeTracker server (e.g., `https://your-server.com`). Use HTTPS if your server uses SSL.
   - **Username**: Your web login username
   - **Password**: Your web login password
3. Tap **"Login"**
4. The app will validate your credentials and navigate to the home screen if successful

### Server URL and HTTPS

The default TimeTracker deployment uses **docker-compose** with **NGINX** on ports 80 and 443 (HTTPS). Use your server’s HTTPS URL (e.g. `https://your-server.com`) with no port unless you use a custom one.

- **Production:** Use a valid certificate (e.g. Let’s Encrypt) so the app can connect without certificate errors.
- **Local / testing:** Use a trusted CA (e.g. [mkcert](https://github.com/FiloSottile/mkcert)) for HTTPS, or HTTP only if your setup serves the API over HTTP (e.g. dev without NGINX).

### Troubleshooting

**"Invalid username or password" error:**
- Use the same username and password you use on the web app
- Ensure the server URL is correct and the server is reachable

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
