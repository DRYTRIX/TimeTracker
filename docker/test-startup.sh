#!/bin/bash
echo "=== Testing Startup Script ==="

echo "Current working directory: $(pwd)"
echo "Current user: $(whoami)"
echo "Current user ID: $(id)"

echo "Checking if startup script exists..."
if [ -f "/app/docker/start.sh" ]; then
    echo "✓ Startup script exists at /app/docker/start.sh"
    echo "File permissions: $(ls -la /app/docker/start.sh)"
    echo "File owner: $(stat -c '%U:%G' /app/docker/start.sh)"

    echo "Testing if script is executable..."
    if [ -x "/app/docker/start.sh" ]; then
        echo "✓ Startup script is executable"
        echo "Script first few lines:"
        head -5 /app/docker/start.sh
    else
        echo "✗ Startup script is NOT executable"
    fi
else
    echo "✗ Startup script does NOT exist at /app/docker/start.sh"
    echo "Contents of /app/docker/:"
    ls -la /app/docker/ || echo "Directory /app/docker/ does not exist"
fi

echo "Checking /app directory structure..."
echo "Contents of /app:"
ls -la /app/ || echo "Directory /app/ does not exist"

echo "=== Test Complete ==="
