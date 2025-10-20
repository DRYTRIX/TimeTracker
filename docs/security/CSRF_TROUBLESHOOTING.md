# CSRF Token Troubleshooting Quick Reference

## 🔴 Problem: Forms fail with "CSRF token missing or invalid"

### Quick Checks (30 seconds)

Run this command to diagnose:
```bash
# Linux/Mac
bash scripts/verify_csrf_config.sh

# Windows
scripts\verify_csrf_config.bat
```

### Common Causes & Solutions

#### ✅ 1. SECRET_KEY Changed or Not Set
**Symptom:** All forms suddenly stopped working after restart

**Check:**
```bash
docker-compose exec app env | grep SECRET_KEY
```

**Solution:**
```bash
# Generate a secure key
python -c "import secrets; print(secrets.token_hex(32))"

# Add to .env file
echo "SECRET_KEY=your-generated-key-here" >> .env

# Restart
docker-compose restart app
```

**Prevention:** Store SECRET_KEY in `.env` file and add to `.gitignore`

---

#### ✅ 2. CSRF Protection Disabled
**Symptom:** No csrf_token field in forms

**Check:**
```bash
docker-compose exec app env | grep WTF_CSRF_ENABLED
```

**Solution:**
```bash
# In .env file
WTF_CSRF_ENABLED=true

# Restart
docker-compose restart app
```

---

#### ✅ 3. Cookies Blocked by Browser
**Symptom:** Works on one browser but not another

**Check:**
- Open browser DevTools → Application → Cookies
- Look for `session` cookie from your domain

**Solution:**
- Enable cookies in browser settings
- Check if browser extensions are blocking cookies
- Try incognito/private mode to test

---

#### ✅ 4. Reverse Proxy Issues
**Symptom:** Works on localhost but fails behind nginx/traefik/apache

**Check nginx config:**
```nginx
proxy_pass http://timetracker:8080;
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;

# IMPORTANT: Don't strip cookies!
proxy_pass_request_headers on;
proxy_cookie_path / /;
```

**Solution:**
- Ensure proxy forwards cookies
- Check `proxy_cookie_domain` and `proxy_cookie_path`
- Verify HOST header is correct

---

#### ✅ 5. Token Expired
**Symptom:** Forms work initially, then fail after some time

**Check:**
```bash
docker-compose exec app env | grep WTF_CSRF_TIME_LIMIT
```

**Solution:**
```bash
# In .env file - increase timeout (in seconds)
WTF_CSRF_TIME_LIMIT=7200  # 2 hours

# Or disable expiration (less secure)
WTF_CSRF_TIME_LIMIT=null

# Restart
docker-compose restart app
```

---

#### ✅ 6. Multiple App Instances with Different SECRET_KEYs
**Symptom:** Intermittent failures, works sometimes but not always

**Check:**
```bash
# Check all containers
docker ps --filter "name=timetracker-app"

# Check each one
docker exec timetracker-app-1 env | grep SECRET_KEY
docker exec timetracker-app-2 env | grep SECRET_KEY
```

**Solution:**
- Ensure ALL instances use the SAME SECRET_KEY
- Use Docker secrets or environment files
- Never let each container generate its own key

---

#### ✅ 7. Clock Skew
**Symptom:** Tokens expire immediately or at wrong times

**Check:**
```bash
docker exec app date
date
```

**Solution:**
```bash
# On host, sync time
sudo ntpdate -s time.nist.gov

# Or install NTP daemon
sudo apt-get install ntp
sudo systemctl start ntp

# Restart container
docker-compose restart app
```

---

#### ✅ 8. Accessing via IP Address (Not Localhost)
**Symptom:** Works on localhost but CSRF cookie not created when accessing via IP (e.g., 192.168.1.100)

**Cause:** `WTF_CSRF_SSL_STRICT=true` blocks cookies on HTTP connections to non-localhost addresses

**Check:**
```bash
docker-compose exec app env | grep WTF_CSRF_SSL_STRICT
```

**Solution:**
```bash
# In .env file
WTF_CSRF_SSL_STRICT=false
SESSION_COOKIE_SECURE=false
CSRF_COOKIE_SECURE=false

# Restart
docker-compose restart app
```

**Note:** Only use these settings for development/testing on trusted networks. Production should use HTTPS with strict settings.

