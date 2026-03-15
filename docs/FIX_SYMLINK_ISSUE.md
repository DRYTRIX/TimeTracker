# Fix Symbolic Link Permission Error

## Quick Fix

The error is caused by Windows not having permission to create symbolic links.

### Option 1: Enable Developer Mode (Recommended - One Time)

1. Press `Win + I` to open Settings
2. Go to **Privacy & Security** → **For developers**
3. Turn on **Developer Mode**
4. Restart your terminal/PowerShell
5. Try building again

This is a one-time setting and allows creating symlinks without administrator privileges.

### Option 2: Run as Administrator

1. Right-click PowerShell or Command Prompt
2. Choose **"Run as Administrator"**
3. Navigate to project and build:
   ```cmd
   cd C:\Users\dries\OneDrive\Dokumente\GitHub\TimeTracker
   scripts\build-desktop-simple.bat
   ```

### Option 3: Clear Cache and Rebuild

The build configuration has been updated to disable code signing (which avoids the symlink issue):

1. **Clear electron-builder cache:**
   ```cmd
   scripts\clear-electron-builder-cache.bat
   ```

2. **Build again:**
   ```cmd
   scripts\build-desktop-simple.bat
   ```

## What Was Fixed

- Removed deprecated `compressor` option from NSIS config
- Disabled code signing (`forceCodeSigning: false`) to avoid symlink issues
- Build script now clears winCodeSign cache before building
- Added helper script to clear cache manually

## Why This Happens

electron-builder downloads code signing tools (winCodeSign) which contain macOS files using symbolic links. Windows needs special permissions to create symlinks.

## Solution Applied

The `desktop/package.json` now has:
```json
"win": {
  "forceCodeSigning": false
}
```

This prevents electron-builder from downloading the code signing tools that cause symlink issues.

---

**Best Solution:** Enable Developer Mode (one-time setup) + the build config is already fixed!
