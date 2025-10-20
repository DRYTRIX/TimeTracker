# 🔒 HTTPS Setup for TimeTracker

## Quick Start with mkcert

### 1. Install mkcert

**Windows:**
```powershell
choco install mkcert
```

**macOS:**
```bash
brew install mkcert
```

**Linux:**
```bash
# See HTTPS_MKCERT_GUIDE.md for detailed instructions
```

### 2. Run Setup Script

**Windows:**
```cmd
setup-https-mkcert.bat
```

**Linux/Mac:**
```bash
bash setup-https-mkcert.sh
```

### 3. Start with HTTPS

```bash
docker-compose -f docker-compose.yml -f docker-compose.https.yml up -d
```

### 4. Access Your App

```
https://localhost
https://192.168.1.100  (your actual IP)
```

**✅ No certificate warnings!**
**✅ Works with IP addresses!**
**✅ Secure HTTPS!**

---

## What the Script Does

1. ✅ Installs local Certificate Authority (trusted by your browser)
2. ✅ Generates SSL certificates for localhost + your IP
3. ✅ Creates nginx reverse proxy configuration
4. ✅ Creates docker-compose.https.yml
5. ✅ Updates .env with secure HTTPS settings:
   - `WTF_CSRF_SSL_STRICT=true`
   - `SESSION_COOKIE_SECURE=true`
   - `CSRF_COOKIE_SECURE=true`

---

## Benefits

### Solves CSRF Cookie Issues
- ✅ CSRF cookies work correctly with IP addresses
- ✅ Strict security settings enabled
- ✅ No more "CSRF token missing or invalid" errors

### Secure Communication
- ✅ All traffic encrypted
- ✅ Trusted certificates (no warnings)
- ✅ Modern TLS 1.2/1.3

### Easy Management
- ✅ One command setup
- ✅ Valid for 10 years
- ✅ No renewal needed

---

## Access from Other Devices

To access from your phone, tablet, or other computers without warnings:

1. **Find CA location:**
   ```bash
   mkcert -CAROOT
   ```

2. **Copy `rootCA.pem` to device**

3. **Install certificate on device:**
   - iOS: Settings → Profile → Install
   - Android: Settings → Security → Install certificate
   - See [HTTPS_MKCERT_GUIDE.md](HTTPS_MKCERT_GUIDE.md) for details

4. **Access from device:**
   ```
   https://192.168.1.100
   ```

---

## File Structure

After running the setup:

```
TimeTracker/
├── nginx/
│   ├── conf.d/
│   │   └── https.conf          # nginx HTTPS config
│   └── ssl/
│       ├── cert.pem            # SSL certificate (gitignored)
│       └── key.pem             # Private key (gitignored)
├── docker-compose.yml          # Base configuration
├── docker-compose.https.yml    # HTTPS override (auto-generated)
├── setup-https-mkcert.sh      # Linux/Mac setup script
├── setup-https-mkcert.bat     # Windows setup script
└── .env                        # Updated with HTTPS settings
```

---

## Verification

### Check Certificate
1. Navigate to `https://localhost`
2. Click padlock icon in browser
3. View certificate → Should show "mkcert" with no warnings

### Check Cookies
1. Open DevTools (F12) → Application → Cookies
2. Verify `session` and `XSRF-TOKEN` cookies have `Secure` flag

### Test Application
1. Login
2. Create a project
3. Log time
4. Should work without any CSRF errors ✅

---

## Stopping HTTPS

To return to HTTP:

```bash
# Stop HTTPS setup
docker-compose -f docker-compose.yml -f docker-compose.https.yml down

# Start normally
docker-compose up -d
```

---

## Troubleshooting

### Certificate Warning Appears

```bash
# Reinstall CA
mkcert -install

# Restart browser completely
```

### nginx Won't Start

```bash
# Check if port is in use
netstat -ano | findstr :443     # Windows
lsof -i :443                    # Linux/Mac

# Check logs
docker-compose logs nginx
```

### IP Address Not Working

```bash
# Regenerate with correct IP
mkcert -key-file nginx/ssl/key.pem -cert-file nginx/ssl/cert.pem \
  localhost 127.0.0.1 ::1 YOUR_ACTUAL_IP *.local

# Restart
docker-compose restart nginx
```

---

## Complete Documentation

For detailed instructions, see:
- **[HTTPS_MKCERT_GUIDE.md](HTTPS_MKCERT_GUIDE.md)** - Complete mkcert guide
- **[CSRF_IP_ACCESS_FIX.md](CSRF_IP_ACCESS_FIX.md)** - CSRF troubleshooting

---

## Summary

**One command to HTTPS:**
```bash
bash setup-https-mkcert.sh
docker-compose -f docker-compose.yml -f docker-compose.https.yml up -d
```

**Result:**
✅ Secure HTTPS  
✅ No certificate warnings  
✅ Works with IP addresses  
✅ CSRF cookies work perfectly  
✅ Production-grade security settings  

**Enjoy secure TimeTracker! 🔒**

