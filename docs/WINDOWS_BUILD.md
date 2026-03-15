# Windows Build Guide

This guide helps you build the TimeTracker desktop application on Windows.

## Quick Start

### Option 1: Use Windows Native Scripts (Recommended)

**Command Prompt:**
```cmd
scripts\build-desktop-windows.bat
```

**PowerShell:**
```powershell
.\scripts\build-desktop-windows.ps1
```

### Option 2: Use Git Bash Script

```bash
./scripts/build-desktop.sh
```

Note: The bash script will detect Windows and suggest using native scripts.

## Prerequisites

1. **Node.js 18+** - [Download](https://nodejs.org/)
2. **Python 3** - For version syncing
3. **Git** - For cloning (if using Git Bash)

Verify installation:
```cmd
node --version
npm --version
python --version
```

## Common Issues and Solutions

### Issue: npm install fails with EPERM errors

**Symptoms:**
```
npm ERR! code EPERM
npm ERR! syscall rmdir
npm ERR! Error: EPERM: operation not permitted
```

**Solutions (in order of effectiveness):**

1. **Exclude node_modules from OneDrive Sync** (Most Important!)
   - Right-click `desktop\node_modules` folder
   - Choose "Always keep on this device"
   - Or exclude the entire `node_modules` folder from OneDrive sync
   - This is the #1 cause of Windows build issues

2. **Run Fix Script:**
   ```cmd
   scripts\fix-windows-build.bat
   ```

3. **Run as Administrator:**
   - Right-click Command Prompt or PowerShell
   - Choose "Run as Administrator"
   - Navigate to project and run build script

4. **Temporarily Disable Antivirus:**
   - Disable real-time scanning temporarily
   - Run npm install
   - Re-enable antivirus

5. **Move Project Outside OneDrive:**
   - Move entire project to `C:\Projects\TimeTracker` or similar
   - This prevents all OneDrive-related issues

6. **Use WSL (Windows Subsystem for Linux):**
   - Install WSL from Microsoft Store
   - Run build scripts from WSL terminal
   - WSL handles file permissions better

### Issue: electron-builder not found

**Symptoms:**
```
'electron-builder' is not recognized as an internal or external command
```

**Solution:**
```cmd
cd desktop
npm install
```

The Windows scripts use `npx electron-builder` which should work even if the binary isn't in PATH.

### Issue: Missing icon.ico

**Symptoms:**
```
Error: icon.ico not found
```

**Solution:**
```cmd
cd desktop
npm install sharp
cd ..
node scripts\generate-icons.js
```

Then convert the generated PNG to ICO using:
- Online: [CloudConvert](https://cloudconvert.com/png-ico)
- ImageMagick: `magick convert icon-256x256.png icon.ico`

### Issue: Build fails with permission errors

**Symptoms:**
```
Error: EACCES: permission denied
```

**Solutions:**
1. Run as Administrator
2. Check folder permissions
3. Exclude from antivirus scanning
4. Move project outside OneDrive

## Step-by-Step Build Process

### 1. Prepare Environment

```cmd
cd C:\Users\YourName\OneDrive\Dokumente\GitHub\TimeTracker
```

### 2. Fix OneDrive Issues (if applicable)

```cmd
scripts\fix-windows-build.bat
```

### 3. Generate Icons (if missing)

```cmd
npm install sharp
node scripts\generate-icons.js
```

### 4. Build Application

**Command Prompt:**
```cmd
scripts\build-desktop-windows.bat
```

**PowerShell:**
```powershell
.\scripts\build-desktop-windows.ps1
```

### 5. Find Output

The built installer will be in:
```
desktop\dist\TimeTracker-4.10.1-x64.exe
```

## Troubleshooting

### Verify Setup

Check if everything is configured correctly:
```cmd
cd desktop
node --version
npm --version
dir node_modules\electron-builder
```

### Clean Build

If build fails, try a clean build:
```cmd
cd desktop
rmdir /s /q node_modules
del package-lock.json
npm install
cd ..
scripts\build-desktop-windows.bat
```

### Check Logs

npm logs are in:
```
%APPDATA%\npm-cache\_logs\
```

### Common Error Messages

| Error | Solution |
|-------|----------|
| `EPERM: operation not permitted` | Exclude node_modules from OneDrive |
| `electron-builder not found` | Run `npm install` in desktop folder |
| `icon.ico not found` | Generate icons with `node scripts\generate-icons.js` |
| `Python not found` | Install Python 3 and add to PATH |
| `Node.js not found` | Install Node.js 18+ and add to PATH |

## Best Practices

1. **Always exclude node_modules from OneDrive sync**
   - This prevents 90% of Windows build issues

2. **Use native Windows scripts**
   - `build-desktop-windows.bat` or `.ps1` work better than bash scripts

3. **Run as Administrator if needed**
   - Some operations require elevated permissions

4. **Keep project outside OneDrive if possible**
   - Prevents file locking issues entirely

5. **Use WSL for complex builds**
   - WSL handles npm better than native Windows

## Scripts Reference

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `build-desktop-windows.bat` | Build desktop app (CMD) | Command Prompt |
| `build-desktop-windows.ps1` | Build desktop app (PowerShell) | PowerShell |
| `build-desktop.sh` | Build desktop app (Bash) | Git Bash/WSL |
| `fix-windows-build.bat` | Fix npm issues | When npm install fails |
| `verify-desktop-setup.sh` | Check setup | Before building |

## Getting Help

If issues persist:

1. Check this guide first
2. Run `scripts\fix-windows-build.bat`
3. Verify prerequisites are installed
4. Check npm logs in `%APPDATA%\npm-cache\_logs\`
5. Create an issue with:
   - Error messages
   - Windows version
   - Node.js version
   - Whether project is in OneDrive

---

**Last Updated:** 2024
