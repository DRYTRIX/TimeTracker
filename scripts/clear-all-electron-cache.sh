#!/bin/bash
# Clear all electron-builder cache to fix symlink and code signing issues

set -e

echo "Clearing all electron-builder cache..."
echo ""

# Determine cache directory based on platform
CACHE_BASE=""
if [[ "$(uname -s)" == MINGW* ]] || [[ "$(uname -s)" == MSYS* ]] || [[ "$OSTYPE" == "msys" ]]; then
    # Windows (Git Bash/MSYS)
    if [ -n "$LOCALAPPDATA" ]; then
        CACHE_BASE="$LOCALAPPDATA/electron-builder"
    elif [ -n "$HOME" ]; then
        CACHE_BASE="$HOME/AppData/Local/electron-builder"
    else
        CACHE_BASE="$HOME/.cache/electron-builder"
    fi
elif [[ "$(uname -s)" == Darwin* ]]; then
    # macOS
    CACHE_BASE="$HOME/Library/Caches/electron-builder"
else
    # Linux
    CACHE_BASE="$HOME/.cache/electron-builder"
fi

if [ -z "$CACHE_BASE" ]; then
    echo "ERROR: Could not determine cache directory"
    exit 1
fi

echo "Cache directory: $CACHE_BASE"
echo ""

if [ -d "$CACHE_BASE" ]; then
    echo "Removing entire electron-builder cache..."
    rm -rf "$CACHE_BASE" 2>/dev/null || {
        echo "[WARNING] Could not remove cache directory"
        echo "  You may need to run as Administrator (Windows)"
        echo "  Or manually delete: $CACHE_BASE"
        exit 1
    }
    echo "[OK] Cache cleared successfully"
else
    echo "[OK] Cache directory does not exist"
fi

echo ""
echo "Next steps:"
if [[ "$(uname -s)" == MINGW* ]] || [[ "$(uname -s)" == MSYS* ]]; then
    echo "  1. Enable Developer Mode in Windows (recommended)"
    echo "     - Win+I > Privacy & Security > For developers"
    echo "     - Enable Developer Mode"
    echo "  2. Or run PowerShell/CMD as Administrator"
    echo "  3. Build again: ./scripts/build-desktop.sh"
else
    echo "  1. Build again: ./scripts/build-desktop.sh"
fi
echo ""
