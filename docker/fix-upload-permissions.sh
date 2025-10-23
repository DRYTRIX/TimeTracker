#!/bin/bash
# Fix script for upload directory permissions
# Run this in your Docker container to resolve file upload permission issues

echo "=== Fixing upload directory permissions ==="

# Define the upload directories that need permissions fixed
UPLOAD_DIRS=(
    "/app/app/static/uploads"
    "/app/app/static/uploads/logos"
    "/app/app/static/uploads/avatars"
    "/app/static/uploads"
    "/app/static/uploads/logos"
    "/app/static/uploads/avatars"
)

# Function to fix directory permissions
fix_directory() {
    local dir="$1"
    if [ -d "$dir" ]; then
        echo "Fixing permissions for: $dir"
        chmod 755 "$dir"
        
        # Test write permissions
        local test_file="$dir/test_permissions.tmp"
        if echo "test" > "$test_file" 2>/dev/null; then
            rm -f "$test_file"
            echo "✓ Write permission test passed for: $dir"
        else
            echo "⚠ Write permission test failed for: $dir"
        fi
    else
        echo "Creating directory: $dir"
        mkdir -p "$dir"
        chmod 755 "$dir"
        echo "✓ Created directory: $dir"
    fi
}

# Fix permissions for all upload directories
for dir in "${UPLOAD_DIRS[@]}"; do
    fix_directory "$dir"
done

# Also fix the parent static directories
STATIC_DIRS=("/app/app/static" "/app/static")
for dir in "${STATIC_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "Fixing permissions for static directory: $dir"
        chmod 755 "$dir"
        echo "✓ Set static directory permissions for: $dir"
    fi
done

echo ""
echo "=== Permission fix completed ==="
echo "The application should now be able to upload logo files."

# Show current permissions
echo ""
echo "Current directory permissions:"
for dir in "${UPLOAD_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        ls -ld "$dir"
    fi
done
