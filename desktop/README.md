# TimeTracker Desktop App

Electron desktop application for Windows, Linux, and macOS that integrates with the TimeTracker REST API.

## Features

- ⏱️ **Time Tracking** - Start, stop, and manage timers
- 📊 **Projects & Tasks** - View and select projects and tasks
- 📝 **Time Entries** - View and manage time entries
- 🔄 **Offline Support** - Work offline with automatic sync
- 🔐 **Secure Authentication** - Token-based authentication
- 🖥️ **System Tray** - Minimize to tray, quick timer controls
- ⌨️ **Keyboard Shortcuts** - Global shortcuts for quick access

## Setup

### Prerequisites

- Node.js 18+ and npm
- Electron development tools

### Installation

1. Install dependencies:
```bash
npm install
```

2. Run in development mode:
```bash
npm run dev
```

3. Run in production mode:
```bash
npm start
```

## Building

### Quick Start

For the simplest cross-platform build experience:

**From the desktop directory:**
```bash
npm run build:all
```

**From the project root:**
- Linux/macOS: `./scripts/build-desktop.sh all-platforms`
- Windows: `scripts\build-desktop.bat all`

### Platform-Specific Builds

### Windows

```bash
npm run build:win
```

Creates NSIS installer in `dist/` directory.

### macOS

```bash
npm run build:mac
```

Creates DMG installer in `dist/` directory.

### Linux

```bash
npm run build:linux
```

Creates AppImage and .deb packages in `dist/` directory.

### All Platforms (Cross-Platform Build)

Build for all supported platforms with a single command (automatically detects your OS):

```bash
npm run build:all
```

**Platform Support:**
- **Windows**: Builds Windows only by default (Linux builds require administrator privileges for symlinks)
- **macOS**: Can build Windows, macOS, and Linux packages (all platforms!)
- **Linux**: Can build Windows and Linux packages

The command automatically detects your OS and only builds for platforms that can be built on your system. You won't see errors about unsupported platforms - they'll simply be skipped.

**Building Linux on Windows (requires admin privileges):**
```bash
# Run as administrator or set environment variable
$env:BUILD_LINUX_ON_WINDOWS="true"; npm run build:all

# Or build both platforms explicitly
npm run build:win+linux
```

**Troubleshooting Windows Builds:**

If you encounter permission errors (symlink issues):
1. **Clear electron-builder cache:**
   ```bash
   npm run clean:cache
   ```
   Or manually (Windows):
   ```powershell
   rmdir /s /q "$env:LOCALAPPDATA\electron-builder\Cache"
   ```
2. **Run as Administrator** - Right-click terminal → "Run as Administrator"
3. **Disable OneDrive sync** for the `desktop` folder (OneDrive can cause file lock issues)
4. **Build Windows only:** `npm run build:win` (no symlinks needed)

**Force build all (will fail on unsupported platforms):**
```bash
npm run build:all-force
```

You can also use the build scripts from the project root:

**Linux/macOS:**
```bash
./scripts/build-desktop.sh all-platforms
# or from project root:
./scripts/build-all.sh --desktop-only all-platforms
```

**Windows:**
```batch
scripts\build-desktop.bat all
REM or from project root:
scripts\build-all.bat --desktop-only
```

### Current Platform Only

```bash
npm run build
```

This builds only for your current platform.

## Configuration

1. Launch the app
2. Enter your TimeTracker server URL (e.g., `https://your-server.com`)
3. Enter your API token (obtained from Admin > API Tokens in the web app)
4. Start tracking time!

## Architecture

- **Main Process** (`src/main/`) - Window management, system tray, IPC
- **Renderer Process** (`src/renderer/`) - UI and frontend logic
- **Shared** (`src/shared/`) - Shared code between processes

## API Integration

The app integrates with the TimeTracker REST API (`/api/v1/`):

- Timer endpoints: `/api/v1/timer/start`, `/api/v1/timer/stop`, `/api/v1/timer/status`
- Time entries: `/api/v1/time-entries`
- Projects: `/api/v1/projects`
- Tasks: `/api/v1/tasks`

See the main project's API documentation for details.

## Distribution

Built installers can be found in the `dist/` directory after running build commands.

For code signing and notarization (required for macOS distribution), configure certificates in `package.json` build section.
