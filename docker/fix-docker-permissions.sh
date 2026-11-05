#!/bin/bash
# Fix Docker container permission issues for file uploads
# This script should be run INSIDE your Docker container

echo "=== Fixing Docker Container Permissions ==="

# Get current user info
echo "Current user: $(whoami)"
echo "Current UID: $(id -u)"
echo "Current GID: $(id -g)"
echo "Current working directory: $(pwd)"

# Define the upload directories
UPLOAD_DIRS=(
    "/app/app/static/uploads"
    "/app/app/static/uploads/logos"
    "/app/static/uploads"
    "/app/static/uploads/logos"
)

# Step 1: Create directories with proper permissions
echo -e "\n1. Creating upload directories..."
for dir in "${UPLOAD_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "Creating directory: $dir"
        mkdir -p "$dir"
    else
        echo "Directory exists: $dir"
    fi
done

# Step 2: Set very permissive permissions (777 for testing)
echo -e "\n2. Setting permissive permissions..."
for dir in "${UPLOAD_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "Setting 777 permissions for: $dir"
        chmod -R 777 "$dir"
    fi
done

# Step 3: Try to change ownership to current user
echo -e "\n3. Changing ownership to current user..."
CURRENT_USER=$(whoami)
CURRENT_UID=$(id -u)
CURRENT_GID=$(id -g)

for dir in "${UPLOAD_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "Changing ownership of $dir to $CURRENT_USER:$CURRENT_USER"
        chown -R "$CURRENT_USER:$CURRENT_USER" "$dir" 2>/dev/null || echo "  - chown failed, trying with UID"

        # If chown fails, try with UID
        chown -R "$CURRENT_UID:$CURRENT_GID" "$dir" 2>/dev/null || echo "  - chown with UID also failed"
    fi
done

# Step 4: Test write permissions
echo -e "\n4. Testing write permissions..."
TEST_SUCCESS=true
for dir in "${UPLOAD_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        TEST_FILE="$dir/test_permissions.tmp"
        if echo "test" > "$TEST_FILE" 2>/dev/null; then
            rm -f "$TEST_FILE"
            echo "✓ Write permission test passed for: $dir"
        else
            echo "✗ Write permission test failed for: $dir"
            TEST_SUCCESS=false
        fi
    fi
done

# Step 5: Show current permissions and ownership
echo -e "\n5. Current directory status:"
for dir in "${UPLOAD_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "\nDirectory: $dir"
        ls -la "$dir" | head -5
        echo "Permissions: $(stat -c "%a" "$dir")"
        echo "Owner: $(stat -c "%U:%G" "$dir")"
    fi
done

# Step 6: Alternative approach - try to fix parent directories
echo -e "\n6. Fixing parent directory permissions..."
PARENT_DIRS=("/app/app/static" "/app/static")
for parent_dir in "${PARENT_DIRS[@]}"; do
    if [ -d "$parent_dir" ]; then
        echo "Setting 755 permissions for parent: $parent_dir"
        chmod 755 "$parent_dir"
        chown "$CURRENT_USER:$CURRENT_USER" "$parent_dir" 2>/dev/null || echo "  - chown failed for parent"
    fi
done

# Final test
echo -e "\n7. Final permission test..."
if $TEST_SUCCESS; then
    echo "=== Permission fix completed successfully! ==="
    echo "The application should now be able to upload logo files."
    echo -e "\nTry uploading a logo file now. If it still fails, you may need to:"
    echo "1. Restart the Docker container"
    echo "2. Check Docker volume mount permissions"
    echo "3. Run the container with proper user mapping"
else
    echo "=== Some permission tests failed ==="
    echo -e "\nTrying alternative approach..."

    # Try to run as root if possible
    if [ "$(id -u)" -eq 0 ]; then
        echo "Running as root, setting permissions..."
        for dir in "${UPLOAD_DIRS[@]}"; do
            if [ -d "$dir" ]; then
                chmod -R 777 "$dir"
                chown -R 1000:1000 "$dir" 2>/dev/null || echo "  - chown to 1000:1000 failed"
            fi
        done
    else
        echo "Not running as root. You may need to:"
        echo "1. Run this script as root (sudo)"
        echo "2. Restart the container with proper user mapping"
        echo "3. Check Docker volume permissions"
    fi
fi

echo -e "\n=== Permission fix script completed ==="
