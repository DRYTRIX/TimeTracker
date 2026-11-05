#!/bin/bash

# Test Docker Network Connectivity
# This script helps debug Docker network issues

echo "=== Docker Network Connectivity Test ==="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running"
    exit 1
fi

# Get Docker host IP
echo "Docker Host Information:"
if command -v docker-machine &> /dev/null; then
    DOCKER_HOST_IP=$(docker-machine ip default 2>/dev/null || echo "localhost")
else
    DOCKER_HOST_IP="localhost"
fi
echo "  - Docker Host IP: $DOCKER_HOST_IP"

# Check running containers
echo -e "\nRunning Containers:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Test port 8082 (was used for license server)
echo -e "\nTesting Port 8082:"
if nc -z localhost 8082 2>/dev/null; then
    echo "  ✓ Port 8082 is open on localhost"
else
    echo "  ✗ Port 8082 is not open on localhost"
fi

# Test from host to host.docker.internal
echo -e "\nTesting host.docker.internal from host:"
if ping -c 1 host.docker.internal >/dev/null 2>&1; then
    echo "  ✓ Can reach host.docker.internal from host"
    HOST_DOCKER_IP=$(ping -c 1 host.docker.internal | grep "PING" | sed 's/.*(\([^)]*\)).*/\1/')
    echo "  - Resolved to IP: $HOST_DOCKER_IP"
else
    echo "  ✗ Cannot reach host.docker.internal from host"
fi

# Test network connectivity from within a container
echo -e "\nTesting network from within container:"
if docker ps | grep -q timetracker-app; then
    echo "  - Testing from timetracker-app container:"
    docker exec timetracker-app ping -c 1 host.docker.internal >/dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "    ✓ Container can reach host.docker.internal"
    else
        echo "    ✗ Container cannot reach host.docker.internal"
    fi

    # Get container IP
    CONTAINER_IP=$(docker exec timetracker-app hostname -I | awk '{print $1}')
    echo "    - Container IP: $CONTAINER_IP"
else
    echo "  - timetracker-app container not running"
fi

# Show Docker network information
echo -e "\nDocker Networks:"
docker network ls

# Show detailed network info for default bridge
echo -e "\nDefault Bridge Network Details:"
docker network inspect bridge 2>/dev/null | grep -A 10 -B 5 "Containers"

echo -e "\n=== End Network Test ==="
echo ""
echo "If you're having connectivity issues:"
echo "1. Verify Docker network configuration"
echo "2. Consider using Docker service names instead of host.docker.internal"
