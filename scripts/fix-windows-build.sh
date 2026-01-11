#!/bin/bash
# Fix Windows/OneDrive build issues for desktop app

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DESKTOP_DIR="$PROJECT_ROOT/desktop"

echo "Fixing Windows/OneDrive build issues..."
echo ""

cd "$DESKTOP_DIR"

# Check if we're on Windows/OneDrive
IS_WINDOWS=false
IS_ONEDRIVE=false
if [[ "$(uname -s)" == MINGW* ]] || [[ "$(uname -s)" == MSYS* ]] || [[ "$(uname -s)" == CYGWIN* ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    IS_WINDOWS=true
fi
if [[ "$PROJECT_ROOT" == *"OneDrive"* ]]; then
    IS_ONEDRIVE=true
fi

if [ "$IS_WINDOWS" = false ] && [ "$IS_ONEDRIVE" = false ]; then
    echo "This script is for Windows/OneDrive issues only."
    echo "Your system doesn't appear to be Windows or using OneDrive."
    exit 0
fi

echo "Detected:"
if [ "$IS_WINDOWS" = true ]; then
    echo "  ✓ Windows environment"
fi
if [ "$IS_ONEDRIVE" = true ]; then
    echo "  ✓ OneDrive location detected"
    echo ""
    echo "WARNING: OneDrive can cause file locking issues with npm!"
    echo ""
fi

# Clean npm cache
echo "Cleaning npm cache..."
npm cache clean --force 2>/dev/null || true
echo "  ✓ Cache cleaned"
echo ""

# Remove problematic node_modules if it exists
if [ -d "node_modules" ]; then
    echo "Removing existing node_modules..."
    echo "  (This may take a moment on Windows/OneDrive)"
    
    # Try to remove with retries
    MAX_RETRIES=3
    RETRY=0
    while [ $RETRY -lt $MAX_RETRIES ]; do
        if rm -rf node_modules 2>/dev/null; then
            echo "  ✓ node_modules removed"
            break
        else
            RETRY=$((RETRY + 1))
            if [ $RETRY -lt $MAX_RETRIES ]; then
                echo "  ⚠ Attempt $RETRY failed, retrying in 2 seconds..."
                sleep 2
            else
                echo "  ✗ Failed to remove node_modules after $MAX_RETRIES attempts"
                echo ""
                echo "Manual steps required:"
                echo "  1. Close all programs (VS Code, terminals, etc.)"
                echo "  2. Open File Explorer"
                echo "  3. Navigate to: $DESKTOP_DIR"
                echo "  4. Delete the 'node_modules' folder manually"
                echo "  5. Run this script again"
                exit 1
            fi
        fi
    done
    echo ""
fi

# Remove package-lock.json if it exists (will be regenerated)
if [ -f "package-lock.json" ]; then
    echo "Removing package-lock.json..."
    rm -f package-lock.json
    echo "  ✓ Removed"
    echo ""
fi

# Reinstall dependencies
echo "Reinstalling dependencies..."
echo "  (This may take several minutes)"
echo ""

if npm install --prefer-offline --no-audit --loglevel=warn; then
    echo ""
    echo "✓ Dependencies installed successfully!"
    echo ""
    echo "Next steps:"
    echo "  1. If using OneDrive, exclude node_modules from sync:"
    echo "     - Right-click desktop/node_modules"
    echo "     - Choose 'Always keep on this device'"
    echo "  2. Run the build script: ./scripts/build-desktop.sh"
else
    echo ""
    echo "✗ Installation failed"
    echo ""
    echo "Additional solutions:"
    echo "  1. Exclude desktop/node_modules from OneDrive sync"
    echo "  2. Run PowerShell/Command Prompt as Administrator"
    echo "  3. Temporarily disable antivirus real-time scanning"
    echo "  4. Move project outside OneDrive folder"
    echo "  5. Use WSL instead of Git Bash"
    exit 1
fi
