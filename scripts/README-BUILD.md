# Build Scripts for TimeTracker Mobile and Desktop Apps

This directory contains build scripts for building the TimeTracker mobile (Flutter) and desktop (Electron) applications locally.

## Quick Start

### All Platforms (Linux/macOS)
```bash
# Make scripts executable (first time only)
chmod +x scripts/*.sh

# Build everything
./scripts/build-all.sh

# Build mobile only
./scripts/build-all.sh --mobile-only

# Build desktop only
./scripts/build-all.sh --desktop-only

# Build specific platform
./scripts/build-all.sh android    # Mobile Android
./scripts/build-all.sh ios        # Mobile iOS (macOS only)
./scripts/build-all.sh linux      # Desktop Linux
./scripts/build-all.sh macos      # Desktop macOS
```

### Windows
```batch
REM Build everything
scripts\build-all.bat

REM Build mobile only
scripts\build-all.bat --mobile-only

REM Build desktop only
scripts\build-all.bat --desktop-only

REM Build Android only
scripts\build-all.bat --android-only

REM Build Windows only
scripts\build-all.bat --windows-only
```

## Individual Build Scripts

### Mobile App (Flutter)

**Linux/macOS:**
```bash
# Build Android
./scripts/build-mobile.sh android

# Build iOS (macOS only)
./scripts/build-mobile.sh ios

# Build all
./scripts/build-mobile.sh all
```

**Windows:**
```batch
REM Build Android
scripts\build-mobile.bat android

REM Build all
scripts\build-mobile.bat all
```

### Desktop App (Electron)

**Linux/macOS:**
```bash
# Build for current platform
./scripts/build-desktop.sh current

# Build Windows (cross-platform, requires Wine on Linux)
./scripts/build-desktop.sh win

# Build macOS (macOS only)
./scripts/build-desktop.sh mac

# Build Linux (Linux only)
./scripts/build-desktop.sh linux

# Build all platforms
./scripts/build-desktop.sh all
```

**Windows:**
```batch
REM Build Windows installer
scripts\build-desktop.bat win

REM Build all platforms
scripts\build-desktop.bat all
```

## Prerequisites

### Mobile App (Flutter)
- Flutter SDK 3.0.0 or higher
- Android SDK (for Android builds)
- Xcode (for iOS builds, macOS only)
- Command line tools: `flutter`, `dart`

### Desktop App (Electron)
- Node.js 18+ and npm
- Platform-specific build tools:
  - Windows: Visual Studio Build Tools or Visual Studio
  - macOS: Xcode Command Line Tools
  - Linux: Standard build tools (make, gcc, etc.)

## Build Outputs

### Mobile App
- **Android APK**: `mobile/build/app/outputs/flutter-apk/app-release.apk`
- **Android AAB**: `mobile/build/app/outputs/bundle/release/app-release.aab`
- **iOS**: `mobile/build/ios/iphoneos/Runner.app` (requires Xcode for distribution)

### Desktop App
- **Windows**: `desktop/dist/*.exe` (NSIS installer)
- **macOS**: `desktop/dist/*.dmg`
- **Linux**: `desktop/dist/*.AppImage` and `desktop/dist/*.deb`

## Troubleshooting

### Flutter Issues
- **"Flutter not found"**: Add Flutter to your PATH or install Flutter SDK
- **"Android SDK not found"**: Install Android Studio and configure Android SDK
- **Build fails**: Run `flutter doctor` to check configuration

### Electron Issues
- **"Node.js not found"**: Install Node.js 18+ from nodejs.org
- **Build fails on Windows**: Install Visual Studio Build Tools
- **Icons missing**: Create placeholder icons in `desktop/assets/` or update build config

### Platform-Specific Issues

**Linux:**
- May need to install: `libnss3-dev`, `libgconf-2-4`, `libxss1`

**macOS:**
- iOS builds require Xcode and signing certificates
- May need to accept Xcode license: `sudo xcodebuild -license accept`

**Windows:**
- May need Visual Studio Build Tools for native modules
- Some builds may require administrator privileges

## Advanced Options

### Build Flags

The main build script supports various flags:

**Linux/macOS:**
```bash
# Build only mobile
./scripts/build-all.sh --mobile-only

# Build only desktop
./scripts/build-all.sh --desktop-only

# Build only Android
./scripts/build-all.sh --android-only

# Build only iOS (macOS)
./scripts/build-all.sh --ios-only

# Build only Linux desktop
./scripts/build-all.sh --linux-only

# Build only macOS desktop
./scripts/build-all.sh --macos-only
```

**Windows:**
```batch
REM Similar flags available
scripts\build-all.bat --mobile-only
scripts\build-all.bat --desktop-only
scripts\build-all.bat --android-only
scripts\build-all.bat --windows-only
```

### CI/CD Integration

These scripts are designed to work in CI/CD environments:

```yaml
# Example GitHub Actions
- name: Build Mobile
  run: ./scripts/build-mobile.sh android

- name: Build Desktop
  run: ./scripts/build-desktop.sh current
```

## Notes

- Build scripts will create necessary directories automatically
- First build may take longer due to dependency downloads
- Release builds require code signing for distribution (not handled by scripts)
- Some builds may require manual configuration (e.g., iOS code signing)
