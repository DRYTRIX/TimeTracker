# Fix OneDrive File Locking Issues

## ⚠️ Critical: OneDrive is Causing npm Install to Fail

Your error shows OneDrive is locking files in `node_modules`, preventing npm from working.

## ✅ Quick Fix (Most Important!)

**Exclude `node_modules` from OneDrive sync:**

1. Right-click `desktop\node_modules` folder
2. Choose **"Always keep on this device"**
3. Or exclude it from OneDrive sync entirely

This prevents **90% of Windows build issues!**

## 🔧 Automated Fix Scripts

### Option 1: PowerShell Script (Recommended)
```powershell
.\scripts\fix-onedrive-lock.ps1
```

This script:
- Handles locked files better than batch files
- Automatically retries removal
- Provides clear instructions

### Option 2: Batch Script
```cmd
scripts\fix-windows-build.bat
```

### Option 3: Manual Steps

1. **Close ALL programs**
   - VS Code
   - All terminals
   - File Explorer windows
   - Any other programs using the project

2. **Run PowerShell as Administrator**
   ```powershell
   cd desktop
   Remove-Item -Path node_modules -Recurse -Force
   Remove-Item -Path package-lock.json -Force
   npm install
   ```

## 📋 Step-by-Step Solution

### Step 1: Exclude from OneDrive (Do This First!)

**Method A: Right-click in File Explorer**
1. Open File Explorer
2. Navigate to `desktop\node_modules`
3. Right-click → **"Always keep on this device"**

**Method B: OneDrive Settings**
1. Right-click OneDrive icon in system tray
2. Settings → Sync and backup → Advanced settings
3. Exclude `desktop\node_modules` from sync

### Step 2: Fix Existing Issues

Run the PowerShell fix script:
```powershell
.\scripts\fix-onedrive-lock.ps1
```

Or manually:
```powershell
cd desktop
Remove-Item -Path node_modules -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path package-lock.json -Force -ErrorAction SilentlyContinue
npm cache clean --force
npm install
```

### Step 3: Build

```cmd
scripts\build-desktop-simple.bat
```

## 🚫 Prevent Future Issues

**Always exclude these from OneDrive sync:**
- `desktop\node_modules\` (most important!)
- `node_modules\` (if any in root)
- `.venv\` or `venv\` (Python virtual environments)
- `__pycache__\` directories

**Or move the entire project outside OneDrive:**
- Move to `C:\Projects\TimeTracker\`
- This prevents all OneDrive-related issues

## 🔍 Understanding the Error

The error `EPERM: operation not permitted, rmdir` means:
- OneDrive is synchronizing files in real-time
- npm tries to delete/rename files
- OneDrive locks them for sync
- npm can't complete the operation

**Solution:** Exclude `node_modules` from sync so OneDrive leaves it alone.

## ⚡ Emergency Fix

If you need to build **right now** and can't exclude from OneDrive:

1. **Pause OneDrive sync temporarily:**
   - Right-click OneDrive icon → Pause syncing → 2 hours

2. **Delete and reinstall:**
   ```cmd
   cd desktop
   rmdir /s /q node_modules
   del package-lock.json
   npm install
   ```

3. **Build:**
   ```cmd
   cd ..
   scripts\build-desktop-simple.bat
   ```

4. **Resume OneDrive** (but exclude node_modules first!)

## 📚 Long-Term Solution

**Best Practice:** Move project outside OneDrive
- Create `C:\Projects\` directory
- Move entire `TimeTracker` folder there
- Prevents all OneDrive-related npm issues
- Better performance too

---

**Remember:** Excluding `node_modules` from OneDrive sync is the #1 solution! 🎯
