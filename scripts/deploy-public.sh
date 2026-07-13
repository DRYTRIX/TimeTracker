#!/bin/bash

# TimeTracker Public Image Deployment Script
# Deploys using the official GHCR image and docker-compose.nas.yml (app + PostgreSQL)

set -e

COMPOSE_FILE="docker-compose.nas.yml"
IMAGE="ghcr.io/drytrix/timetracker:latest"

echo "🚀 TimeTracker Public Image Deployment"
echo "======================================"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first:"
    echo "   curl -fsSL https://get.docker.com -o get-docker.sh"
    echo "   sudo sh get-docker.sh"
    echo "   sudo usermod -aG docker \$USER"
    exit 1
fi

# Prefer docker compose plugin, fall back to docker-compose
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    echo "❌ Docker Compose is not installed."
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"
echo "📦 Using public image: $IMAGE"

# Ensure compose file exists (download if running outside cloned repo)
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "📥 Downloading $COMPOSE_FILE..."
    curl -fsSL -o "$COMPOSE_FILE" \
        "https://raw.githubusercontent.com/drytrix/TimeTracker/main/$COMPOSE_FILE"
fi

# Create .env with SECRET_KEY if missing
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    if command -v openssl &> /dev/null; then
        SECRET_KEY=$(openssl rand -hex 32)
    else
        echo "❌ openssl is required to generate SECRET_KEY. Install openssl or create .env manually."
        exit 1
    fi
    cat > .env <<EOF
SECRET_KEY=$SECRET_KEY
TZ=Europe/Brussels
CURRENCY=EUR
HTTP_PORT=8080
EOF
    echo "✅ Generated SECRET_KEY in .env"
else
    echo "✅ .env file already exists"
fi

# Pull the latest image
echo "📥 Pulling latest TimeTracker image..."
docker pull "$IMAGE"

# Start the application
echo "🚀 Starting TimeTracker..."
$COMPOSE_CMD -f "$COMPOSE_FILE" up -d

# Wait for application to start
echo "⏳ Waiting for application to start (migrations may take 1–2 minutes)..."
for i in $(seq 1 24); do
    if curl -f -s http://localhost:8080/_health > /dev/null 2>&1; then
        break
    fi
    sleep 5
done

if curl -f -s http://localhost:8080/_health > /dev/null 2>&1; then
    echo "✅ TimeTracker is running successfully!"
    echo ""
    echo "🌐 Access the application at:"
    echo "   http://localhost:8080"
    if command -v hostname &> /dev/null; then
        echo "   http://$(hostname -I 2>/dev/null | awk '{print $1}'):8080"
    fi
    echo ""
    echo "🔧 Useful commands:"
    echo "   View logs: $COMPOSE_CMD -f $COMPOSE_FILE logs -f"
    echo "   Stop app:  $COMPOSE_CMD -f $COMPOSE_FILE down"
    echo "   Update:    docker pull $IMAGE && $COMPOSE_CMD -f $COMPOSE_FILE up -d"
else
    echo "❌ Application not healthy yet. Check logs:"
    echo "   $COMPOSE_CMD -f $COMPOSE_FILE logs"
    exit 1
fi

echo ""
echo "🎉 Deployment complete!"
