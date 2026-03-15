#!/bin/bash

echo "Starting TimeTracker Local Test Environment with SQLite..."
echo

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "Error: docker-compose is not installed or not in PATH"
    echo "Please install Docker Compose"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "Error: Docker is not running"
    echo "Please start Docker"
    exit 1
fi

echo "Building and starting containers..."
docker-compose -f docker/docker-compose.local-test.yml up --build

echo
echo "Local test environment stopped."
