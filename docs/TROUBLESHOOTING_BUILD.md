# Build Troubleshooting Guide

## Common Issues and Solutions

### Windows/OneDrive Permission Errors

**Error:**
```
npm ERR! code EPERM
npm ERR! syscall rmdir
npm ERR! Error: EPERM: operation not permitted
```

**Cause:**
- OneDrive file locking prevents npm from modifying files
- Antivirus scanning files during installation
- File permissions restricted

**Solutions:**

1. **Exclude node_modules from OneDrive Sync:**
   - Right-click `desktop/node_modules` folder
   - Choose "Always keep on this device" or exclude from sync
   - This is the most effective solution

2. **Run Fix Script:**
   ```bash
   ./scripts/fix-windows-build.sh
   ```

3. **Manual Cleanup:**
   ```bash
   cd desktop
   rm -rf node_modules
   rm -f package-lock.json
   npm install
   ```

4. **Run as Administrator:**
   - Right-click Git Bash / PowerShell
   - Choose "Run as Administrator"
   - Run build script again

5. **Temporarily Disable Antivirus:**
   - Disable real-time scanning temporarily
   - Run npm install
   - Re-enable antivirus

6. **Move Project Outside OneDrive:**
   - Move entire project to a non-OneDrive location
   - This prevents all OneDrive-related issues

7. **Use WSL Instead:**
   - Install WSL (Windows Subsystem for Linux)
   - Run build scripts from WSL terminal
   - WSL handles file permissions better

### Missing Icon Files

**Warning:**
```
⚠ icon.png not found (required for Linux builds)
⚠ icon.ico not found (required for Windows builds)
⚠ icon.icns not found (required for macOS builds)
```

**Solution:**
```bash
# Install sharp for icon generation
npm install sharp

# Generate icons
node scripts/generate-icons.js

# Convert to platform formats:
# - Windows: Use online converter or ImageMagick to convert PNG to ICO
# - macOS: Use iconutil or online converter to convert PNG to ICNS
# - Linux: PNG is already generated
```

### npm Install Fails

**Error:**
```
npm ERR! code EACCES
npm ERR! syscall access
```

**Solutions:**

1. **Check Permissions:**
   ```bash
   ls -la desktop/
   ```

2. **Fix Permissions (Linux/Mac):**
   ```bash
   sudo chown -R $(whoami) desktop/
   ```

3. **Clear npm Cache:**
   ```bash
   npm cache clean --force
   ```

4. **Remove node_modules and Retry:**
   ```bash
   cd desktop
   rm -rf node_modules package-lock.json
   npm install
   ```

### Build Script Issues

**Problem: Asset preparation runs twice**

**Solution:**
- This is fixed in the latest version
- The script now checks if assets are already prepared

**Problem: Interactive prompts don't work**

**Solution:**
- Scripts now detect non-interactive mode
- Use environment variable: `CI=true` to skip prompts

### Platform-Specific Issues

#### Windows

**Issue: Can't build for macOS/Linux on Windows**

**Solution:**
- Windows builds can only create Windows installers
- Use GitHub Actions or CI/CD for cross-platform builds
- Or use WSL for Linux builds

#### macOS

**Issue: Can't build for Windows/Linux on macOS**

**Solution:**
- macOS builds can create macOS DMGs
- Use GitHub Actions for cross-platform builds

#### Linux

**Issue: Can't build for Windows/macOS on Linux**

**Solution:**
- Linux builds can create Linux packages
- Use GitHub Actions for cross-platform builds

### Version Sync Issues

**Error:**
```
ERROR: Failed to sync version
```

**Solution:**
- Ensure `setup.py` exists and has a version
- Check Python 3 is available: `python3 --version`
- Verify `desktop/package.json` is writable

### Electron Builder Issues

**Error:**
```
Error: Application entry file "src/main/main.js" in the "package.json" is missing
```

**Solution:**
- Verify `desktop/src/main/main.js` exists
- Check `desktop/package.json` has correct "main" field
- Ensure all source files are present

**Error:**
```
Error: icon.ico not found
```

**Solution:**
- Generate icons: `node scripts/generate-icons.js`
- Convert PNG to ICO for Windows builds
- Or build for a platform that doesn't require that icon

## Quick Fixes

### Complete Reset (Windows/OneDrive)

```bash
# 1. Fix Windows build issues
./scripts/fix-windows-build.sh

# 2. Generate icons
npm install sharp
node scripts/generate-icons.js

# 3. Build
./scripts/build-desktop.sh
```

### Complete Reset (Linux/Mac)

```bash
# 1. Clean everything
cd desktop
rm -rf node_modules package-lock.json
npm cache clean --force

# 2. Reinstall
npm install

# 3. Generate icons
cd ..
npm install sharp
node scripts/generate-icons.js

# 4. Build
./scripts/build-desktop.sh
```

## Getting Help

If issues persist:

1. **Check Logs:**
   - npm logs: `%APPDATA%\npm-cache\_logs\` (Windows)
   - npm logs: `~/.npm/_logs/` (Linux/Mac)

2. **Verify Environment:**
   ```bash
   node --version  # Should be 18+
   npm --version   # Should be 9+
   ```

3. **Check File System:**
   - Ensure sufficient disk space
   - Check file system permissions
   - Verify no file locks

4. **Create Issue:**
   - Include error messages
   - Include OS and Node.js version
   - Include steps to reproduce

---

**Last Updated:** 2024