**See:** `docs/CSRF_IP_ACCESS_GUIDE.md` for detailed explanation

---

#### ✅ 9. Development/Testing: Just Disable CSRF
**⚠️ WARNING: Only for local development/testing!**

```bash
# In .env file
WTF_CSRF_ENABLED=false

# Restart
docker-compose restart app
```

**NEVER do this in production!**

---

## 🔍 Diagnostic Commands

### Check Configuration
```bash
# View all CSRF-related env vars
docker-compose exec app env | grep -E "(SECRET_KEY|CSRF|COOKIE)"

# Check app logs for CSRF errors
docker-compose logs app | grep -i csrf

# Test health endpoint
curl -v http://localhost:8080/_health
```

### Check Cookies in Browser
1. Open DevTools (F12)
2. Go to Application → Cookies
3. Look for `session` cookie
4. Check it has proper domain and path
5. Verify it's not marked as expired

### Verify CSRF Token in HTML
1. Open any form page
2. View page source (Ctrl+U)
3. Search for `csrf_token`
4. Should see: `<input type="hidden" name="csrf_token" value="...">`

### Test with curl
```bash
# Get login page and save cookies
curl -c cookies.txt http://localhost:8080/login -o login.html

# Extract CSRF token
TOKEN=$(grep csrf_token login.html | grep -oP 'value="\K[^"]+')

# Try to login with token
curl -b cookies.txt -c cookies.txt \
  -d "username=admin" \
  -d "csrf_token=$TOKEN" \
  http://localhost:8080/login
```

---

## 📋 Checklist: Fresh Deployment

When deploying TimeTracker for the first time:

- [ ] Generate secure SECRET_KEY: `python -c "import secrets; print(secrets.token_hex(32))"`
- [ ] Add SECRET_KEY to `.env` file
- [ ] Verify `WTF_CSRF_ENABLED=true` in production
- [ ] If using HTTPS, set `SESSION_COOKIE_SECURE=true`
- [ ] If behind reverse proxy, configure cookie forwarding
- [ ] Start containers: `docker-compose up -d`
- [ ] Run verification: `bash scripts/verify_csrf_config.sh`
- [ ] Test form submission (try logging in)
- [ ] Check logs: `docker-compose logs app | grep -i csrf`

---

## 🆘 Still Not Working?

### Enable Debug Logging
```bash
# In .env file
LOG_LEVEL=DEBUG

# Restart
docker-compose restart app

# Watch logs
docker-compose logs -f app
```

### Nuclear Option: Fresh Start
```bash
# Stop and remove containers
docker-compose down

# Remove volumes (⚠️ this deletes data!)
docker-compose down -v

# Clean rebuild
docker-compose build --no-cache
docker-compose up -d
```

### Get More Help
1. Check detailed documentation: `docs/CSRF_CONFIGURATION.md`
2. Review original fix: `CSRF_TOKEN_FIX_SUMMARY.md`
3. Check application logs in `logs/timetracker.log`
4. Search existing issues on GitHub
5. Create new issue with:
   - Output of `verify_csrf_config.sh`
   - Relevant logs from `docker-compose logs app`
   - Browser console errors (F12 → Console)
   - Network tab showing failed requests

---

## 💡 Pro Tips

1. **Use `.env` file**: Store SECRET_KEY there, never in docker-compose.yml
2. **Version control**: Add `.env` to `.gitignore`
3. **Documentation**: Keep SECRET_KEY in secure password manager
4. **Monitoring**: Watch for CSRF errors in logs
5. **Testing**: Test after any reverse proxy changes
6. **Backups**: Include SECRET_KEY in backup procedures

---

## 🔗 Related Documentation

- [Detailed CSRF Configuration Guide](docs/CSRF_CONFIGURATION.md)
- [CSRF IP Access Guide](docs/CSRF_IP_ACCESS_GUIDE.md) - **For localhost vs IP address issues**
- [Original CSRF Implementation](CSRF_TOKEN_FIX_SUMMARY.md)
- [Docker Setup Guide](docs/DOCKER_PUBLIC_SETUP.md)
- [Troubleshooting Guide](docs/DOCKER_STARTUP_TROUBLESHOOTING.md)

---

**Last Updated:** October 2025  
**Applies To:** TimeTracker v1.0+

