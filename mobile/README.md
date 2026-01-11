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

1. Launch the app
2. Enter your TimeTracker server URL (e.g., `https://your-server.com`)
3. Enter your API token (obtained from Admin > API Tokens in the web app)
4. Start tracking time!

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
