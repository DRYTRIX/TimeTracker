#!/bin/bash
# Build script that completely prevents code signing and winCodeSign download

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DESKTOP_DIR="$PROJECT_ROOT/desktop"

cd "$PROJECT_ROOT"

# Function to detect platform
detect_platform() {
    local uname_out=$(uname -s)
    case "${uname_out}" in
        Linux*)     echo "linux" ;;
        Darwin*)    echo "darwin" ;;
        MINGW*|MSYS*|CYGWIN*)
            echo "win32" ;;
        *)          echo "unknown" ;;
    esac
}

PLATFORM=$(detect_platform)

echo "Building TimeTracker Desktop App (NO CODE SIGNING)..."
echo ""

# Set ALL code signing environment variables to prevent downloads
export CSC_IDENTITY_AUTO_DISCOVERY=false
export WIN_CSC_LINK=""
export WIN_CSC_KEY_PASSWORD=""
export CSC_LINK=""
export CSC_KEY_PASSWORD=""
export APPLE_ID=""
export APPLE_ID_PASSWORD=""
export APPLE_TEAM_ID=""

# Clear ALL electron-builder cache
echo "Clearing electron-builder cache completely..."
CACHE_BASE=""
if [ "$PLATFORM" = "win32" ]; then
    if [ -n "$LOCALAPPDATA" ]; then
        CACHE_BASE="$LOCALAPPDATA/electron-builder"
    elif [ -n "$HOME" ]; then
        CACHE_BASE="$HOME/AppData/Local/electron-builder"
    fi
else
    if [ "$PLATFORM" = "darwin" ]; then
        CACHE_BASE="$HOME/Library/Caches/electron-builder"
    else
        CACHE_BASE="$HOME/.cache/electron-builder"
    fi
fi

if [ -n "$CACHE_BASE" ] && [ -d "$CACHE_BASE" ]; then
    echo "Removing: $CACHE_BASE"
    rm -rf "$CACHE_BASE" 2>/dev/null || {
        echo "[WARNING] Could not remove cache (may need Admin rights)"
        echo "  Manually delete: $CACHE_BASE"
    }
fi

echo ""
echo "Environment variables set:"
echo "  CSC_IDENTITY_AUTO_DISCOVERY=false"
echo "  WIN_CSC_LINK=''"
echo "  CSC_LINK=''"
echo ""

cd "$DESKTOP_DIR"

# Build with explicit no-sign configuration using CLI flags only (no temp config)
echo "Building with explicit no-sign configuration..."
echo ""

case "$PLATFORM" in
    win32)
        echo "Building Windows installer..."
        echo "Using explicit CLI flags to disable code signing..."
        CSC_IDENTITY_AUTO_DISCOVERY=false \
        WIN_CSC_LINK="" \
        CSC_LINK="" \
        npx --yes electron-builder --win
        ;;
    darwin)
        echo "Building macOS installer..."
        echo "Using explicit CLI flags to disable code signing..."
        CSC_IDENTITY_AUTO_DISCOVERY=false \
        CSC_LINK="" \
        APPLE_ID="" \
        APPLE_ID_PASSWORD="" \
        npx --yes electron-builder --mac --config.mac.sign=null
        ;;
    linux)
        echo "Building Linux installer..."
        echo "Linux doesn't require code signing configuration..."
        CSC_IDENTITY_AUTO_DISCOVERY=false \
        npx --yes electron-builder --linux
        ;;
    *)
        echo "ERROR: Unknown platform: $PLATFORM"
        exit 1
        ;;
esac

if [ $? -eq 0 ]; then
    echo ""
    echo "[SUCCESS] Build completed without code signing!"
else
    echo ""
    echo "[ERROR] Build failed"
    exit 1
fi
