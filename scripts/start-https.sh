#!/bin/bash
# Start TimeTracker with automatic HTTPS
# Automatically generates certificates and starts all services

set -e

echo "=========================================="
echo "TimeTracker HTTPS Startup"
echo "=========================================="
echo ""

# Detect local IP
if [[ "$OSTYPE" == "darwin"* ]]; then
    LOCAL_IP=$(ipconfig getifaddr en0 || ipconfig getifaddr en1 || echo "192.168.1.100")
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    LOCAL_IP=$(hostname -I | awk '{print $1}' || echo "192.168.1.100")
else
    LOCAL_IP="192.168.1.100"
fi

echo "🌐 Local IP detected: $LOCAL_IP"
echo ""

# Create nginx config if it doesn't exist
if [ ! -f nginx/conf.d/https.conf ]; then
    echo "📝 Creating nginx HTTPS configuration..."
    mkdir -p nginx/conf.d
    
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
    
    echo "✅ nginx configuration created"
    echo ""
fi

# Update .env with HTTPS settings if it exists
if [ -f .env ]; then
    echo "🔧 Updating .env with HTTPS settings..."
    
    # Backup .env
    cp .env .env.backup 2>/dev/null || true
    
    # Update settings
    sed -i.bak 's/^WTF_CSRF_SSL_STRICT=.*/WTF_CSRF_SSL_STRICT=true/' .env 2>/dev/null || echo "WTF_CSRF_SSL_STRICT=true" >> .env
    sed -i.bak 's/^SESSION_COOKIE_SECURE=.*/SESSION_COOKIE_SECURE=true/' .env 2>/dev/null || echo "SESSION_COOKIE_SECURE=true" >> .env
    sed -i.bak 's/^CSRF_COOKIE_SECURE=.*/CSRF_COOKIE_SECURE=true/' .env 2>/dev/null || echo "CSRF_COOKIE_SECURE=true" >> .env
    
    # Clean up
    rm -f .env.bak
    
    echo "✅ .env updated"
    echo ""
fi

# Export IP for docker-compose
export HOST_IP=$LOCAL_IP

# Choose certificate method
echo "Select certificate method:"
echo "  1) Self-signed (works immediately, shows browser warning)"
echo "  2) mkcert (trusted certificates, requires one-time CA install)"
echo ""
read -p "Choice [1]: " CERT_METHOD
CERT_METHOD=${CERT_METHOD:-1}

echo ""

if [ "$CERT_METHOD" = "2" ]; then
    # Check if mkcert is available
    if command -v mkcert >/dev/null 2>&1; then
        echo "🔐 Using mkcert for trusted certificates..."
        docker-compose -f docker-compose.yml -f docker/docker-compose.https-mkcert.yml up -d
    else
        echo "⚠️  mkcert not found on host. Using self-signed certificates instead."
        echo "   Install mkcert for trusted certificates: brew install mkcert (Mac) or choco install mkcert (Windows)"
        echo ""
        docker-compose -f docker-compose.yml -f docker/docker-compose.https-auto.yml up -d
    fi
else
    echo "🔐 Using self-signed certificates..."
    docker-compose -f docker-compose.yml -f docker/docker-compose.https-auto.yml up -d
fi

echo ""
echo "=========================================="
echo "✅ TimeTracker is starting with HTTPS!"
echo "=========================================="
echo ""
echo "Access your application at:"
echo "  https://localhost"
echo "  https://$LOCAL_IP"
echo ""

if [ "$CERT_METHOD" = "1" ] || ! command -v mkcert >/dev/null 2>&1; then
    echo "⚠️  Browser Warning Expected:"
    echo "   Self-signed certificates will show a security warning."
    echo "   Click 'Advanced' → 'Proceed to localhost (unsafe)' to continue."
    echo ""
    echo "   For no warnings, run: bash setup-https-mkcert.sh"
else
    echo "📋 To avoid browser warnings:"
    echo "   Install the CA certificate from: nginx/ssl/rootCA.pem"
    echo "   See instructions above or in HTTPS_MKCERT_GUIDE.md"
fi

echo ""
echo "View logs:"
echo "  docker-compose logs -f"
echo ""
echo "Stop services:"
echo "  docker-compose down"
echo ""

