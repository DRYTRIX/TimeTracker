# Quick Fix for Windows Build Issues

## Try the Simplified Build Script

If `build-desktop.bat` stops working, use the simplified version:

```cmd
scripts\build-desktop-simple.bat
```

This version:
- Uses simpler logic (no delayed expansion issues)
- Has better debug output
- More reliable on Windows

## If That Doesn't Work

### Step 1: Manual Build

```cmd
cd desktop
npm install
npx electron-builder --win
```

### Step 2: Check What's Missing

Run the test script:
```cmd
scripts\test-build-desktop.bat
```

This will show exactly what's wrong.

### Step 3: Common Fixes

1. **Exclude node_modules from OneDrive**
   - Right-click `desktop\node_modules`
   - Choose "Always keep on this device"

2. **Reinstall Dependencies**
   ```cmd
   cd desktop
   rmdir /s /q node_modules
   del package-lock.json
   npm install
   ```

3. **Fix Script Issues**
   ```cmd
   scripts\fix-windows-build.bat
   ```

## Debugging

If the script stops after "npm version", check:
- Is node_modules missing or corrupted?
- Are there OneDrive file locks?
- Does `npx` work? Try: `npx --version`

---

**Last Resort:** Use the PowerShell script:
```powershell
.\scripts\build-desktop-windows.ps1
```
