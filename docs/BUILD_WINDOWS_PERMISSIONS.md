# Windows Build Permissions Fix

## Issue: Symbolic Link Permission Error

**Error:**
```
ERROR: Cannot create symbolic link : Een van de vereiste bevoegdheden is niet aan de client toegekend.
```

This means Windows cannot create symbolic links because of missing permissions.

## Solutions

### Solution 1: Enable Developer Mode (Recommended)

1. **Open Windows Settings:**
   - Press `Win + I`
   - Go to **Privacy & Security** → **For developers**

2. **Enable Developer Mode:**
   - Turn on **Developer Mode**
   - This allows creating symbolic links without administrator privileges

3. **Restart your terminal/PowerShell**

4. **Try building again:**
   ```cmd
   scripts\build-desktop-simple.bat
   ```

### Solution 2: Run as Administrator

1. **Right-click PowerShell or Command Prompt**
2. **Choose "Run as Administrator"**
3. **Navigate to project and build:**
   ```cmd
   cd C:\Users\dries\OneDrive\Dokumente\GitHub\TimeTracker
   scripts\build-desktop-simple.bat
   ```

### Solution 3: Disable Code Signing (Already Applied)

The `desktop/package.json` has been updated to disable code signing for development builds:
```json
"win": {
  "sign": false,
  "signingHashAlgorithms": []
}
```

This prevents electron-builder from downloading and extracting the code signing tools that cause the symlink issue.

### Solution 4: Clear electron-builder Cache

If the cache is corrupted:

```powershell
Remove-Item -Path "$env:LOCALAPPDATA\electron-builder\Cache\winCodeSign" -Recurse -Force -ErrorAction SilentlyContinue
```

Then try building again.

## Quick Fix

**Enable Developer Mode (fastest):**
1. `Win + I` → Privacy & Security → For developers
2. Enable Developer Mode
3. Restart terminal
4. Build again

**Or run as Administrator:**
- Right-click PowerShell → Run as Administrator
- Run build script

## Why This Happens

- electron-builder downloads code signing tools
- These tools include macOS files that use symbolic links
- Windows requires special permissions to create symlinks
- Developer Mode or Administrator privileges are needed

## Prevention

The build configuration has been updated to:
- Disable code signing for development builds
- This avoids downloading the problematic tools
- Production builds can re-enable signing if needed

---

**Last Updated:** 2024
