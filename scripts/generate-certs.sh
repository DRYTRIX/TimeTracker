#!/bin/sh
# Auto-generate SSL certificates for HTTPS
# This script runs in an init container at startup

set -e

CERT_DIR="/certs"
CERT_FILE="$CERT_DIR/cert.pem"
KEY_FILE="$CERT_DIR/key.pem"

echo "=========================================="
echo "SSL Certificate Generator"
echo "=========================================="
echo ""

# Create cert directory if it doesn't exist
mkdir -p "$CERT_DIR"

# Check if certificates already exist
if [ -f "$CERT_FILE" ] && [ -f "$KEY_FILE" ]; then
    echo "✅ Certificates already exist, skipping generation"
    
    # Check if they're about to expire (less than 30 days)
    if command -v openssl >/dev/null 2>&1; then
        EXPIRY=$(openssl x509 -enddate -noout -in "$CERT_FILE" 2>/dev/null | cut -d= -f2)
        if [ -n "$EXPIRY" ]; then
            echo "📅 Certificate expires: $EXPIRY"
        fi
    fi
    exit 0
fi

echo "🔧 Generating new SSL certificates..."
echo ""

# Install openssl if not present
if ! command -v openssl >/dev/null 2>&1; then
    echo "Installing OpenSSL..."
    if command -v apk >/dev/null 2>&1; then
        apk add --no-cache openssl
    elif command -v apt-get >/dev/null 2>&1; then
        apt-get update && apt-get install -y --no-install-recommends openssl && rm -rf /var/lib/apt/lists/*
    else
        echo "⚠️ Could not detect package manager to install openssl. Please install it manually."
        exit 1
    fi
fi

# Detect IP address (try to get container host IP)
HOST_IP=${HOST_IP:-"192.168.1.100"}
echo "Using IP address: $HOST_IP"

# Create OpenSSL config for SAN (Subject Alternative Names)
cat > /tmp/openssl.cnf << EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
x509_extensions = v3_req
distinguished_name = dn

[dn]
C = US
ST = State
L = City
O = TimeTracker
OU = Development
CN = localhost

[v3_req]
subjectAltName = @alt_names
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth

[alt_names]
DNS.1 = localhost
DNS.2 = *.local
DNS.3 = timetracker.local
IP.1 = 127.0.0.1
IP.2 = ::1
IP.3 = ${HOST_IP}
EOF

# Generate self-signed certificate valid for 10 years
echo "Generating certificate..."
openssl req -x509 \
    -newkey rsa:2048 \
    -nodes \
    -keyout "$KEY_FILE" \
    -out "$CERT_FILE" \
    -days 3650 \
    -config /tmp/openssl.cnf

# Set proper permissions
chmod 644 "$CERT_FILE"
chmod 600 "$KEY_FILE"

echo ""
echo "✅ Certificates generated successfully!"
echo ""
echo "Certificate details:"
openssl x509 -in "$CERT_FILE" -noout -subject -dates 2>/dev/null || true
echo ""
echo "📝 Note: These are self-signed certificates."
echo "   Browsers will show a warning on first access."
echo "   Click 'Advanced' → 'Proceed' to accept."
echo ""
echo "For trusted certificates (no warnings), use mkcert:"
echo "   bash setup-https-mkcert.sh"
echo ""
echo "=========================================="

