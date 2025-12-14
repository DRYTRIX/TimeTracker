# CSRF Cookie Fix for Remote IP Access

## Problem Summary

✅ **Works:** Accessing via `http://localhost:8080` - CSRF cookies created correctly  
❌ **Fails:** Accessing via `http://192.168.1.100:8080` - CSRF cookies NOT created

## Root Cause

The `WTF_CSRF_SSL_STRICT=true` setting (default) blocks cookie creation for HTTP connections to non-localhost addresses. This is a security feature that prevents CSRF tokens from being sent over insecure connections.

## Quick Fix

### Option 1: Automated Script (Recommended)

**Linux/Mac:**
```bash
bash scripts/fix_csrf_ip_access.sh
```

**Windows:**
```cmd
scripts\fix_csrf_ip_access.bat
```

The script will:
1. Update your `.env` file with correct settings
2. Restart the application
3. Verify the configuration

### Option 2: Manual Configuration

Edit your `.env` file and add/update:

```bash
WTF_CSRF_SSL_STRICT=false
SESSION_COOKIE_SECURE=false
CSRF_COOKIE_SECURE=false
```

Then restart:
```bash
docker-compose restart app
```

## What These Settings Do

| Setting | Value | Purpose |
|---------|-------|---------|
| `WTF_CSRF_SSL_STRICT` | `false` | Allows CSRF tokens over HTTP (needed for IP access) |
| `SESSION_COOKIE_SECURE` | `false` | Allows session cookies over HTTP |
| `CSRF_COOKIE_SECURE` | `false` | Allows CSRF cookies over HTTP |

## Verification

### 1. Check Environment Variables
```bash
docker-compose exec app env | grep -E "(WTF_CSRF|SESSION_COOKIE|CSRF_COOKIE)"
```

Expected output:
```
WTF_CSRF_SSL_STRICT=false
SESSION_COOKIE_SECURE=false
CSRF_COOKIE_SECURE=false
```

### 2. Test Cookie Creation

1. Open your browser
2. Navigate to `http://YOUR_IP:8080`
3. Open DevTools (F12)
4. Go to **Application** → **Cookies**
5. Verify these cookies exist:
   - `session` - Your session cookie
   - `XSRF-TOKEN` - The CSRF token

### 3. Test CSRF Endpoint

```bash
# Via localhost (should work)
curl -v http://localhost:8080/auth/csrf-token

# Via IP (should now also work)
curl -v http://192.168.1.100:8080/auth/csrf-token
```

Look for `Set-Cookie` headers in both responses.

## Security Considerations

### ⚠️ Important Security Notes

**These settings are suitable for:**
- ✅ Development environments
- ✅ Testing on local networks
- ✅ Private/trusted networks (VPN, home network)

**NOT suitable for:**
- ❌ Public internet access without HTTPS
- ❌ Production environments with sensitive data
- ❌ Untrusted networks

### Production Configuration

For production deployments, always use HTTPS and set:

```bash
WTF_CSRF_SSL_STRICT=true
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
```

## Alternative Solutions

### Solution 1: Use a Domain Name

Add to your hosts file instead of using IP:

**Linux/Mac** (`/etc/hosts`):
```
192.168.1.100 timetracker.local
```

**Windows** (`C:\Windows\System32\drivers\etc\hosts`):
```
192.168.1.100 timetracker.local
```

Then access via: `http://timetracker.local:8080`

### Solution 2: Set Up HTTPS

For production-like testing with HTTPS:

1. Generate self-signed certificate:
```bash
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout key.pem -out cert.pem -days 365 \
  -subj "/CN=192.168.1.100"
```

2. Update docker-compose to use HTTPS
3. Set all security flags to `true`

## Troubleshooting

### Still not working?

1. **Verify settings are loaded:**
   ```bash
   docker-compose exec app env | grep WTF_CSRF_SSL_STRICT
   ```

2. **Check logs:**
   ```bash
   docker-compose logs app | grep -i csrf
   ```

3. **Try a fresh restart:**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

4. **Clear browser cookies:**
   - DevTools → Application → Cookies → Delete all for this site

5. **Test in incognito/private window:**
   - Rules out browser extension issues

### Different browsers behave differently?

- Chrome/Edge: Usually most permissive
- Firefox: Stricter cookie policies
- Safari: Strictest, especially with tracking prevention

Try disabling enhanced tracking protection or privacy features temporarily for testing.

## Related Documentation

- **Detailed Guide:** [docs/CSRF_IP_ACCESS_GUIDE.md](docs/CSRF_IP_ACCESS_GUIDE.md)
- **General CSRF Troubleshooting:** [CSRF_TROUBLESHOOTING.md](CSRF_TROUBLESHOOTING.md)
- **CSRF Configuration:** [docs/CSRF_CONFIGURATION.md](docs/CSRF_CONFIGURATION.md)

## Summary

**The Fix:** Set `WTF_CSRF_SSL_STRICT=false` for HTTP access via IP addresses.

**Why It Works:** This allows Flask-WTF to create and validate CSRF cookies over HTTP connections to non-localhost addresses.

**When to Use:** Development, testing, and trusted private networks only. Always use HTTPS with strict settings in production.

---

**Quick Command Reference:**

```bash
# Apply fix (automated)
bash scripts/fix_csrf_ip_access.sh

# Verify configuration
docker-compose exec app env | grep -E "WTF_CSRF|SESSION_COOKIE|CSRF_COOKIE"

# Restart application
docker-compose restart app

# Check logs
docker-compose logs app | tail -50
```

---

**Last Updated:** October 2024  
**Applies To:** TimeTracker v1.0+

