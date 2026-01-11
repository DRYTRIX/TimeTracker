#!/bin/bash
# Build script for TimeTracker Desktop App (Electron)
# For Windows, use build-desktop-windows.bat or build-desktop-windows.ps1 instead

set -e

# Detect if running on Windows and suggest using native scripts
if [[ "$(uname -s)" == MINGW* ]] || [[ "$(uname -s)" == MSYS* ]] || [[ "$OSTYPE" == "msys" ]]; then
    echo "NOTE: You're on Windows. For better compatibility, consider using:"
    echo "  - scripts\build-desktop-windows.bat (Command Prompt)"
    echo "  - scripts\build-desktop-windows.ps1 (PowerShell)"
    echo ""
    read -p "Continue with bash script anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Build cancelled. Use the Windows-native scripts instead."
        exit 0
    fi
    echo ""
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DESKTOP_DIR="$PROJECT_ROOT/desktop"

cd "$PROJECT_ROOT"

# Sync version from setup.py to package.json
echo "Syncing version from setup.py..."
python3 "$SCRIPT_DIR/sync-desktop-version.py"
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to sync version"
    exit 1
fi
echo ""

cd "$DESKTOP_DIR"

echo "Building TimeTracker Desktop App..."
echo ""

# Prepare assets (logo, icons) - only once
# Use a temp file to track if already prepared (works across subshells)
ASSETS_CHECK_FILE="$DESKTOP_DIR/.assets_prepared"
if [ ! -f "$ASSETS_CHECK_FILE" ]; then
    echo "Preparing desktop assets..."
    bash "$SCRIPT_DIR/prepare-desktop-assets.sh" || {
        echo "WARNING: Asset preparation had issues, continuing anyway..."
    }
    touch "$ASSETS_CHECK_FILE"
    echo ""
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js is not installed or not in PATH"
    exit 1
fi

echo "Node.js version: $(node --version)"
echo "npm version: $(npm --version)"
echo ""

# Check for logo file (required for splash screen and branding)
if [ ! -f "assets/logo.svg" ]; then
    echo "WARNING: assets/logo.svg not found"
    echo "  Creating from main logo..."
    if [ -f "$PROJECT_ROOT/app/static/images/timetracker-logo.svg" ]; then
        mkdir -p assets
        cp "$PROJECT_ROOT/app/static/images/timetracker-logo.svg" assets/logo.svg
        echo "  ✓ Logo copied to assets/logo.svg"
    else
        echo "  ERROR: Main logo not found at app/static/images/timetracker-logo.svg"
        echo "  Please ensure the logo file exists"
        exit 1
    fi
fi

# Check for icon files (warn if missing, but don't fail)
# Only check if not already prepared
if [ ! -f "$ASSETS_CHECK_FILE" ]; then
    echo "Checking icon files..."
    MISSING_ICONS=0
    if [ ! -f "assets/icon.ico" ]; then
        echo "  WARNING: assets/icon.ico not found (required for Windows builds)"
        MISSING_ICONS=1
    fi
    if [ ! -f "assets/icon.icns" ]; then
        echo "  WARNING: assets/icon.icns not found (required for macOS builds)"
        MISSING_ICONS=1
    fi
    if [ ! -f "assets/icon.png" ]; then
        echo "  WARNING: assets/icon.png not found (required for Linux builds)"
        MISSING_ICONS=1
    fi

    if [ $MISSING_ICONS -eq 1 ]; then
        echo ""
        echo "NOTE: Some icon files are missing. The build will continue, but:"
        echo "  - Windows builds require icon.ico"
        echo "  - macOS builds require icon.icns"
        echo "  - Linux builds require icon.png"
        echo ""
        echo "To generate icons, run:"
        echo "  node scripts/generate-icons.js"
        echo "  Then convert the generated PNG files to .ico/.icns as needed"
        echo ""
        # On Windows/Git Bash, skip interactive prompt if CI or non-interactive
        if [ -t 0 ] && [ -z "$CI" ]; then
            read -p "Continue anyway? (y/N) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo "Build cancelled"
                exit 1
            fi
        else
            echo "Continuing (non-interactive mode)..."
        fi
        echo ""
    fi
fi

# Install dependencies
echo "Installing dependencies..."

