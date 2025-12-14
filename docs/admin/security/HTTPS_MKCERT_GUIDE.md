# HTTPS Setup with mkcert - Complete Guide

## 🎯 What is mkcert?

mkcert is a simple tool for making locally-trusted development certificates. It requires **no configuration** and creates certificates that work with:
- ✅ localhost
- ✅ IP addresses (192.168.1.100)
- ✅ Custom domains (timetracker.local)
- ✅ **NO browser warnings!**

Perfect for development and local network deployment.

---

## 📦 Installation

### Windows

**Option 1: Chocolatey**
```powershell
choco install mkcert
```

**Option 2: Scoop**
```powershell
scoop bucket add extras
scoop install mkcert
```

### macOS

```bash
brew install mkcert
```

### Linux

**Ubuntu/Debian:**
```bash
sudo apt install libnss3-tools
curl -JLO "https://dl.filippo.io/mkcert/latest?for=linux/amd64"
chmod +x mkcert-v*-linux-amd64
sudo mv mkcert-v*-linux-amd64 /usr/local/bin/mkcert
```

**Arch Linux:**
```bash
sudo pacman -S mkcert
```

---

## 🚀 Quick Setup

### Automated Setup (Recommended)

**Windows:**
```cmd
setup-https-mkcert.bat
```

**Linux/Mac:**
```bash
bash setup-https-mkcert.sh
```

This will:
1. Install local Certificate Authority (CA)
2. Generate certificates for localhost + your IP
3. Create nginx configuration
4. Create docker-compose.https.yml
5. Update .env with secure settings

### Start with HTTPS

```bash
docker-compose -f docker-compose.yml -f docker-compose.https.yml up -d
```

### Access Your Application

```
https://localhost
https://192.168.1.100  (your IP)
https://timetracker.local
```

**No certificate warnings! 🎉**

---

## 🔧 Manual Setup

If you prefer to do it manually:

### Step 1: Install CA

```bash
mkcert -install
```

This installs a local Certificate Authority on your system that browsers will trust.

### Step 2: Generate Certificates

```bash
# Create directories
mkdir -p nginx/ssl

# Generate certs (replace 192.168.1.100 with your IP)
mkcert -key-file nginx/ssl/key.pem \
       -cert-file nginx/ssl/cert.pem \
       localhost 127.0.0.1 ::1 192.168.1.100 *.local
```

**Windows PowerShell:**
```powershell
mkdir nginx\ssl -Force
mkcert -key-file nginx\ssl\key.pem -cert-file nginx\ssl\cert.pem localhost 127.0.0.1 ::1 192.168.1.100 *.local
```

### Step 3: Create nginx Configuration

Create `nginx/conf.d/https.conf`:

```nginx
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
```

### Step 4: Create docker-compose.https.yml

```yaml
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
    ports: []  # nginx handles ports
    environment:
      - WTF_CSRF_SSL_STRICT=true
      - SESSION_COOKIE_SECURE=true
      - CSRF_COOKIE_SECURE=true
```

### Step 5: Update .env

```bash
WTF_CSRF_SSL_STRICT=true
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
```

### Step 6: Start Services

```bash
docker-compose -f docker-compose.yml -f docker-compose.https.yml up -d
```

---

## 🌐 Access from Other Devices

To access from phones, tablets, or other computers on your network **without certificate warnings**:

### Step 1: Find Your CA Location

```bash
mkcert -CAROOT
```

This shows the directory containing `rootCA.pem`

**Example output:**
```
/Users/username/Library/Application Support/mkcert
C:\Users\username\AppData\Local\mkcert
```

### Step 2: Copy rootCA.pem to Device

Transfer the `rootCA.pem` file to your device via:
- USB drive
- Network share
- Email
- Cloud storage

### Step 3: Install CA on Device

**iOS/iPadOS:**
1. Open `rootCA.pem` file
2. Install profile
3. Settings → General → About → Certificate Trust Settings
4. Enable the certificate

**Android:**
1. Settings → Security → Encryption & credentials
2. Install certificate from storage
3. Select `rootCA.pem`

**Windows:**
1. Double-click `rootCA.pem`
2. Install Certificate
3. Store: Local Machine → Trusted Root Certification Authorities

**macOS:**
1. Double-click `rootCA.pem`
2. Add to Keychain
3. Trust for SSL

**Linux:**
```bash
sudo cp rootCA.pem /usr/local/share/ca-certificates/mkcert-rootCA.crt
sudo update-ca-certificates
```

### Step 4: Access from Device

```
https://192.168.1.100
```

