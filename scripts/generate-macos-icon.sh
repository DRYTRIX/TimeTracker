#!/bin/bash
# Generate icon.icns from icon.iconset (macOS only)
# Run after: npm run generate:icons
# Requires: iconutil (built-in on macOS)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ICONSET="$PROJECT_ROOT/desktop/assets/icon.iconset"
ICNS_OUT="$PROJECT_ROOT/desktop/assets/icon.icns"

if [ ! -d "$ICONSET" ]; then
  echo "Error: icon.iconset not found. Run 'npm run generate:icons' first."
  exit 1
fi

iconutil -c icns "$ICONSET" -o "$ICNS_OUT"
echo "Created $ICNS_OUT"
