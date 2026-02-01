# Building TimeTracker Mobile and Desktop Apps

## Quick Start

### Build Everything (All Platforms)

**Linux/macOS:**
```bash
chmod +x scripts/build-all.sh
./scripts/build-all.sh
```

**Windows:**
```batch
scripts\build-all.bat
```

## Available Build Scripts

### Main Build Scripts

1. **build-all.sh / build-all.bat** - Build both mobile and desktop apps
   - Automatically detects platform
   - Supports flags: `--mobile-only`, `--desktop-only`, `--android-only`, `--ios-only`, `--windows-only`, `--linux-only`, `--macos-only`

2. **build-mobile.sh / build-mobile.bat** - Build mobile app only
   - Supports: `android`, `ios`, `all`

3. **build-desktop.sh / build-desktop.bat** - Build desktop app only
   - Supports: `win`, `mac`, `linux`, `all`, `current`

## Usage Examples

### Build Everything
```bash
# Linux/macOS
./scripts/build-all.sh

# Windows
scripts\build-all.bat
```

### Build Mobile Only
```bash
# Linux/macOS
./scripts/build-all.sh --mobile-only
# Or
./scripts/build-mobile.sh android

# Windows
scripts\build-all.bat --mobile-only
# Or
scripts\build-mobile.bat android
```

### Build Desktop Only
```bash
# Linux/macOS
./scripts/build-all.sh --desktop-only
# Or
./scripts/build-desktop.sh current

# Windows
scripts\build-all.bat --desktop-only
# Or
scripts\build-desktop.bat win
```

### Build Specific Platform
```bash
# Android only
./scripts/build-all.sh --android-only

# iOS only (macOS)
./scripts/build-all.sh --ios-only

# Windows desktop only
scripts\build-all.bat --windows-only

# Linux desktop only
./scripts/build-all.sh --linux-only
```

## Prerequisites

### Mobile App
- Flutter SDK 3.0+
- Android SDK (for Android)
- Xcode (for iOS, macOS only)
- **App icon:** Launcher icons are generated at the start of each mobile build from `mobile/assets/icon/app_icon.png`. That PNG can be exported once from `app/static/images/timetracker-logo-icon.svg` (1024×1024), or created by running `scripts/generate-mobile-icon.bat` / `scripts/generate-mobile-icon.sh` (requires ImageMagick, Inkscape, or Python with Pillow).

### Desktop App
- Node.js 18+
- npm
- Platform build tools

## Build Outputs

### Mobile App
- **Android APK**: `mobile/build/app/outputs/flutter-apk/app-release.apk`
- **Android AAB**: `mobile/build/app/outputs/bundle/release/app-release.aab`
- **iOS**: `mobile/build/ios/iphoneos/Runner.app`

### Desktop App
- **Windows**: `desktop/dist/*.exe`
- **macOS**: `desktop/dist/*.dmg`
- **Linux**: `desktop/dist/*.AppImage` and `desktop/dist/*.deb`

## Troubleshooting

- **Mobile launcher icon shows Android default:** Run icon generation and do a full clean build: from `mobile/` run `flutter clean`, `flutter pub get`, `dart run flutter_launcher_icons`, then build again. The build scripts run icon generation automatically; if you built without them, run the above once.
- **Icon should match the web app:** Export `app/static/images/timetracker-logo-icon.svg` to 1024×1024 PNG at `mobile/assets/icon/app_icon.png` (see `mobile/assets/icon/README.md`), then run `dart run flutter_launcher_icons` and rebuild.

See `scripts/README-BUILD.md` for detailed troubleshooting guide.

## CI/CD

These scripts are designed to work in CI/CD environments (GitHub Actions workflows are also available in `.github/workflows/`).
