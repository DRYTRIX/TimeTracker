#!/bin/bash
# Build script for TimeTracker Mobile App (Flutter)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MOBILE_DIR="$PROJECT_ROOT/mobile"

cd "$PROJECT_ROOT"

# Sync version from setup.py to mobile app
echo "Syncing version from setup.py..."
python3 "$SCRIPT_DIR/sync-mobile-version.py"
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to sync version"
    exit 1
fi
echo ""

cd "$MOBILE_DIR"

echo "Building TimeTracker Mobile App..."
echo ""

# Check Flutter
if ! command -v flutter &> /dev/null; then
    echo "ERROR: Flutter is not installed or not in PATH"
    exit 1
fi

echo "Flutter version:"
flutter --version | head -n 1
echo ""

# Install dependencies
echo "Installing dependencies..."
flutter pub get
echo ""

# Generate app icons (source PNG then launcher sizes)
cd "$PROJECT_ROOT"
"$SCRIPT_DIR/generate-mobile-icon.sh" || true
cd "$MOBILE_DIR"
echo "Generating launcher icons..."
dart run flutter_launcher_icons
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to generate launcher icons"
    exit 1
fi
echo ""

# Analyze
echo "Analyzing code..."
flutter analyze || true
echo ""

# Run tests
echo "Running tests..."
flutter test || true
echo ""

# Build
PLATFORM="${1:-all}"

case "$PLATFORM" in
    android)
        echo "Building Android APK..."
        flutter build apk --release
        echo "Building Android App Bundle..."
        flutter build appbundle --release
        ;;
    ios)
        if [ "$(uname)" != "Darwin" ]; then
            echo "ERROR: iOS builds can only be done on macOS"
            exit 1
        fi
        echo "Building iOS..."
        flutter build ios --release --no-codesign
        ;;
    all)
        echo "Building Android APK..."
        flutter build apk --release
        echo "Building Android App Bundle..."
        flutter build appbundle --release
        if [ "$(uname)" = "Darwin" ]; then
            echo "Building iOS..."
            flutter build ios --release --no-codesign
        fi
        ;;
    *)
        echo "Usage: $0 [android|ios|all]"
        exit 1
        ;;
esac

echo ""
echo "Build complete!"
echo "Outputs: $MOBILE_DIR/build/"
