#!/bin/bash
# Build script for TimeTracker Mobile and Desktop Apps
# Supports: Linux, macOS

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Check prerequisites
check_flutter() {
    if ! command -v flutter &> /dev/null; then
        print_error "Flutter is not installed or not in PATH"
        echo "Please install Flutter from: https://flutter.dev/docs/get-started/install"
        exit 1
    fi
    print_success "Flutter found: $(flutter --version | head -n 1)"
}

check_node() {
    if ! command -v node &> /dev/null; then
        print_error "Node.js is not installed or not in PATH"
        echo "Please install Node.js 18+ from: https://nodejs.org/"
        exit 1
    fi
    print_success "Node.js found: $(node --version)"
}

check_npm() {
    if ! command -v npm &> /dev/null; then
        print_error "npm is not installed or not in PATH"
        exit 1
    fi
    print_success "npm found: $(npm --version)"
}

# Build functions
build_mobile() {
    print_header "Building Mobile App (Flutter)"
    
    cd "$PROJECT_ROOT/mobile"
    
    # Check if Flutter is available
    check_flutter
    
    # Get dependencies
    print_header "Installing Flutter dependencies"
    flutter pub get
    
    # Analyze code
    print_header "Analyzing Flutter code"
    flutter analyze || print_warning "Code analysis found issues (continuing anyway)"
    
    # Run tests
    print_header "Running Flutter tests"
    flutter test || print_warning "Some tests failed (continuing anyway)"
    
    # Build Android
    if [ "$BUILD_ANDROID" = "true" ] || [ "$1" = "android" ] || [ "$1" = "all" ] || [ -z "$1" ]; then
        print_header "Building Android APK"
        flutter build apk --release
        
        if [ -f "build/app/outputs/flutter-apk/app-release.apk" ]; then
            print_success "Android APK built successfully"
            echo "  Location: $PROJECT_ROOT/mobile/build/app/outputs/flutter-apk/app-release.apk"
        else
            print_error "Android APK build failed"
        fi
        
        print_header "Building Android App Bundle"
        flutter build appbundle --release
        
        if [ -f "build/app/outputs/bundle/release/app-release.aab" ]; then
            print_success "Android App Bundle built successfully"
            echo "  Location: $PROJECT_ROOT/mobile/build/app/outputs/bundle/release/app-release.aab"
        else
            print_error "Android App Bundle build failed"
        fi
    fi
    
    # Build iOS
    if [ "$(uname)" = "Darwin" ]; then
        if [ "$BUILD_IOS" = "true" ] || [ "$1" = "ios" ] || [ "$1" = "all" ] || [ -z "$1" ]; then
            print_header "Building iOS"
            flutter build ios --release --no-codesign
            
            if [ -d "build/ios/iphoneos/Runner.app" ]; then
                print_success "iOS app built successfully"
                echo "  Location: $PROJECT_ROOT/mobile/build/ios/iphoneos/Runner.app"
                print_warning "iOS build requires code signing for device installation"
                echo "  Use Xcode to archive and distribute the app"
            else
                print_error "iOS build failed"
            fi
        fi
    else
        print_warning "iOS builds can only be done on macOS"
    fi
}

