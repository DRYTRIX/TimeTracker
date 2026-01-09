---
name: Mobile and Desktop Apps
overview: Create complete Android/iOS mobile apps using Flutter and lightweight Windows/Linux/macOS desktop applications using Electron that integrate with the existing TimeTracker REST API.
todos:
  - id: flutter_setup
    content: Set up Flutter project structure with clean architecture (data/domain/presentation layers)
    status: pending
  - id: electron_setup
    content: Set up Electron project with main/renderer process separation and build configuration
    status: pending
  - id: api_client_mobile
    content: Implement Flutter API client with Dio, token auth, and error handling
    status: pending
  - id: api_client_desktop
    content: Implement Electron API client (Axios) with token auth and error handling
    status: pending
  - id: auth_flow
    content: Implement authentication flows for both platforms with secure token storage
    status: pending
  - id: timer_mobile
    content: Implement timer functionality in Flutter (start/stop/status with background updates)
    status: pending
  - id: timer_desktop
    content: Implement timer functionality in Electron with system tray integration
    status: pending
  - id: offline_storage
    content: Set up local databases (Hive/SQLite for mobile, IndexedDB/SQLite for desktop)
    status: pending
  - id: offline_sync
    content: Implement offline sync with conflict resolution for both platforms
    status: pending
  - id: projects_tasks_ui
    content: Build projects and tasks UI screens for both platforms
    status: pending
  - id: time_entries_ui
    content: Build time entries listing and editing screens
    status: pending
  - id: settings_ui
    content: Implement settings screens (server URL, API token, sync preferences)
    status: pending
  - id: background_tasks
    content: Implement background timer updates using WorkManager (mobile)
    status: pending
  - id: system_tray
    content: Complete system tray implementation with timer controls (desktop)
    status: pending
  - id: notifications
    content: Implement push notifications for timer events on both platforms
    status: pending
  - id: platform_polish
    content: Platform-specific polish (Material Design 3 for Android, HIG for iOS, native desktop features)
    status: pending
  - id: testing
    content: Write unit, widget, and integration tests for both applications
    status: pending
  - id: build_config
    content: Configure builds for all target platforms (Android APK/AAB, iOS archive, Electron installers)
    status: pending
  - id: documentation
    content: Create user guides and API integration documentation
    status: pending
  - id: distribution
    content: Set up distribution pipelines (app stores for mobile, installers for desktop)
    status: pending
---

# Mobile and Desktop Apps Development Plan

## Overview

This plan covers developing:

1. **Mobile Apps** (Android & iOS) - Built with Flutter for cross-platform code sharing
2. **Desktop Apps** (Windows/Linux/macOS) - Built with Electron for web-based cross-platform deployment

