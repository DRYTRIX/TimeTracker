#!/bin/sh
# Auto-generate mkcert certificates in container

set -e

CERT_DIR="/certs"
CERT_FILE="$CERT_DIR/cert.pem"
KEY_FILE="$CERT_DIR/key.pem"
CA_FILE="$CERT_DIR/rootCA.pem"

echo "=========================================="
echo "mkcert Certificate Generator"
echo "=========================================="
echo ""

# Create cert directory
mkdir -p "$CERT_DIR"

# Check if certificates exist
if [ -f "$CERT_FILE" ] && [ -f "$KEY_FILE" ]; then
    echo "✅ Certificates already exist"
    exit 0
fi

echo "🔧 Generating mkcert certificates..."
echo ""

# Install local CA (for container use)
mkcert -install

# Get domains/IPs to include
DOMAINS=${CERT_DOMAINS:-"localhost 127.0.0.1 ::1"}
echo "Generating certificate for: $DOMAINS"
echo ""

# Generate certificates
mkcert -key-file "$KEY_FILE" -cert-file "$CERT_FILE" $DOMAINS

# Copy CA certificate for user to install on host
cp "$(mkcert -CAROOT)/rootCA.pem" "$CA_FILE" 2>/dev/null || true

chmod 644 "$CERT_FILE" "$CA_FILE" 2>/dev/null || true
chmod 600 "$KEY_FILE"

echo ""
echo "✅ mkcert certificates generated!"
echo ""
echo "📋 Next steps:"
echo "   1. The certificates are in: nginx/ssl/"
echo "   2. To avoid browser warnings, install rootCA.pem on your host:"
echo ""
echo "      Windows:"
echo "        - Double-click nginx/ssl/rootCA.pem"
echo "        - Install to: Trusted Root Certification Authorities"
echo ""
echo "      macOS:"
echo "        - Double-click nginx/ssl/rootCA.pem"
echo "        - Add to Keychain and mark as trusted"
echo ""
echo "      Linux:"
echo "        sudo cp nginx/ssl/rootCA.pem /usr/local/share/ca-certificates/mkcert.crt"
echo "        sudo update-ca-certificates"
echo ""
echo "   3. Restart your browser"
echo "   4. Access: https://localhost or https://$HOST_IP"
echo ""
echo "=========================================="
