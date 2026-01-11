# Build Configuration Guide

This document explains how version syncing and build configuration works across all TimeTracker applications.

## Version Management

All applications now sync their version from `setup.py`, which is the single source of truth for version information.

### Desktop App (Electron)

**Version Sync:**
- Automatically syncs from `setup.py` to `desktop/package.json` before building
- Script: `scripts/sync-desktop-version.py`
- Run manually: `python scripts/sync-desktop-version.py`

**Build Scripts:**
- `scripts/build-desktop.bat` (Windows)
- `scripts/build-desktop.sh` (Linux/macOS)
- `scripts/build-all.bat` / `scripts/build-all.sh`

All build scripts automatically sync the version before building.

### Mobile App (Flutter)

**Version Sync:**
- Automatically syncs from `setup.py` to:
  - `mobile/pubspec.yaml` (Flutter version)
  - `mobile/android/local.properties` (Android version code and name)
- Script: `scripts/sync-mobile-version.py`
- Run manually: `python scripts/sync-mobile-version.py`

**Version Code Calculation:**
- Android version code is calculated as: `major * 10000 + minor * 100 + patch`
- Example: Version `4.10.1` → version code `41001`

**Build Scripts:**
- `scripts/build-mobile.bat` (Windows)
- `scripts/build-mobile.sh` (Linux/macOS)
- `scripts/build-all.bat` / `scripts/build-all.sh`

All build scripts automatically sync the version before building.

## Server URL Configuration

### Desktop App

The desktop app can receive the server URL in multiple ways:

1. **Command Line Argument:**
   ```bash
   TimeTracker.exe --server-url https://your-server.com
   # or
   TimeTracker.exe --server https://your-server.com
   ```

2. **Environment Variable:**
   ```bash
   set TIMETRACKER_SERVER_URL=https://your-server.com
   TimeTracker.exe
   ```

3. **In-App Configuration:**
   - Users can configure the server URL in the app's settings screen
   - Stored in Electron's secure storage

### Mobile App

The mobile app supports server URL configuration through:

1. **Environment Variable (Build Time):**
   ```bash
   flutter build apk --dart-define=TIMETRACKER_SERVER_URL=https://your-server.com
   ```

2. **Default Server URL (Build Time):**
   ```bash
   flutter build apk --dart-define=DEFAULT_SERVER_URL=https://your-server.com
   ```

3. **Runtime Configuration:**
   - Users can configure the server URL in the app settings
   - Stored in SharedPreferences
   - Configuration class: `mobile/lib/core/config.dart`

## Icon and Favicon Configuration

### Desktop App Icons

**Required Files:**
- `desktop/assets/icon.ico` - Windows icon
- `desktop/assets/icon.icns` - macOS icon  
- `desktop/assets/icon.png` - Linux icon

**Generation:**
See `desktop/assets/README.md` for detailed instructions on generating icons from the SVG logo.

**Favicon:**
- Configured in `desktop/src/renderer/index.html`
- Uses `desktop/assets/icon.png` and `icon.ico`
- Falls back gracefully if files don't exist

### Web App Favicon

The web application uses the logo as favicon:
- Location: `app/static/images/timetracker-logo.svg`
- Configured in: `app/templates/base.html`
- Also used in PWA manifest: `app/static/manifest.webmanifest`

## Build Optimization

### Desktop App

The Electron build is optimized for smaller executables:

- **ASAR Packaging:** Enabled (`"asar": true`)
- **Compression:** Maximum (`"compression": "maximum"`)
- **Architecture:** Only x64 (removed ia32 for smaller size)
- **NSIS Compressor:** zlib for better compression

### Output File Naming

Executables are named with version information:
- Windows: `TimeTracker-4.10.1-x64.exe`
- macOS: `TimeTracker-4.10.1-x64.dmg` or `TimeTracker-4.10.1-arm64.dmg`
- Linux: `TimeTracker-4.10.1-x64.AppImage` or `TimeTracker-4.10.1-x64.deb`

## Usage Examples

### Building Desktop App

```bash
# Windows
scripts\build-desktop.bat

# Linux/macOS
./scripts/build-desktop.sh

# All platforms (on macOS)
./scripts/build-desktop.sh all
```

### Building Mobile App

```bash
# Windows
scripts\build-mobile.bat

# Linux/macOS
./scripts/build-mobile.sh

# With custom server URL
flutter build apk --dart-define=TIMETRACKER_SERVER_URL=https://your-server.com
```

### Building Everything

```bash
# Windows
scripts\build-all.bat

# Linux/macOS
./scripts/build-all.sh
```

### Running Desktop App with Server URL

```bash
# Windows
TimeTracker.exe --server-url https://your-server.com

# Linux/macOS
./TimeTracker --server-url https://your-server.com

# Or with environment variable
export TIMETRACKER_SERVER_URL=https://your-server.com
./TimeTracker
```

## Version Update Process

To update the version for all applications:

1. **Update `setup.py`:**
   ```python
   setup(
       name='timetracker',
       version='4.11.0',  # Update here
       ...
   )
   ```

2. **Run version sync scripts:**
   ```bash
   python scripts/sync-desktop-version.py
   python scripts/sync-mobile-version.py
   ```

3. **Or just build** - the build scripts will automatically sync versions

## Troubleshooting

### Version Not Syncing

- Ensure Python 3 is installed and in PATH
- Check that `setup.py` exists in the project root
- Verify the version format in `setup.py` matches semantic versioning (X.Y.Z)

### Icons Not Showing

- Ensure icon files exist in `desktop/assets/`
- Check file permissions
- Verify icon file formats are correct (.ico for Windows, .icns for macOS, .png for Linux)

### Server URL Not Working

- Verify the URL format (must start with http:// or https://)
- Check command line argument syntax
- Ensure environment variables are set correctly
- For mobile app, verify the configuration class is imported correctly