✅ **No certificate warning!**

---

## 🔍 Verification

### Check Certificate in Browser

1. Navigate to `https://localhost`
2. Click the padlock icon
3. View certificate details
4. Should show:
   - ✅ Issued by: mkcert
   - ✅ Valid for: localhost, 127.0.0.1, your IP
   - ✅ No warnings

### Test HTTPS Redirect

```bash
# Should redirect to HTTPS
curl -I http://localhost

# Should show 301 redirect
```

### Verify nginx

```bash
# Check nginx is running
docker-compose ps nginx

# Check nginx logs
docker-compose logs nginx
```

### Test Application

1. Access via HTTPS
2. Open DevTools (F12) → Application → Cookies
3. Verify cookies have `Secure` flag
4. Test form submissions (login, create project)
5. Should work without CSRF errors

---

## 🛠️ Troubleshooting

### Certificate Warning Still Appears

**Cause:** CA not installed or browser not restarted

**Solution:**
```bash
# Reinstall CA
mkcert -install

# Restart browser completely (close all windows)

# Clear browser cache and cookies
```

### "NET::ERR_CERT_AUTHORITY_INVALID"

**Cause:** Browser doesn't trust the CA

**Solution:**
1. Check CA is installed: `mkcert -CAROOT`
2. Reinstall: `mkcert -install`
3. On Linux, may need `libnss3-tools`
4. Restart browser

### nginx Won't Start

**Cause:** Port 80 or 443 already in use

**Check:**
```bash
# Windows
netstat -ano | findstr :443

# Linux/Mac
lsof -i :443
```

**Solution:**
```bash
# Stop conflicting service or change ports in docker-compose.https.yml
ports:
  - "8080:80"
  - "8443:443"
```

### Certificate Not Valid for IP Address

**Cause:** IP not included when generating cert

**Solution:**
```bash
# Regenerate with your IP
mkcert -key-file nginx/ssl/key.pem \
       -cert-file nginx/ssl/cert.pem \
       localhost 127.0.0.1 ::1 YOUR_IP_HERE *.local

# Restart nginx
docker-compose restart nginx
```

### Other Devices Show Warning

**Cause:** CA not installed on device

**Solution:**
- Follow "Access from Other Devices" section above
- Install rootCA.pem on each device
- Restart browser/app on device

---

## 🔄 Certificate Renewal

mkcert certificates are valid for **10 years** by default. No renewal needed for development use!

To check expiration:
```bash
openssl x509 -in nginx/ssl/cert.pem -noout -dates
```

To regenerate:
```bash
# Re-run setup script
bash setup-https-mkcert.sh

# Or manually
mkcert -key-file nginx/ssl/key.pem -cert-file nginx/ssl/cert.pem localhost 127.0.0.1 ::1 YOUR_IP *.local

# Restart nginx
docker-compose restart nginx
```

---

## 🔐 Security Notes

### Development Use Only

mkcert is designed for **development and testing**:
- ✅ Perfect for local development
- ✅ Great for LAN/home network
- ✅ Safe for trusted networks
- ❌ **NOT for production internet-facing apps**

### For Production

Use real certificates:
- Let's Encrypt (free, automated)
- Commercial CA (paid)
- Use Caddy for automatic HTTPS

See production deployment guides for details.

### Best Practices

1. ✅ Keep rootCA.pem secure (anyone with it can create trusted certs)
2. ✅ Don't commit `nginx/ssl/*.pem` to git (add to .gitignore)
3. ✅ Use different certs for each project
4. ✅ Uninstall CA when not needed: `mkcert -uninstall`

---

## 📋 Command Reference

```bash
# Install CA
mkcert -install

# Find CA location
mkcert -CAROOT

# Generate certificate
mkcert -key-file KEY.pem -cert-file CERT.pem DOMAIN1 DOMAIN2

# Uninstall CA
mkcert -uninstall

# Check certificate
openssl x509 -in CERT.pem -text -noout
```

---

## 🎉 Summary

### What You Get

✅ **Local HTTPS with NO warnings**
✅ **Works with IP addresses**
✅ **Trusted by all browsers**
✅ **Valid for 10 years**
✅ **Perfect for development**

### Quick Start

```bash
# Install mkcert
# Windows: choco install mkcert
# Mac: brew install mkcert

# Run setup
bash setup-https-mkcert.sh

# Start with HTTPS
docker-compose -f docker-compose.yml -f docker-compose.https.yml up -d

# Access
https://localhost
https://192.168.1.100
```

**That's it! Enjoy secure HTTPS! 🔒**

