#!/bin/bash
# Setup HTTPS for TimeTracker using mkcert
# Works with localhost and IP addresses - NO certificate warnings!

set -e

echo "=========================================="
echo "TimeTracker HTTPS Setup with mkcert"
echo "=========================================="
echo ""

# Check if mkcert is installed
if ! command -v mkcert &> /dev/null; then
    echo "❌ mkcert is not installed!"
    echo ""
    echo "Install mkcert:"
    echo "  macOS:   brew install mkcert"
    echo "  Linux:   https://github.com/FiloSottile/mkcert#linux"
    echo "  Windows: choco install mkcert  OR  scoop install mkcert"
    echo ""
    exit 1
fi

echo "✅ mkcert found"
echo ""

# Install local CA
echo "Installing local Certificate Authority..."
mkcert -install
echo "✅ Local CA installed"
echo ""

# Detect local IP
if [[ "$OSTYPE" == "darwin"* ]]; then
    LOCAL_IP=$(ipconfig getifaddr en0 || ipconfig getifaddr en1 || echo "192.168.1.100")
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    LOCAL_IP=$(hostname -I | awk '{print $1}' || echo "192.168.1.100")
else
    LOCAL_IP="192.168.1.100"
fi

echo "Detected local IP: $LOCAL_IP"
echo ""

# Create directories
mkdir -p nginx/ssl nginx/conf.d

# Generate certificates
echo "Generating certificates..."
mkcert -key-file nginx/ssl/key.pem -cert-file nginx/ssl/cert.pem \
    localhost 127.0.0.1 ::1 $LOCAL_IP *.local

echo "✅ Certificates generated"
echo ""

# Create nginx config
cat > nginx/conf.d/https.conf << 'NGINX_EOF'
server {
    listen 80;
    server_name _;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name _;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;

    location / {
        proxy_pass http://app:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
NGINX_EOF

echo "✅ nginx config created"
echo ""

# Create docker-compose override
cat > docker-compose.https.yml << 'COMPOSE_EOF'
services:
  nginx:
    image: nginx:alpine
    container_name: timetracker-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - app
    restart: unless-stopped

  app:
    ports: []
    environment:
      - WTF_CSRF_SSL_STRICT=true
      - SESSION_COOKIE_SECURE=true
      - CSRF_COOKIE_SECURE=true
COMPOSE_EOF

echo "✅ docker-compose.https.yml created"
echo ""

# Update .env if exists
if [ -f .env ]; then
    cp .env .env.backup
    sed -i.bak 's/^WTF_CSRF_SSL_STRICT=.*/WTF_CSRF_SSL_STRICT=true/' .env 2>/dev/null || echo "WTF_CSRF_SSL_STRICT=true" >> .env
    sed -i.bak 's/^SESSION_COOKIE_SECURE=.*/SESSION_COOKIE_SECURE=true/' .env 2>/dev/null || echo "SESSION_COOKIE_SECURE=true" >> .env
    sed -i.bak 's/^CSRF_COOKIE_SECURE=.*/CSRF_COOKIE_SECURE=true/' .env 2>/dev/null || echo "CSRF_COOKIE_SECURE=true" >> .env
    rm -f .env.bak
    echo "✅ .env updated"
else
    echo "⚠️  No .env file - create from env.example"
fi

echo ""
echo "=========================================="
echo "✅ HTTPS Setup Complete!"
echo "=========================================="
echo ""
echo "Start with HTTPS:"
echo "  docker-compose -f docker-compose.yml -f docker-compose.https.yml up -d"
echo ""
echo "Access at:"
echo "  https://localhost"
echo "  https://$LOCAL_IP"
echo ""
echo "For other devices:"
echo "  1. Find CA: mkcert -CAROOT"
echo "  2. Copy rootCA.pem to device"
echo "  3. Import as trusted certificate"
echo ""

