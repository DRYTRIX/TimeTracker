# Final Fix for Symbolic Link Error

## The Problem

electron-builder **keeps downloading winCodeSign** even when code signing is disabled, causing symbolic link permission errors.

## 🔧 Solution: Use the No-Sign Build Script

I've created a specialized build script that **aggressively prevents** code signing:

### Option 1: Use the No-Sign Script (RECOMMENDED)

**Git Bash:**
```bash
./scripts/build-desktop-no-sign.sh
```

**Command Prompt:**
```cmd
scripts\build-desktop-no-sign.bat
```

This script:
- ✅ Clears ALL electron-builder cache
- ✅ Sets multiple environment variables to disable signing
- ✅ Uses explicit `--config.win.sign=null` flag
- ✅ Prevents winCodeSign download

### Option 2: Enable Developer Mode (One-Time Fix)

**This is the PERMANENT solution:**

1. Press `Win + I` (Windows Settings)
2. Go to **Privacy & Security** → **For developers**
3. Turn on **Developer Mode**
4. **Restart your terminal**
5. Build normally:
   ```bash
   ./scripts/build-desktop.sh
   ```

Developer Mode allows Windows to create symbolic links without Administrator privileges, solving the issue permanently.

### Option 3: Manual Environment Variables

Before ANY build, set these:

**Command Prompt:**
```cmd
set CSC_IDENTITY_AUTO_DISCOVERY=false
set WIN_CSC_LINK=
set CSC_LINK=
scripts\build-desktop-simple.bat
```

**PowerShell:**
```powershell
$env:CSC_IDENTITY_AUTO_DISCOVERY="false"
$env:WIN_CSC_LINK=""
$env:CSC_LINK=""
.\scripts\build-desktop-windows.ps1
```

**Git Bash:**
```bash
export CSC_IDENTITY_AUTO_DISCOVERY=false
export WIN_CSC_LINK=""
export CSC_LINK=""
./scripts/build-desktop.sh
```

## Why This Happens

electron-builder checks for code signing **even when disabled** and downloads winCodeSign tools "just in case". The winCodeSign archive contains macOS files with symbolic links, which Windows cannot extract without special permissions.

## What We've Done

✅ Updated `desktop/package.json` with `sign: null`  
✅ Added environment variables to all build scripts  
✅ Created cache clearing scripts  
✅ Created specialized "no-sign" build scripts  
✅ Added explicit `--config.win.sign=null` flags  

## Quick Decision Tree

```
Still getting symlink error?
│
├─> Try: ./scripts/build-desktop-no-sign.sh
│   (Most aggressive prevention)
│
├─> Enable Developer Mode (one-time)
│   Win+I > Privacy & Security > For developers
│   (Permanent fix)
│
└─> Run as Administrator
    (Temporary workaround)
```

## Success Indicators

When it works, you should see:
- ✅ No "downloading winCodeSign" messages
- ✅ Build completes successfully
- ✅ Installer created in `desktop/dist/`

---

**TL;DR:** Use `./scripts/build-desktop-no-sign.sh` OR enable Developer Mode!
