# Desktop Build Windows Troubleshooting

## Problem: npm Permission Errors (EPERM)

You're getting errors like:
```
npm ERR! code EPERM
npm ERR! syscall rmdir
npm ERR! path C:\Users\...\node_modules\...
npm ERR! Error: EPERM: operation not permitted, rmdir
```

## Root Causes

This is common on Windows, especially when:

1. **OneDrive File Locking** (Most Common)
   - Project is in OneDrive folder
   - OneDrive constantly syncs files and can lock them
   - npm can't remove/modify directories during sync

2. **Antivirus Software**
   - Real-time scanning locks files during npm operations
   - Windows Defender or third-party antivirus scanning node_modules

3. **File System Permissions**
   - Insufficient permissions to modify files
   - Files locked by another process (IDE, file explorer, etc.)

4. **Long Path Names**
   - Windows has a 260-character path limit
   - Deep node_modules structures can exceed this

## Solutions (Try in Order)

### Solution 1: Quick Fix Script (Recommended)

Run the fix script:
```batch
scripts\fix-desktop-build.bat
```

This will:
- Clean npm cache
- Remove problematic temp directories
- Optionally remove and reinstall node_modules

### Solution 2: Exclude node_modules from OneDrive (Recommended for OneDrive Users)

**If your project is in OneDrive:**

1. **Exclude from Sync (Best Solution)**
   - Right-click `desktop\node_modules` folder
   - Select "Free up space" or "Always keep on this device"
   - Or: OneDrive Settings → Sync → Advanced → Files On-Demand
   - This prevents OneDrive from syncing/locking node_modules

2. **Move Project Outside OneDrive (Best Long-term Solution)**
   ```batch
   # Move to a non-OneDrive location
   C:\dev\TimeTracker  # or C:\projects\TimeTracker
   ```
   - Prevents all OneDrive-related issues
   - Faster build times (no sync overhead)
   - Better performance

### Solution 3: Run as Administrator

Sometimes Windows permissions require admin access:

```batch
# Right-click Command Prompt or PowerShell
# Select "Run as administrator"
# Then run your build script
scripts\build-desktop.bat
```

### Solution 4: Clean and Reinstall

Manually clean and reinstall:

```batch
cd desktop

# Clean npm cache
npm cache clean --force

# Remove node_modules
rd /s /q node_modules

# Remove package-lock.json (optional, for fresh install)
del package-lock.json

# Reinstall
npm install
```

### Solution 5: Exclude from Antivirus

Add exclusions to Windows Defender or your antivirus:

**Windows Defender:**
1. Windows Security → Virus & threat protection
2. Manage settings → Exclusions
3. Add folder: `C:\Users\...\TimeTracker\desktop\node_modules`

### Solution 6: Close Locking Processes

Before building, close:
- File Explorer windows showing the project
- IDE/editors with the project open
- Any terminal windows in the project directory
- Other npm/node processes

### Solution 7: Enable Long Path Support (Windows 10+)

If you're hitting path length limits:

1. Open PowerShell as Administrator
2. Run:
   ```powershell
   New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
   ```
3. Restart your computer

## Prevention

### Best Practices

1. **Move Project Outside OneDrive**
   - Use: `C:\dev\`, `C:\projects\`, or `C:\code\`
   - Prevents all OneDrive-related issues

2. **Use a Project Directory Outside User Folder**
   - Avoid: `C:\Users\...\OneDrive\...`
   - Prefer: `C:\dev\TimeTracker`

3. **Add node_modules to .gitignore** (Already done)
   - Prevents git from tracking node_modules
   - Reduces sync conflicts

4. **Use npm ci for CI/CD**
   - Cleaner, more reliable than npm install
   - Build script already uses this

## Additional Resources

- [npm Troubleshooting Guide](https://docs.npmjs.com/common-errors)
- [Windows Long Path Support](https://docs.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation)
- [OneDrive Files On-Demand](https://support.microsoft.com/en-us/office/save-disk-space-with-onedrive-files-on-demand-for-windows-10-0e6860d3-d9f3-4971-b321-7092438fb38e)

## Still Having Issues?

If none of these solutions work:

1. Check npm logs: `%LOCALAPPDATA%\npm-cache\_logs\`
2. Try with a different Node.js version
3. Check Windows Event Viewer for system errors
4. Consider using WSL2 (Windows Subsystem for Linux) for building
