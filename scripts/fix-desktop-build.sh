#!/bin/bash
# Fix script for npm permission errors on Linux/Mac

# Don't use set -e here as we want to handle errors gracefully
set -u  # Fail on undefined variables

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DESKTOP_DIR="$PROJECT_ROOT/desktop"

echo "========================================"
echo "Fixing npm permission errors..."
echo "========================================"
echo ""

cd "$DESKTOP_DIR"

# Check if running on WSL (Windows Subsystem for Linux)
if grep -qi microsoft /proc/version 2>/dev/null; then
    echo "WARNING: Running on WSL (Windows Subsystem for Linux)!"
    echo "If project is in OneDrive on Windows, you may encounter file locking issues."
    echo ""
    echo "RECOMMENDED: Move project outside OneDrive or exclude node_modules from sync"
    echo ""
    read -p "Press Enter to continue..." || true
fi

echo "Cleaning npm cache..."
npm cache clean --force 2>/dev/null || echo "WARNING: npm cache clean failed, continuing..."
echo ""

# Try to remove problematic temp directories
echo "Attempting to remove problematic directories..."
if [ -d "node_modules" ]; then
    # Remove extract-zip temp directories
    find node_modules -type d -name ".extract-zip-*" -exec rm -rf {} + 2>/dev/null || true
fi

# Ask if user wants to remove node_modules entirely
echo ""
read -p "Remove entire node_modules folder and reinstall? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Removing node_modules..."
    if [ -d "node_modules" ]; then
        if rm -rf node_modules 2>/dev/null; then
            echo "Successfully removed node_modules"
        else
            echo "ERROR: Could not remove node_modules folder"
            echo "This is likely due to file locks or permissions."
            echo ""
            echo "Try:"
            echo "  1. Close all programs (IDE, file explorer, etc.)"
            echo "  2. Run: sudo rm -rf node_modules (if permission issue)"
            echo "  3. Check file permissions: ls -la"
            echo "  4. If on WSL with OneDrive: Exclude node_modules from sync"
            exit 1
        fi
    fi
    
    echo ""
    echo "Installing dependencies fresh..."
    if ! npm install --prefer-offline --no-audit; then
        echo "ERROR: npm install failed"
        echo "Try running with sudo or check file permissions"
        exit 1
    fi
    echo ""
    echo "Dependencies installed successfully!"
else
    echo "Skipping full removal."
fi

echo ""
echo "========================================"
echo "Fix complete!"
echo "========================================"
