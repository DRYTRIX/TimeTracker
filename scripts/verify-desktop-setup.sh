#!/bin/bash
# Verify desktop app setup and dependencies

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DESKTOP_DIR="$PROJECT_ROOT/desktop"

cd "$DESKTOP_DIR"

echo "Verifying desktop app setup..."
echo ""

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "✗ Node.js is not installed"
    exit 1
fi
echo "✓ Node.js: $(node --version)"

# Check npm
if ! command -v npm &> /dev/null; then
    echo "✗ npm is not installed"
    exit 1
fi
echo "✓ npm: $(npm --version)"

# Check node_modules
if [ ! -d "node_modules" ]; then
    echo "✗ node_modules directory not found"
    echo "  Run: npm install"
    exit 1
fi
echo "✓ node_modules exists"

# Check electron
if ! node -e "require('electron')" 2>/dev/null; then
    echo "✗ Electron not found in node_modules"
    echo "  Run: npm install"
    exit 1
fi
echo "✓ Electron installed"

# Check electron-builder
if [ ! -f "node_modules/.bin/electron-builder" ] && [ ! -f "node_modules/electron-builder/out/builder.js" ]; then
    echo "✗ electron-builder not found"
    echo "  Run: npm install"
    exit 1
fi
echo "✓ electron-builder installed"

# Check if electron-builder is accessible via npx
if ! npx --yes electron-builder --version >/dev/null 2>&1; then
    echo "⚠ electron-builder not accessible via npx"
    echo "  This may cause build issues"
else
    echo "✓ electron-builder accessible via npx"
fi

# Check assets
echo ""
echo "Checking assets..."
if [ -f "assets/logo.svg" ]; then
    echo "✓ logo.svg exists"
else
    echo "✗ logo.svg missing"
fi

if [ -f "assets/icon.png" ]; then
    echo "✓ icon.png exists"
else
    echo "⚠ icon.png missing (required for Linux)"
fi

if [ -f "assets/icon.ico" ]; then
    echo "✓ icon.ico exists"
else
    echo "⚠ icon.ico missing (required for Windows)"
fi

if [ -f "assets/icon.icns" ]; then
    echo "✓ icon.icns exists"
else
    echo "⚠ icon.icns missing (required for macOS)"
fi

echo ""
echo "Setup verification complete!"