build_desktop() {
    print_header "Building Desktop App (Electron)"
    
    cd "$PROJECT_ROOT/desktop"
    
    # Check prerequisites
    check_node
    check_npm
    
    # Install dependencies
    print_header "Installing npm dependencies"
    if [ ! -d "node_modules" ]; then
        npm install --prefer-offline --no-audit --loglevel=warn
    else
        npm ci --prefer-offline --no-audit --loglevel=warn || npm install --prefer-offline --no-audit --loglevel=warn
    fi
    
    # Run tests (if available)
    if [ -f "package.json" ] && grep -q '"test"' package.json; then
        print_header "Running tests"
        npm test || print_warning "Some tests failed (continuing anyway)"
    fi
    
    # Build based on platform
    PLATFORM=$(uname -s)
    
    # Check if building for all platforms
    if [ "$1" = "all-platforms" ] || [ "$1" = "all-desktop" ]; then
        print_header "Building for all supported platforms"
        print_warning "Note: Will automatically build for platforms supported on your OS"
        npm run build:all
        return 0
    fi
    
    case "$PLATFORM" in
        Linux*)
            if [ "$BUILD_LINUX" = "true" ] || [ "$1" = "linux" ] || [ "$1" = "all" ] || [ -z "$1" ]; then
                print_header "Building Linux packages"
                npm run build:linux
                
                if [ -d "dist" ] && [ "$(ls -A dist/*.AppImage dist/*.deb 2>/dev/null)" ]; then
                    print_success "Linux packages built successfully"
                    echo "  Location: $PROJECT_ROOT/desktop/dist/"
                    ls -lh dist/*.AppImage dist/*.deb 2>/dev/null || true
                else
                    print_error "Linux build failed"
                fi
            fi
            ;;
        Darwin*)
            if [ "$BUILD_MACOS" = "true" ] || [ "$1" = "macos" ] || [ "$1" = "all" ] || [ -z "$1" ]; then
                print_header "Building macOS DMG"
                npm run build:mac
                
                if [ -d "dist" ] && [ -f "dist"/*.dmg ]; then
                    print_success "macOS DMG built successfully"
                    echo "  Location: $PROJECT_ROOT/desktop/dist/"
                    ls -lh dist/*.dmg
                else
                    print_error "macOS build failed"
                fi
            fi
            ;;
        MINGW*|MSYS*|CYGWIN*)
            print_warning "Use build-all.bat for Windows builds"
            ;;
        *)
            print_warning "Unknown platform: $PLATFORM"
            ;;
    esac
}

# Main script
main() {
    print_header "TimeTracker - Build All Script"
    echo ""
    
    # Parse arguments
    BUILD_MOBILE=false
    BUILD_DESKTOP=false
    PLATFORM_ARG=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --mobile-only)
                BUILD_MOBILE=true
                BUILD_DESKTOP=false
                shift
                ;;
            --desktop-only)
                BUILD_MOBILE=false
                BUILD_DESKTOP=true
                shift
                ;;
            --android-only)
                BUILD_ANDROID=true
                BUILD_IOS=false
                BUILD_MOBILE=true
                BUILD_DESKTOP=false
                shift
                ;;
            --ios-only)
                BUILD_IOS=true
                BUILD_ANDROID=false
                BUILD_MOBILE=true
                BUILD_DESKTOP=false
                shift
                ;;
            --linux-only)
                BUILD_LINUX=true
                BUILD_MACOS=false
                BUILD_MOBILE=false
                BUILD_DESKTOP=true
                shift
                ;;
            --macos-only)
                BUILD_MACOS=true
                BUILD_LINUX=false
                BUILD_MOBILE=false
                BUILD_DESKTOP=true
                shift
                ;;
            android|ios|linux|macos|all|all-platforms|all-desktop)
                PLATFORM_ARG="$1"
                shift
                ;;
            *)
                echo "Unknown option: $1"
                echo "Usage: $0 [--mobile-only|--desktop-only|--android-only|--ios-only|--linux-only|--macos-only] [platform]"
                exit 1
                ;;
        esac
    done
    
    # Default: build both if no flags specified
    if [ "$BUILD_MOBILE" = "false" ] && [ "$BUILD_DESKTOP" = "false" ]; then
        BUILD_MOBILE=true
        BUILD_DESKTOP=true
    fi
    
    # Build mobile
    if [ "$BUILD_MOBILE" = "true" ]; then
        build_mobile "$PLATFORM_ARG"
        echo ""
    fi
    
    # Build desktop
    if [ "$BUILD_DESKTOP" = "true" ]; then
        build_desktop "$PLATFORM_ARG"
        echo ""
    fi
    
    print_header "Build Complete!"
    echo ""
    echo "Build outputs:"
    if [ "$BUILD_MOBILE" = "true" ]; then
        echo "  Mobile: $PROJECT_ROOT/mobile/build/"
    fi
    if [ "$BUILD_DESKTOP" = "true" ]; then
        echo "  Desktop: $PROJECT_ROOT/desktop/dist/"
    fi
}

# Run main function
main "$@"
