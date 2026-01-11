#!/bin/bash
# Build script for TimeTracker Desktop App (Electron)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DESKTOP_DIR="$PROJECT_ROOT/desktop"

cd "$DESKTOP_DIR"

echo "Building TimeTracker Desktop App..."
echo ""

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js is not installed or not in PATH"
    exit 1
fi

echo "Node.js version: $(node --version)"
echo "npm version: $(npm --version)"
echo ""

# Install dependencies
echo "Installing dependencies..."
if [ ! -d "node_modules" ]; then
    npm install --prefer-offline --no-audit --loglevel=warn
else
    npm ci --prefer-offline --no-audit --loglevel=warn || npm install --prefer-offline --no-audit --loglevel=warn
fi
echo ""

# Build
PLATFORM="${1:-current}"

case "$PLATFORM" in
    win|windows)
        echo "Building Windows installer..."
        npm run build:win
        ;;
    mac|macos)
        if [ "$(uname)" != "Darwin" ]; then
            echo "ERROR: macOS builds can only be done on macOS"
            exit 1
        fi
        echo "Building macOS DMG..."
        npm run build:mac
        ;;
    linux)
        if [ "$(uname)" = "Darwin" ] || [[ "$(uname)" == MINGW* ]]; then
            echo "ERROR: Linux builds can only be done on Linux"
            exit 1
        fi
        echo "Building Linux packages..."
        npm run build:linux
        ;;
    all|all-platforms)
        echo "Building for all supported platforms..."
        echo "Note: Will automatically build for platforms supported on your OS"
        npm run build:all
        ;;
    current)
        # Build for current platform
        OS=$(uname -s)
        case "$OS" in
            Linux*)
                echo "Building Linux packages..."
                npm run build:linux
                ;;
            Darwin*)
                echo "Building macOS DMG..."
                npm run build:mac
                ;;
            *)
                echo "Unknown platform: $OS"
                echo "Building for all platforms..."
                npm run build
                ;;
        esac
        ;;
    *)
        echo "Usage: $0 [win|mac|linux|all|current]"
        exit 1
        ;;
esac

echo ""
echo "Build complete!"
echo "Outputs: $DESKTOP_DIR/dist/"