Both applications will integrate with the existing TimeTracker REST API (`/api/v1/`) that uses token-based authentication.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    TimeTracker Backend                       │
│              (Flask + PostgreSQL + REST API)                 │
│                  Base URL: /api/v1/                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ REST API
                            │ (Bearer Token Auth)
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
┌───────▼────────┐                    ┌────────▼────────┐
│ Flutter Mobile │                    │ Electron Desktop│
│   (Android/iOS)│                    │ (Win/Linux/macOS)│
│                │                    │                 │
│ - Shared API   │                    │ - Shared API    │
│   Client       │                    │   Client        │
│ - Local Storage│                    │ - Local Storage │
│ - Background   │                    │ - System Tray   │
│   Tasks        │                    │ - Notifications │
└────────────────┘                    └─────────────────┘
```

## Phase 1: Flutter Mobile Apps (Android & iOS)

### 1.1 Project Setup and Architecture

**Location**: `mobile/` directory at project root

**Structure**:

```
mobile/
├── android/                 # Android platform files
├── ios/                     # iOS platform files  
├── lib/
│   ├── main.dart           # App entry point
│   ├── core/
│   │   ├── config/         # App configuration
│   │   ├── constants/      # Constants and enums
│   │   └── themes/         # App theming
│   ├── data/
│   │   ├── api/            # REST API client
│   │   ├── local/          # Local database (Hive/SQLite)
│   │   └── models/         # Data models
│   ├── domain/
│   │   ├── repositories/   # Repository interfaces
│   │   └── usecases/       # Business logic
│   ├── presentation/
│   │   ├── screens/        # UI screens
│   │   ├── widgets/        # Reusable widgets
│   │   └── providers/      # State management (Riverpod/Provider)
│   └── utils/
│       ├── auth/           # Authentication utilities
│       └── storage/        # Secure storage
├── pubspec.yaml            # Dependencies
└── README.md
```

**Key Dependencies**:

- `dio` - HTTP client for API calls
- `hive` or `sqflite` - Local database for offline support
- `riverpod` or `provider` - State management
- `flutter_secure_storage` - Secure token storage
- `workmanager` - Background tasks
- `local_notifications` - Push notifications
- `permission_handler` - Platform permissions

### 1.2 Core Features Implementation

#### 1.2.1 Authentication & API Client

**API Client** (`lib/data/api/api_client.dart`):

- Base URL configuration from user input or auto-discovery
- Token-based authentication using Bearer tokens
- Request/response interceptors for error handling
- Retry logic for network failures
- Token refresh mechanism (if implemented)

**Authentication Flow**:

1. User enters server URL (with validation)
2. User provides API token (from web admin panel)
3. Token stored securely using `flutter_secure_storage`
4. Token validated on first API call
5. Persistent login session

**Integration with existing API**:

- Use existing `/api/v1/` endpoints
- Leverage `require_api_token()` decorator from `app/utils/api_auth.py`
- Support scopes: `read:time_entries`, `write:time_entries`, `read:projects`, `read:tasks`

#### 1.2.2 Time Tracking Features

**Timer Management**:

- **Start Timer**: `POST /api/v1/timer/start` with `project_id`, optional `task_id`
- **Stop Timer**: `POST /api/v1/timer/stop`
- **Timer Status**: `GET /api/v1/timer/status` - Poll every 5-10 seconds when active
- Visual timer display with running time
- Background timer updates using `workmanager`
- Persistent timer state (survives app restarts)

**Time Entries**:

- **List Entries**: `GET /api/v1/time-entries` with date filtering
- **Create Entry**: `POST /api/v1/time-entries` for manual entries
- **Update Entry**: `PUT /api/v1/time-entries/{id}`
- **Delete Entry**: `DELETE /api/v1/time-entries/{id}`

**Offline Support**:

- Local database stores time entries when offline
- Sync queue for pending operations
- Background sync when connection restored
- Conflict resolution for concurrent edits

#### 1.2.3 Projects & Tasks

**Projects**:

- **List Projects**: `GET /api/v1/projects?status=active`
- Project filtering and search
- Favorite projects (stored locally)
- Project details view

**Tasks**:

- **List Tasks**: `GET /api/v1/tasks?project_id={id}`
- Task selection when starting timer
- Task status display

#### 1.2.4 UI Screens

**Home/Dashboard Screen**:

- Active timer display (large, prominent)
- Quick start button for most recent project
- Today's time summary
- Recent time entries list

**Timer Screen**:

- Large timer display (minutes:seconds or hours:minutes)
- Project and task selection
- Start/Stop/Pause controls
- Notes input field
- Timer notes can be added on stop

**Projects Screen**:

- List of active projects
- Search and filter
- Project cards with time spent today
- Tap to view details or start timer

**Time Entries Screen**:

- Calendar view for selecting date
- List of time entries for selected date
- Swipe to edit/delete
- Manual entry form

**Settings Screen**:

- Server URL configuration
- API token management
- Sync settings (auto-sync, sync interval)
- Theme settings (light/dark mode)
- About and version info

#### 1.2.5 Background Features

**Background Timer**:

- Use `workmanager` for periodic timer updates
- Update local display every minute
- Sync with server periodically
- Show notification when timer is running

**Push Notifications** (Future enhancement):

- Idle detection reminders
- Timer stop reminders
- Sync status notifications

### 1.3 Platform-Specific Features

#### Android

- Material Design 3 UI
- Android 12+ splash screen
- Edge-to-edge display support
- Android 13+ notification permissions
- Background execution limits handling

#### iOS

- iOS Human Interface Guidelines
- Native iOS navigation patterns
- Face ID/Touch ID for secure token storage (optional)
- iOS 14+ widget support (Future)
- Background app refresh configuration

### 1.4 Testing & Deployment

**Testing**:

- Unit tests for business logic
- Widget tests for UI components
- Integration tests for API calls
- Test local database operations

**Build & Release**:

- Android: Generate signed APK/AAB via Gradle
- iOS: Archive and distribute via Xcode
- App Store/Play Store submission
- Version management aligned with backend

## Phase 2: Electron Desktop App (Windows/Linux/macOS)

### 2.1 Project Setup and Architecture

**Location**: `desktop/` directory at project root

**Structure**:

```
desktop/
├── src/
│   ├── main/               # Electron main process
│   │   ├── main.js        # Main entry point
│   │   ├── preload.js     # Preload script
│   │   ├── tray.js        # System tray management
│   │   └── window.js      # Window management
│   ├── renderer/          # Electron renderer (frontend)
│   │   ├── index.html     # Main HTML
│   │   ├── css/           # Styles
│   │   ├── js/            # Frontend JavaScript
│   │   │   ├── api/       # API client
│   │   │   ├── storage/   # Local storage
│   │   │   ├── ui/        # UI components
│   │   │   └── utils/     # Utilities
│   │   └── assets/        # Static assets
│   └── shared/            # Shared code between main/renderer
│       └── config.js      # Configuration
├── package.json           # Dependencies and scripts
├── electron-builder.yml   # Build configuration
└── README.md
```

**Key Dependencies**:

- `electron` - Electron framework
- `electron-store` - Persistent storage
- `axios` - HTTP client
- `dexie` or `better-sqlite3` - Local database
- `auto-updater` (platform-specific) - Auto-update functionality
- `electron-notifications` - Desktop notifications

### 2.2 Core Features Implementation

#### 2.2.1 Main Process Setup

**Window Management** (`src/main/window.js`):

- Create main window (800x600 minimum, 1200x800 default)
- Window state persistence (position, size)
- Minimize to tray option
- Always on top option (optional)
- Multi-monitor support

**System Tray** (`src/main/tray.js`):

- System tray icon with menu
- Quick timer controls from tray
- Active timer display in tooltip
- Context menu: Start Timer, Stop Timer, Show Window, Quit
- Tray icon updates based on timer state

**Preload Script** (`src/main/preload.js`):

- Expose secure APIs to renderer
- IPC communication setup
- Electron API access control

#### 2.2.2 Renderer Process (Frontend)

**UI Framework Options**:

- **Option A**: Vanilla JS + modern CSS (lightweight, fast)
- **Option B**: React/Vue (if more complex UI needed)
- **Recommendation**: Start with vanilla JS for simplicity

**API Client** (`src/renderer/js/api/client.js`):

- Similar structure to Flutter API client
- Base URL configuration
- Token authentication
- Request/response handling
- Error management

**Local Storage** (`src/renderer/js/storage/`):

- Use `electron-store` for settings
- IndexedDB or SQLite for time entries cache
- Offline queue for pending operations

#### 2.2.3 Time Tracking Features

**Timer Functionality**:

- Same API endpoints as mobile app
- `POST /api/v1/timer/start`, `POST /api/v1/timer/stop`, `GET /api/v1/timer/status`
- Persistent timer (survives window close)
- System tray timer display
- Desktop notifications for timer events

**UI Components**:

- Compact timer widget (can be separate small window)
- Full dashboard view
- Project/task selection
- Time entries list
- Settings panel

#### 2.2.4 Desktop-Specific Features

**System Integration**:

- Global keyboard shortcuts (Ctrl+Shift+T to toggle timer)
- Auto-start on login (optional)
- Idle detection using system APIs
- System notifications for timer reminders

**Performance**:

- Lightweight bundle size (<50MB)
- Fast startup time (<2 seconds)
- Low memory footprint
- Efficient background operation

**Offline Support**:

- Local database for cached data
- Offline queue for operations
- Background sync when online
- Conflict resolution

### 2.3 Platform-Specific Configuration

#### Windows

- NSIS installer or MSI package
- Windows 10+ compatibility
- Windows notification API
- Windows registry for auto-start (optional)

#### Linux

- AppImage, .deb, or .rpm packages
- Desktop entry file for app launcher
- XDG desktop integration
- System tray via StatusNotifierItem (AppIndicator)

#### macOS

- DMG installer
- macOS 10.15+ compatibility
- Native macOS notifications
- Menu bar integration (alternative to dock)
- Code signing and notarization for distribution

### 2.4 Build and Distribution

**Build Configuration** (`electron-builder.yml`):

- Multi-platform builds from single codebase
- Code signing certificates (platform-specific)
- Auto-updater configuration
- Icon and branding assets

**Distribution**:

- GitHub Releases for downloadable installers
- Optional: Auto-update server setup
- Version management aligned with backend

## Phase 3: Shared Components and Integration

### 3.1 API Client Library

**Shared API Client** (optional separate package):

- Common API client logic for both mobile and desktop
- TypeScript definitions for API responses
- Request/response models
- Error handling utilities

### 3.2 Backend API Enhancements

**Additional API Endpoints** (if needed):

- WebSocket support for real-time timer updates (optional enhancement)
- Bulk operations endpoint for offline sync
- Health check endpoint with version info

**Existing API Usage**:

- Leverage existing `/api/v1/` endpoints
- Use existing authentication mechanism (`app/utils/api_auth.py`)
- Follow existing API documentation (`docs/api/REST_API.md`)

### 3.3 Documentation

**API Integration Guide**:

- Document how mobile/desktop apps connect to backend
- API token creation instructions
- Common integration patterns
- Troubleshooting guide

**User Guides**:

- Mobile app user manual
- Desktop app user manual
- Setup and configuration instructions
- Offline mode explanation

## Implementation Phases

### Phase 1: Foundation (Weeks 1-2)

- [ ] Set up Flutter project structure
- [ ] Set up Electron project structure
- [ ] Implement basic API client for both platforms
- [ ] Implement authentication flow
- [ ] Basic UI skeleton for both apps

### Phase 2: Core Time Tracking (Weeks 3-4)

- [ ] Timer start/stop functionality
- [ ] Timer status polling
- [ ] Projects and tasks integration
- [ ] Time entries listing
- [ ] Basic offline storage setup

### Phase 3: Enhanced Features (Weeks 5-6)

- [ ] Offline sync implementation
- [ ] Background tasks (mobile)
- [ ] System tray integration (desktop)
- [ ] Notifications
- [ ] Settings and configuration

### Phase 4: Polish & Testing (Weeks 7-8)

- [ ] UI/UX refinements
- [ ] Cross-platform testing
- [ ] Performance optimization
- [ ] Security audit
- [ ] Documentation completion

### Phase 5: Distribution (Week 9+)

- [ ] Build configuration for all platforms
- [ ] Store submission (mobile)
- [ ] Installer creation (desktop)
- [ ] Release and distribution
- [ ] User feedback collection

## Technical Considerations

### Security

- API tokens stored securely (Keychain on iOS, Keystore on Android, encrypted storage on desktop)
- HTTPS required for API communication
- Token validation on app startup
- Secure token transmission only

### Offline Support

- Local database for all core entities
- Sync queue with conflict resolution
- Background sync when connection restored
- Clear offline/online status indicators

### Performance

- Efficient API polling intervals
- Lazy loading for large lists
- Image/asset optimization
- Memory management
- Battery optimization (mobile)

### Error Handling

- Network error handling with retry logic
- API error response parsing
- User-friendly error messages
- Offline mode graceful degradation

## Dependencies on Existing Codebase

**No Backend Changes Required**:

- Existing REST API (`app/routes/api_v1.py`) is sufficient
- Existing authentication (`app/utils/api_auth.py`) works as-is
- Existing API token management (`app/services/api_token_service.py`) supports the apps
- Existing endpoints cover all required functionality

**Optional Enhancements** (Future):

- WebSocket endpoint for real-time updates
- Bulk sync endpoint for offline operations
- Push notification service (FCM/APNS) integration

## Success Metrics

- Mobile apps support all core time tracking features
- Desktop app is lightweight (<50MB, <2s startup)
- Both apps work seamlessly offline
- API integration is stable and reliable
- User experience is intuitive and responsive
- Apps can be built and distributed for all target platforms