#!/bin/bash
# Clear electron-builder cache to fix symbolic link issues

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Clearing electron-builder cache..."
echo ""

# Determine cache directory based on platform
CACHE_DIR=""
if [[ "$(uname -s)" == MINGW* ]] || [[ "$(uname -s)" == MSYS* ]] || [[ "$OSTYPE" == "msys" ]]; then
    # Windows (Git Bash/MSYS)
    if [ -n "$LOCALAPPDATA" ]; then
        CACHE_DIR="$LOCALAPPDATA/electron-builder/Cache"
    elif [ -n "$HOME" ]; then
        CACHE_DIR="$HOME/AppData/Local/electron-builder/Cache"
    else
        CACHE_DIR="$HOME/.cache/electron-builder"
    fi
elif [[ "$(uname -s)" == Darwin* ]]; then
    # macOS
    CACHE_DIR="$HOME/Library/Caches/electron-builder"
else
    # Linux
    CACHE_DIR="$HOME/.cache/electron-builder"
fi

echo "Cache directory: $CACHE_DIR"
echo ""

if [ -d "$CACHE_DIR" ]; then
    echo "Removing cache directories..."
    
    # Remove winCodeSign cache (causes symlink issues on Windows)
    if [ -d "$CACHE_DIR/winCodeSign" ]; then
        echo "  Removing winCodeSign cache..."
        rm -rf "$CACHE_DIR/winCodeSign" 2>/dev/null || {
            echo "  [WARNING] Could not remove winCodeSign cache"
            echo "  You may need to run as Administrator (Windows)"
        }
    fi
    
    echo ""
    echo "[OK] Cache cleared"
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
