# Building on Windows - Quick Guide

## 🚀 Quick Start

**Use the Windows-native build script:**

```cmd
scripts\build-desktop-windows.bat
```

Or in PowerShell:
```powershell
.\scripts\build-desktop-windows.ps1
```

## ⚠️ Important: OneDrive Issues

If your project is in OneDrive, you **MUST** exclude `node_modules` from sync:

1. Right-click `desktop\node_modules` folder
2. Choose **"Always keep on this device"**
3. Or exclude it from OneDrive sync entirely

This prevents 90% of Windows build issues!

## 🔧 If Build Fails

### Step 1: Fix npm Issues
```cmd
scripts\fix-windows-build.bat
```

### Step 2: Generate Icons (if missing)
```cmd
cd desktop
npm install sharp
cd ..
node scripts\generate-icons.js
```

### Step 3: Build Again
```cmd
scripts\build-desktop-windows.bat
```

## 📋 Full Documentation

See [README_WINDOWS_BUILD.md](README_WINDOWS_BUILD.md) for complete troubleshooting guide.

---

**TL;DR:** Use `scripts\build-desktop-windows.bat` and exclude `node_modules` from OneDrive!
