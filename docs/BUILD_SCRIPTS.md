# Build Scripts Documentation

This document describes the build scripts for TimeTracker and recent improvements.

## Desktop Build Scripts

### `scripts/build-desktop.sh`

Main script for building the desktop Electron application.

**Usage:**
```bash
./scripts/build-desktop.sh [platform]
```

**Platforms:**
- `win` or `windows` - Build Windows installer
- `mac` or `macos` - Build macOS DMG (macOS only)
- `linux` - Build Linux packages (Linux only)
- `all` or `all-platforms` - Build for all supported platforms
- `current` (default) - Build for current platform

**Features:**
- Automatically syncs version from `setup.py` to `package.json`
- Checks for required assets (logo, icons)
- Prepares assets automatically if missing
- Handles missing icon files gracefully with warnings
- Provides helpful error messages

**Example:**
```bash
# Build for current platform
./scripts/build-desktop.sh

# Build for Windows
./scripts/build-desktop.sh win

# Build for all platforms
./scripts/build-desktop.sh all
```

### `scripts/prepare-desktop-assets.sh`

Prepares desktop assets before building:
- Copies logo from main app to desktop/assets
- Checks for icon files
- Attempts to generate icons if possible
- Provides helpful warnings and instructions

**Usage:**
```bash
./scripts/prepare-desktop-assets.sh
```

### `scripts/check-desktop-assets.sh`

Quick check script to verify all required assets are present.

**Usage:**
```bash
./scripts/check-desktop-assets.sh
```

**Output:**
- Lists all assets and their status
- Exits with error code if critical assets are missing
- Provides instructions to fix missing assets

## All Platforms Build Script

### `scripts/build-all.sh`

Builds both mobile and desktop applications.

**Usage:**
```bash
./scripts/build-all.sh [options] [platform]
```

**Options:**
- `--mobile-only` - Build only mobile app
- `--desktop-only` - Build only desktop app
- `--android-only` - Build only Android
- `--ios-only` - Build only iOS (macOS only)
- `--linux-only` - Build only Linux desktop
- `--macos-only` - Build only macOS desktop

**Platforms:**
- `android` - Android APK and App Bundle
- `ios` - iOS app (macOS only)
- `linux` - Linux desktop packages
- `macos` - macOS DMG
- `all` - All platforms
- `all-platforms` - All desktop platforms
- `all-desktop` - All desktop platforms

**Example:**
```bash
# Build everything
./scripts/build-all.sh

# Build only desktop for current platform
./scripts/build-all.sh --desktop-only

# Build Android and Linux
./scripts/build-all.sh android linux
```

## Mobile Build Script

### `scripts/build-mobile.sh`

Builds the Flutter mobile application.

**Usage:**
```bash
./scripts/build-mobile.sh [platform]
```

**Platforms:**
- `android` - Android APK and App Bundle
- `ios` - iOS app (macOS only)
- `all` (default) - All platforms

## Recent Improvements

### Asset Management

1. **Automatic Logo Copying**
   - Build scripts now automatically copy the logo from `app/static/images/timetracker-logo.svg` to `desktop/assets/logo.svg` if missing

2. **Icon File Checking**
   - Scripts check for required icon files before building
   - Provide clear warnings if icons are missing
   - Don't fail the build, but warn about potential issues

3. **Graceful Degradation**
   - Splash screen only loads if `splash.html` exists
   - Missing icons don't prevent builds (but platform-specific builds may fail)
   - Helpful error messages guide users to fix issues

### Error Handling

- Better error messages with solutions
- Graceful handling of missing files
- Platform detection and validation
- Clear instructions for fixing issues

### Asset Preparation

The `prepare-desktop-assets.sh` script:
- Ensures logo is available
- Checks for all icon files
- Attempts to generate icons if `generate-icons.js` is available
- Provides clear instructions for manual icon generation

## Troubleshooting

### Missing Icons

If you see warnings about missing icons:

1. **Generate icons:**
   ```bash
   npm install sharp  # If not installed
   node scripts/generate-icons.js
   ```

2. **Convert to platform formats:**
   - Windows: Convert PNG to ICO using online tools or ImageMagick
   - macOS: Convert PNG to ICNS using `iconutil` or online tools
   - Linux: PNG is already generated

3. **Manual creation:**
   - See `desktop/assets/README.md` for detailed instructions
   - Use online converters like CloudConvert or iConvert Icons

### Build Failures

**Permission Errors:**
- On Linux/Mac: Check file permissions
- On WSL with OneDrive: Exclude `node_modules` from sync
- Try: `sudo npm install` (if permission issue)

**Missing Dependencies:**
- Ensure Node.js 18+ is installed
- Run `npm install` in `desktop/` directory
- Check `package.json` for required packages

**Platform-Specific Issues:**
- Windows builds require Windows or WSL
- macOS builds require macOS
- Linux builds require Linux

## File Structure

```
scripts/
├── build-desktop.sh          # Desktop build script
├── build-all.sh              # All platforms build script
├── build-mobile.sh           # Mobile build script
├── prepare-desktop-assets.sh # Asset preparation
├── check-desktop-assets.sh   # Asset verification
└── generate-icons.js         # Icon generation

desktop/
├── assets/
│   ├── logo.svg             # Desktop app logo (required)
│   ├── icon.png             # Linux icon (required)
│   ├── icon.ico             # Windows icon (required for Windows)
│   └── icon.icns            # macOS icon (required for macOS)
└── package.json             # Electron app configuration
```

## Best Practices

1. **Before Building:**
   - Run `scripts/check-desktop-assets.sh` to verify assets
   - Ensure version is synced (handled automatically)
   - Check platform requirements

2. **During Development:**
   - Use `npm run dev` in `desktop/` for development
   - Test splash screen and branding elements
   - Verify logo displays correctly

3. **For Releases:**
   - Generate all icon formats
   - Test builds on target platforms
   - Verify installer branding
   - Check splash screen functionality

---

**Last Updated:** 2024
**Maintainer:** Development Team
