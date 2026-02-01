#!/bin/bash
# Generate mobile app icon (app_icon.png) from SVG or Python fallback.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SVG="$PROJECT_ROOT/app/static/images/timetracker-logo-icon.svg"
OUT="$PROJECT_ROOT/mobile/assets/icon/app_icon.png"

mkdir -p "$(dirname "$OUT")"

# Try ImageMagick first (exact SVG export)
if command -v magick &> /dev/null; then
    if magick "$SVG" -resize 1024x1024 "$OUT"; then
        echo "Generated app_icon.png with ImageMagick"
        exit 0
    fi
fi

# Try Inkscape
if command -v inkscape &> /dev/null; then
    if inkscape "$SVG" -w 1024 -h 1024 -o "$OUT"; then
        echo "Generated app_icon.png with Inkscape"
        exit 0
    fi
fi

# Fallback: Python script (requires Pillow)
python3 "$SCRIPT_DIR/generate-mobile-icon.py"
exit $?
