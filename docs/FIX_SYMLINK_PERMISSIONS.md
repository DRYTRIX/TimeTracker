# Fix Symbolic Link Permission Error

## Problem

electron-builder is still downloading winCodeSign tools even with `forceCodeSigning: false`, causing symbolic link errors on Windows.

**Error:**
```
ERROR: Cannot create symbolic link : Een van de vereiste bevoegdheden is niet aan de client toegekend.
```

## Root Cause

Even though code signing is disabled, electron-builder may still attempt to download code signing tools. The winCodeSign archive contains macOS files that use symbolic links, which Windows cannot create without special permissions.

## Solutions

### Solution 1: Enable Developer Mode (Recommended - One Time)

1. **Press `Win + I`** to open Windows Settings
2. Go to **Privacy & Security** → **For developers**
3. Turn on **Developer Mode**
4. **Restart your terminal/PowerShell**
5. Try building again

This is a one-time setting that allows creating symbolic links without administrator privileges.

### Solution 2: Clear Cache Before Building

Run this script to clear all electron-builder cache:

```bash
./scripts/clear-all-electron-cache.sh
```

Or manually:
```bash
# In Git Bash or WSL
rm -rf "$LOCALAPPDATA/electron-builder/Cache/winCodeSign"
# Or
rm -rf "$HOME/AppData/Local/electron-builder/Cache/winCodeSign"
```

Then build again.

### Solution 3: Run as Administrator

1. Right-click PowerShell or Command Prompt
2. Choose **"Run as Administrator"**
3. Navigate to project and build:
   ```cmd
   cd C:\Users\dries\OneDrive\Dokumente\GitHub\TimeTracker
   scripts\build-desktop-simple.bat
   ```

### Solution 4: Use Environment Variable

Set an environment variable to skip code signing completely:

**Before building, run:**
```cmd
set CSC_IDENTITY_AUTO_DISCOVERY=false
scripts\build-desktop-simple.bat
```

**Or in PowerShell:**
```powershell
$env:CSC_IDENTITY_AUTO_DISCOVERY="false"
.\scripts\build-desktop-windows.ps1
```

**Or in Git Bash:**
```bash
export CSC_IDENTITY_AUTO_DISCOVERY=false
./scripts/build-desktop.sh
```

### Solution 5: Configure electron-builder to Skip Code Signing

The configuration in `desktop/package.json` has been updated to:
```json
"win": {
  "sign": null,
  "signingHashAlgorithms": null,
  "signDlls": false
}
```

But electron-builder may still download tools. Use Solution 4 (environment variable) to ensure it's completely disabled.

## Quick Fix

**Best approach (combine multiple solutions):**

1. **Enable Developer Mode** (one-time setup)
2. **Clear cache:**
   ```bash
   ./scripts/clear-all-electron-cache.sh
   ```
3. **Set environment variable:**
   ```bash
   export CSC_IDENTITY_AUTO_DISCOVERY=false
   ```
4. **Build:**
   ```bash
   ./scripts/build-desktop.sh
   ```

## Why This Happens

- electron-builder downloads winCodeSign tools even when code signing is disabled
- These tools contain macOS files (darwin/) with symbolic links
- Windows needs special permissions (Developer Mode or Administrator) to create symlinks
- Even if code signing is disabled, the download still happens

## Permanent Fix

1. **Enable Developer Mode** in Windows (recommended - one-time)
2. **Set environment variable** in your shell profile:
   ```bash
   # Add to ~/.bashrc or ~/.zshrc
   export CSC_IDENTITY_AUTO_DISCOVERY=false
   ```

Or for PowerShell:
```powershell
# Add to $PROFILE
$env:CSC_IDENTITY_AUTO_DISCOVERY="false"
```

---

**Remember:** The easiest fix is to enable Developer Mode in Windows Settings!
