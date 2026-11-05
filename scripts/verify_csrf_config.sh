#!/bin/bash
# CSRF Configuration Verification Script
# This script verifies that CSRF tokens are properly configured in a Docker deployment

set -e

echo "=================================================="
echo "  TimeTracker CSRF Configuration Verification"
echo "=================================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ "$1" == "OK" ]; then
        echo -e "${GREEN}✓${NC} $2"
    elif [ "$1" == "WARNING" ]; then
        echo -e "${YELLOW}⚠${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
    fi
}

# Check if container is running
CONTAINER_NAME=${1:-timetracker-app}
echo "Checking container: $CONTAINER_NAME"
echo ""

if ! docker ps | grep -q "$CONTAINER_NAME"; then
    print_status "ERROR" "Container '$CONTAINER_NAME' is not running"
    echo ""
    echo "Available containers:"
    docker ps --format "table {{.Names}}\t{{.Status}}"
    exit 1
fi

print_status "OK" "Container is running"
echo ""

# Check environment variables
echo "1. Checking environment variables..."
echo "-----------------------------------"

SECRET_KEY=$(docker exec "$CONTAINER_NAME" env | grep "^SECRET_KEY=" | cut -d= -f2)
CSRF_ENABLED=$(docker exec "$CONTAINER_NAME" env | grep "^WTF_CSRF_ENABLED=" | cut -d= -f2 || echo "not set")
CSRF_TIMEOUT=$(docker exec "$CONTAINER_NAME" env | grep "^WTF_CSRF_TIME_LIMIT=" | cut -d= -f2 || echo "not set")
FLASK_ENV=$(docker exec "$CONTAINER_NAME" env | grep "^FLASK_ENV=" | cut -d= -f2 || echo "production")

if [ -z "$SECRET_KEY" ]; then
    print_status "ERROR" "SECRET_KEY is not set!"
elif [ "$SECRET_KEY" == "your-secret-key-change-this" ]; then
    print_status "ERROR" "SECRET_KEY is using default value - INSECURE!"
    echo "   Generate a secure key with: python -c \"import secrets; print(secrets.token_hex(32))\""
elif [ "$SECRET_KEY" == "dev-secret-key-change-in-production" ]; then
    print_status "ERROR" "SECRET_KEY is using development default - INSECURE!"
elif [ ${#SECRET_KEY} -lt 32 ]; then
    print_status "WARNING" "SECRET_KEY is short (${#SECRET_KEY} chars). Recommend 64+ chars"
else
    print_status "OK" "SECRET_KEY is set and appears secure (${#SECRET_KEY} chars)"
fi

if [ "$CSRF_ENABLED" == "true" ] || [ "$CSRF_ENABLED" == "not set" ]; then
    print_status "OK" "CSRF protection is enabled"
elif [ "$CSRF_ENABLED" == "false" ]; then
    if [ "$FLASK_ENV" == "development" ]; then
        print_status "WARNING" "CSRF protection is disabled (OK for development)"
    else
        print_status "ERROR" "CSRF protection is disabled in production!"
    fi
else
    print_status "WARNING" "CSRF_ENABLED has unexpected value: $CSRF_ENABLED"
fi

if [ "$CSRF_TIMEOUT" == "not set" ]; then
    print_status "OK" "CSRF timeout using default (3600s / 1 hour)"
else
    print_status "OK" "CSRF timeout set to ${CSRF_TIMEOUT}s ($(($CSRF_TIMEOUT / 60)) minutes)"
fi

echo ""

# Check application logs for CSRF-related issues
echo "2. Checking application logs..."
echo "-------------------------------"

CSRF_ERRORS=$(docker logs "$CONTAINER_NAME" 2>&1 | grep -i "csrf" | grep -i "error\|fail\|invalid" | tail -5)

if [ -n "$CSRF_ERRORS" ]; then
    print_status "WARNING" "Found CSRF-related errors in logs:"
    echo "$CSRF_ERRORS" | while IFS= read -r line; do
        echo "   $line"
    done
else
    print_status "OK" "No CSRF errors found in logs"
fi

echo ""

# Check if app is responding
echo "3. Checking application health..."
echo "---------------------------------"

PORT=$(docker port "$CONTAINER_NAME" 8080 2>/dev/null | cut -d: -f2)
if [ -z "$PORT" ]; then
    PORT="8080"
fi

if curl -s -f "http://localhost:$PORT/_health" > /dev/null 2>&1; then
    print_status "OK" "Application health check passed"
else
    print_status "WARNING" "Health check endpoint not responding"
fi

# Try to fetch login page and check for CSRF token
LOGIN_PAGE=$(curl -s "http://localhost:$PORT/login" || echo "")
if echo "$LOGIN_PAGE" | grep -q "csrf_token"; then
    print_status "OK" "CSRF token found in login page"
else
    if [ "$CSRF_ENABLED" == "false" ]; then
        print_status "OK" "No CSRF token in login page (CSRF is disabled)"
    else
        print_status "WARNING" "No CSRF token found in login page (might be disabled or error)"
    fi
fi

echo ""

# Configuration summary
echo "4. Configuration Summary"
echo "------------------------"
echo "Container:       $CONTAINER_NAME"
echo "Flask Environment: $FLASK_ENV"
echo "SECRET_KEY:      ${SECRET_KEY:0:10}... (${#SECRET_KEY} chars)"
echo "CSRF Enabled:    $CSRF_ENABLED"
echo "CSRF Timeout:    $CSRF_TIMEOUT seconds"
echo ""

# Recommendations
echo "5. Recommendations"
echo "------------------"

HAS_ISSUES=0

if [ "$SECRET_KEY" == "your-secret-key-change-this" ] || [ "$SECRET_KEY" == "dev-secret-key-change-in-production" ]; then
    echo "⚠️  Generate a secure SECRET_KEY:"
    echo "   python -c \"import secrets; print(secrets.token_hex(32))\""
    echo "   Then set it in your .env file or docker-compose.yml"
    HAS_ISSUES=1
fi

if [ "$FLASK_ENV" != "development" ] && [ "$CSRF_ENABLED" == "false" ]; then
    echo "⚠️  Enable CSRF protection in production:"
    echo "   Set WTF_CSRF_ENABLED=true in your environment"
    HAS_ISSUES=1
fi

if [ "$FLASK_ENV" != "development" ] && [ ${#SECRET_KEY} -lt 32 ]; then
    echo "⚠️  Use a longer SECRET_KEY for better security (64+ chars recommended)"
    HAS_ISSUES=1
fi

if [ $HAS_ISSUES -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Configuration looks good!"
fi

echo ""
echo "=================================================="
echo "For detailed documentation, see:"
echo "  docs/CSRF_CONFIGURATION.md"
echo "=================================================="