# Check if node_modules exists and is valid
NODE_MODULES_VALID=false
if [ -d "node_modules" ]; then
    # Check if electron-builder is available (either in node_modules/.bin or via npx)
    if [ -f "node_modules/.bin/electron-builder" ] || [ -f "node_modules/electron-builder/out/builder.js" ]; then
        # Try a quick test to see if electron is accessible
        if node -e "require('electron')" 2>/dev/null; then
            NODE_MODULES_VALID=true
            echo "  ✓ node_modules appears valid, skipping install"
        fi
    fi
fi

    if [ "$NODE_MODULES_VALID" = false ] || [ ! -f "node_modules/.bin/electron-builder" ]; then
    # Detect Windows/OneDrive issues
    IS_WINDOWS=false
    IS_ONEDRIVE=false
    if [[ "$(uname -s)" == MINGW* ]] || [[ "$(uname -s)" == MSYS* ]] || [[ "$(uname -s)" == CYGWIN* ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        IS_WINDOWS=true
    fi
    if [[ "$PROJECT_ROOT" == *"OneDrive"* ]]; then
        IS_ONEDRIVE=true
    fi
    
    if [ ! -d "node_modules" ]; then
        echo "  Installing dependencies (first time)..."
        if ! npm install --prefer-offline --no-audit --loglevel=warn; then
            echo ""
            echo "ERROR: npm install failed"
            if [ "$IS_WINDOWS" = true ] || [ "$IS_ONEDRIVE" = true ]; then
                echo ""
                echo "This is a common issue on Windows, especially with OneDrive:"
                echo "  - OneDrive file locking prevents npm from working properly"
                echo "  - Antivirus may be scanning files during install"
                echo "  - File permissions may be restricted"
                echo ""
                echo "Solutions:"
                echo "  1. Exclude node_modules from OneDrive sync:"
                echo "     - Right-click desktop/node_modules folder"
                echo "     - Choose 'Always keep on this device' or exclude from sync"
                echo "  2. Temporarily disable antivirus real-time scanning"
                echo "  3. Run as Administrator"
                echo "  4. Move project outside OneDrive folder"
                echo "  5. Use WSL instead of Git Bash"
                echo ""
            else
                echo ""
                echo "This is common on Linux/Mac, especially when:"
                echo "  - Files are locked by another process"
                echo "  - Insufficient permissions (try with sudo)"
                echo "  - On WSL: Project is in OneDrive (file locking)"
                echo ""
                echo "Solutions:"
                echo "  1. Run: scripts/fix-desktop-build.sh"
                echo "  2. Check file permissions: ls -la"
                echo "  3. If on WSL with OneDrive: Exclude node_modules from sync"
                echo "  4. Try: sudo npm install (if permission issue)"
                echo ""
            fi
            exit 1
        fi
    else
        echo "  Updating dependencies..."
        # Try npm ci first (faster, more reliable)
        if ! npm ci --prefer-offline --no-audit --loglevel=warn 2>&1; then
            echo "  npm ci failed, trying npm install..."
            # Clean npm cache and retry
            if [ "$IS_WINDOWS" = true ] || [ "$IS_ONEDRIVE" = true ]; then
                echo "  Attempting to fix Windows/OneDrive issues..."
                # Try with different flags for Windows
                if ! npm install --prefer-offline --no-audit --loglevel=warn --no-optional 2>&1; then
                    echo ""
                    echo "ERROR: npm install failed"
                    echo ""
                    echo "Windows/OneDrive specific solutions:"
                    echo "  1. Close all programs that might be using node_modules"
                    echo "  2. Exclude desktop/node_modules from OneDrive sync"
                    echo "  3. Run PowerShell as Administrator and try again"
                    echo "  4. Delete node_modules and try: npm install"
                    echo "  5. Move project outside OneDrive"
                    echo ""
                    echo "To delete node_modules and retry:"
                    echo "  cd desktop"
                    echo "  rm -rf node_modules"
                    echo "  npm install"
                    echo ""
                    exit 1
                fi
            else
                if ! npm install --prefer-offline --no-audit --loglevel=warn; then
                    echo ""
                    echo "ERROR: npm install failed"
                    echo ""
                    echo "Solutions:"
                    echo "  1. Run: scripts/fix-desktop-build.sh"
                    echo "  2. Check file permissions: ls -la"
                    echo "  3. If on WSL with OneDrive: Exclude node_modules from sync"
                    echo "  4. Try: sudo npm install (if permission issue)"
                    echo ""
                    exit 1
                fi
            fi
        fi
    fi
fi
echo ""

# Build
PLATFORM="${1:-current}"

# Detect platform more accurately (handle Git Bash on Windows)
detect_platform() {
    local os=$(uname -s)
    # Git Bash on Windows reports as MINGW64_NT or MINGW32_NT
    if [[ "$os" == MINGW* ]] || [[ "$os" == MSYS* ]] || [[ "$os" == CYGWIN* ]]; then
        echo "win32"
    elif [[ "$os" == Linux* ]]; then
        echo "linux"
    elif [[ "$os" == Darwin* ]]; then
        echo "darwin"
    else
        echo "unknown"
    fi
}

CURRENT_PLATFORM=$(detect_platform)

case "$PLATFORM" in
    win|windows)
        if [ "$CURRENT_PLATFORM" != "win32" ] && [ "$CURRENT_PLATFORM" != "unknown" ]; then
            echo "WARNING: Building Windows installer on non-Windows platform"
            echo "  This may not work correctly. Use CI/CD for cross-platform builds."
        fi
        
        # Clear electron-builder cache to prevent code signing download (Windows only)
        if [ "$CURRENT_PLATFORM" = "win32" ]; then
            # Try both Windows path formats (Git Bash may use different env vars)
            CACHE_BASE=""
            if [ -n "$LOCALAPPDATA" ]; then
                CACHE_BASE="$LOCALAPPDATA/electron-builder"
            elif [ -n "$HOME" ]; then
                CACHE_BASE="$HOME/AppData/Local/electron-builder"
            fi
            
            if [ -n "$CACHE_BASE" ] && [ -d "$CACHE_BASE/Cache/winCodeSign" ]; then
                echo "Clearing winCodeSign cache (prevents symlink errors)..."
                rm -rf "$CACHE_BASE/Cache/winCodeSign" 2>/dev/null || true
                echo ""
            fi
        fi
        
        echo "Building Windows installer..."
        echo "NOTE: Code signing is disabled (sign: null)"
        echo ""
        
        # Set environment variable to prevent code signing
        export CSC_IDENTITY_AUTO_DISCOVERY=false
        
        echo "  If you get symbolic link errors:"
        echo "  1. Enable Developer Mode: Win+I > Privacy & Security > For developers"
        echo "  2. Or run PowerShell/CMD as Administrator"
        echo "  3. Or run: ./scripts/clear-all-electron-cache.sh"
        echo ""
        CSC_IDENTITY_AUTO_DISCOVERY=false npx --yes electron-builder --win
        if [ $? -ne 0 ]; then
            echo ""
            echo "ERROR: Windows build failed"
            echo ""
            echo "Common issues:"
            echo "  - Missing icon.ico file (generate with: node scripts/generate-icons.js)"
            echo "  - Symbolic link errors (enable Developer Mode or run as Administrator)"
            echo "  - Insufficient permissions"
            echo "  - Antivirus blocking the build"
            echo ""
            exit 1
        fi
        ;;
    mac|macos)
        if [ "$CURRENT_PLATFORM" != "darwin" ]; then
            echo "ERROR: macOS builds can only be done on macOS"
            exit 1
        fi
        echo "Building macOS DMG..."
        npx --yes electron-builder --mac
        if [ $? -ne 0 ]; then
            echo "ERROR: macOS build failed"
            exit 1
        fi
        ;;
    linux)
        if [ "$CURRENT_PLATFORM" != "linux" ]; then
            echo "ERROR: Linux builds can only be done on Linux"
            exit 1
        fi
        echo "Building Linux packages..."
        npx --yes electron-builder --linux
        if [ $? -ne 0 ]; then
            echo "ERROR: Linux build failed"
            exit 1
        fi
        ;;
    all|all-platforms)
        echo "Building for all supported platforms..."
        echo "Note: Will automatically build for platforms supported on your OS"
        npx --yes electron-builder --win --mac --linux
        if [ $? -ne 0 ]; then
            echo "ERROR: Build failed"
            exit 1
        fi
        ;;
    current)
        # Build for current platform
        case "$CURRENT_PLATFORM" in
            win32)
                echo "Detected Windows (Git Bash/MSYS)"
                
                # Clear electron-builder cache to prevent code signing download
                CACHE_BASE=""
                if [ -n "$LOCALAPPDATA" ]; then
                    CACHE_BASE="$LOCALAPPDATA/electron-builder"
                elif [ -n "$HOME" ]; then
                    CACHE_BASE="$HOME/AppData/Local/electron-builder"
                fi
                
                if [ -n "$CACHE_BASE" ] && [ -d "$CACHE_BASE/Cache/winCodeSign" ]; then
                    echo "Clearing winCodeSign cache (prevents symlink errors)..."
                    rm -rf "$CACHE_BASE/Cache/winCodeSign" 2>/dev/null || true
                    echo ""
                fi
                
                echo "Building Windows installer..."
                echo "NOTE: Code signing is disabled (sign: null)"
                echo ""
                
                # Set ALL environment variables to prevent code signing completely
                export CSC_IDENTITY_AUTO_DISCOVERY=false
                export WIN_CSC_LINK=""
                export WIN_CSC_KEY_PASSWORD=""
                export CSC_LINK=""
                export CSC_KEY_PASSWORD=""
                
                echo "  If you STILL get symbolic link errors:"
                echo "  1. Enable Developer Mode: Win+I > Privacy & Security > For developers"
                echo "  2. Or run PowerShell/CMD as Administrator"
                echo "  3. Or run: ./scripts/clear-all-electron-cache.sh"
                echo "  4. Or try: ./scripts/build-desktop-no-sign.sh (more aggressive)"
                echo ""
                
                # Build with multiple env vars and explicit CLI flags to ensure no code signing
                CSC_IDENTITY_AUTO_DISCOVERY=false \
                WIN_CSC_LINK="" \
                CSC_LINK="" \
                npx --yes electron-builder --win --config.win.sign=null --config.win.signingHashAlgorithms=null --config.win.signDlls=false 2>&1 | tee /tmp/electron-builder.log || {
                    echo ""
                    echo "Build failed. Checking if it's the symlink issue..."
                    if grep -q "symbolic link" /tmp/electron-builder.log 2>/dev/null || grep -q "winCodeSign" /tmp/electron-builder.log 2>/dev/null; then
                        echo ""
                        echo "================================================================================"
                        echo "SYMLINK ERROR DETECTED!"
                        echo "================================================================================"
                        echo ""
                        echo "electron-builder is still trying to download code signing tools."
                        echo ""
                        echo "SOLUTION: Use the no-sign build script instead:"
                        echo "  ./scripts/build-desktop-no-sign.sh"
                        echo ""
                        echo "Or manually enable Developer Mode in Windows:"
                        echo "  Win+I > Privacy & Security > For developers > Developer Mode"
                        echo ""
                        echo "================================================================================"
                    fi
                    exit 1
                }
                if [ $? -ne 0 ]; then
                    echo ""
                    echo "ERROR: Windows build failed"
                    echo ""
                    echo "Common issues:"
                    echo "  - Missing icon.ico file (generate with: node scripts/generate-icons.js)"
                    echo "  - Symbolic link errors (enable Developer Mode or run as Administrator)"
                    echo "  - Insufficient permissions"
                    echo ""
                    exit 1
                fi
                ;;
            linux)
                echo "Detected Linux"
                echo "Building Linux packages..."
                npx --yes electron-builder --linux
                if [ $? -ne 0 ]; then
                    echo "ERROR: Linux build failed"
                    exit 1
                fi
                ;;
            darwin)
                echo "Detected macOS"
                echo "Building macOS DMG..."
                npx --yes electron-builder --mac
                if [ $? -ne 0 ]; then
                    echo "ERROR: macOS build failed"
                    exit 1
                fi
                ;;
            *)
                echo "Unknown platform: $(uname -s)"
                echo "Attempting to build for Windows (default)..."
                npx --yes electron-builder --win
                if [ $? -ne 0 ]; then
                    echo "ERROR: Build failed"
                    exit 1
                fi
                ;;
        esac
        ;;
    *)
        echo "Usage: $0 [win|mac|linux|all|current]"
        exit 1
        ;;
esac

# Clean up assets check file
rm -f "$ASSETS_CHECK_FILE" 2>/dev/null || true

echo ""
echo "========================================"
echo "Build complete!"
echo "========================================"
echo ""
echo "Outputs: $DESKTOP_DIR/dist/"
if [ "$CURRENT_PLATFORM" = "win32" ]; then
    echo ""
    if [ -d "$DESKTOP_DIR/dist" ]; then
        echo "Built files:"
        ls -lh "$DESKTOP_DIR/dist"/*.exe 2>/dev/null || ls -lh "$DESKTOP_DIR/dist"/*.nsis 2>/dev/null || echo "  (Check dist/ directory for build outputs)"
    fi
fi
