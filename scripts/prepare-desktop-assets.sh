#!/bin/bash
# Prepare desktop assets before building
# Ensures logo and icon files are available

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DESKTOP_ASSETS="$PROJECT_ROOT/desktop/assets"
MAIN_LOGO="$PROJECT_ROOT/app/static/images/timetracker-logo.svg"

# Skip if already prepared (avoid duplicate output)
if [ -n "$ASSETS_PREPARED" ]; then
    exit 0
fi

echo "Preparing desktop assets..."

# Ensure assets directory exists
mkdir -p "$DESKTOP_ASSETS"

# Copy logo if missing
if [ ! -f "$DESKTOP_ASSETS/logo.svg" ]; then
    if [ -f "$MAIN_LOGO" ]; then
        echo "Copying logo to desktop/assets/logo.svg..."
        cp "$MAIN_LOGO" "$DESKTOP_ASSETS/logo.svg"
        echo "  ✓ Logo copied"
    else
        echo "ERROR: Main logo not found at $MAIN_LOGO"
        exit 1
    fi
else
    echo "  ✓ Logo already exists"
fi

# Check for icon files
MISSING_ICONS=0
if [ ! -f "$DESKTOP_ASSETS/icon.png" ]; then
    echo "  ⚠ icon.png not found (will be generated if possible)"
    MISSING_ICONS=1
fi
if [ ! -f "$DESKTOP_ASSETS/icon.ico" ]; then
    echo "  ⚠ icon.ico not found (required for Windows builds)"
    MISSING_ICONS=1
fi
if [ ! -f "$DESKTOP_ASSETS/icon.icns" ]; then
    echo "  ⚠ icon.icns not found (required for macOS builds)"
    MISSING_ICONS=1
fi

# Try to generate PNG icon if sharp is available
if [ ! -f "$DESKTOP_ASSETS/icon.png" ] && command -v node &> /dev/null; then
    if [ -f "$PROJECT_ROOT/scripts/generate-icons.js" ]; then
        echo "Attempting to generate icon.png..."
        cd "$PROJECT_ROOT"
        if node scripts/generate-icons.js 2>/dev/null; then
            echo "  ✓ Icon generation attempted"
        else
            echo "  ⚠ Icon generation failed (sharp may not be installed)"
        fi
    fi
fi

if [ $MISSING_ICONS -eq 1 ]; then
    echo ""
    echo "NOTE: Some icon files are missing. The build will continue, but:"
    echo "  - Windows builds require icon.ico (convert from PNG)"
    echo "  - macOS builds require icon.icns (convert from PNG)"
    echo "  - Linux builds require icon.png"
    echo ""
    echo "To generate icons:"
    echo "  1. Install sharp: npm install sharp"
    echo "  2. Run: node scripts/generate-icons.js"
    echo "  3. Convert PNG to .ico/.icns using online tools or ImageMagick"
    echo ""
fi

echo "Asset preparation complete!"
