#!/bin/bash
# Quick check script for desktop assets
# Verifies that required assets are present

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DESKTOP_ASSETS="$PROJECT_ROOT/desktop/assets"

echo "Checking desktop assets..."
echo ""

ALL_OK=true

# Check logo
if [ -f "$DESKTOP_ASSETS/logo.svg" ]; then
    echo "✓ logo.svg exists"
else
    echo "✗ logo.svg MISSING"
    ALL_OK=false
fi

# Check icons
if [ -f "$DESKTOP_ASSETS/icon.png" ]; then
    echo "✓ icon.png exists"
else
    echo "✗ icon.png MISSING (required for Linux builds)"
    ALL_OK=false
fi

if [ -f "$DESKTOP_ASSETS/icon.ico" ]; then
    echo "✓ icon.ico exists"
else
    echo "⚠ icon.ico MISSING (required for Windows builds)"
fi

if [ -f "$DESKTOP_ASSETS/icon.icns" ]; then
    echo "✓ icon.icns exists"
else
    echo "⚠ icon.icns MISSING (required for macOS builds)"
fi

echo ""

if [ "$ALL_OK" = true ]; then
    echo "✓ All critical assets present"
    exit 0
else
    echo "⚠ Some assets are missing"
    echo ""
    echo "To fix:"
    echo "  1. Run: bash scripts/prepare-desktop-assets.sh"
    echo "  2. Or: node scripts/generate-icons.js"
    exit 1
fi
