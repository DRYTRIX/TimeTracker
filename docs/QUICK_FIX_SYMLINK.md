# Quick Fix for Symbolic Link Error

## The Problem

electron-builder is still downloading winCodeSign tools even with code signing disabled, causing symbolic link errors.

## ⚡ Quick Fix (3 Steps)

### Step 1: Clear Cache
```cmd
scripts\clear-all-electron-cache.bat
```

Or in Git Bash:
```bash
./scripts/clear-all-electron-cache.sh
```

### Step 2: Enable Developer Mode (One Time)
1. Press `Win + I`
2. Go to **Privacy & Security** → **For developers**
3. Turn on **Developer Mode**
4. **Restart your terminal**

### Step 3: Build Again
```cmd
scripts\build-desktop-simple.bat
```

## 🔧 Alternative: Use Environment Variable

Before building, set this environment variable:

**Command Prompt:**
```cmd
set CSC_IDENTITY_AUTO_DISCOVERY=false
scripts\build-desktop-simple.bat
```

**PowerShell:**
```powershell
$env:CSC_IDENTITY_AUTO_DISCOVERY="false"
.\scripts\build-desktop-windows.ps1
```

**Git Bash:**
```bash
export CSC_IDENTITY_AUTO_DISCOVERY=false
./scripts/build-desktop.sh
```

The build scripts now automatically set this variable, but if issues persist, set it manually.

## ✅ What's Already Fixed

- `desktop/package.json` has `sign: null` to disable code signing
- Build scripts now set `CSC_IDENTITY_AUTO_DISCOVERY=false` automatically
- Cache clearing scripts created
- All build scripts updated

## 📋 Why This Works

`CSC_IDENTITY_AUTO_DISCOVERY=false` tells electron-builder to completely skip code signing, preventing it from downloading winCodeSign tools that cause symlink issues.

---

**TL;DR:** Clear cache + Enable Developer Mode = Problem solved!
