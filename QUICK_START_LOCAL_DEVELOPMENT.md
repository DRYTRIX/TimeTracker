# Quick Start: Local Development with PostHog

## TL;DR - Fastest Way to Test PostHog Locally

Since analytics keys are embedded (not overridable via env vars), here's the quickest way to test PostHog locally:

### Step 1: Get Your Dev Key

1. Go to https://posthog.com
2. Create account / Sign in
3. Create project: "TimeTracker Dev"
4. Copy your **Project API Key** (starts with `phc_`)

### Step 2: Run Setup Script (Windows)

```powershell
# Run the setup script
.\scripts\setup-dev-analytics.bat
```

**Or manually:**

1. **Create local config** (gitignored):
   ```powershell
   # Copy template
   cp app\config\analytics_defaults.py app\config\analytics_defaults_local.py
   ```

2. **Edit `app\config\analytics_defaults_local.py`**:
   ```python
   # Replace placeholders with your dev keys
   POSTHOG_API_KEY_DEFAULT = "phc_YOUR_DEV_KEY_HERE"
   POSTHOG_HOST_DEFAULT = "https://app.posthog.com"
   
   SENTRY_DSN_DEFAULT = ""  # Optional
   SENTRY_TRACES_RATE_DEFAULT = "1.0"
   ```

3. **Update `app\config\__init__.py`**:
   ```python
   """Configuration module for TimeTracker."""
   
   # Try local dev config first
   try:
       from app.config.analytics_defaults_local import get_analytics_config, has_analytics_configured
   except ImportError:
       from app.config.analytics_defaults import get_analytics_config, has_analytics_configured
   
   __all__ = ['get_analytics_config', 'has_analytics_configured']
   ```

4. **Add to `.gitignore`** (if not already):
   ```
   app/config/analytics_defaults_local.py
   app/config/__init__.py.backup
   ```

### Step 3: Run the Application

```powershell
# With Docker
docker-compose up -d

# Or locally (if you have Python setup)
python app.py
```

### Step 4: Enable Telemetry

1. Open http://localhost:5000
2. Complete setup → **Check "Enable telemetry"**
3. Or later: Admin → Telemetry Dashboard → Enable

### Step 5: Test!

Perform actions:
- Login/Logout
- Start/Stop timer
- Create project
- Create task

Check PostHog dashboard - events should appear within seconds!

## Verification

### Check if PostHog is initialized

```powershell
# Docker
docker-compose logs app | Select-String "PostHog"

# Should see: "PostHog product analytics initialized"
```

### Check events locally

```powershell
# View events in local logs
Get-Content logs\app.jsonl -Tail 50 | Select-String "event_type"
```

### Check PostHog Dashboard

1. Go to PostHog dashboard
2. Click "Live Events" or "Events"
3. You should see events streaming in real-time!

## Common Issues

### "No events in PostHog"

**Check 1:** Is telemetry enabled?
```powershell
Get-Content data\installation.json | Select-String "telemetry_enabled"
# Should show: "telemetry_enabled": true
```

**Check 2:** Is PostHog initialized?
```powershell
docker-compose logs app | Select-String "PostHog"
```

**Check 3:** Is the API key correct?
- Verify in PostHog dashboard: Settings → Project API Key

### "Import error" when running app

Make sure you created `analytics_defaults_local.py` and updated `__init__.py`

### Keys visible in git

```powershell
# Check what would be committed
git status
git diff app\config\analytics_defaults.py

# Should NOT show your dev keys
# If it does, revert:
git checkout app\config\analytics_defaults.py
```

## Clean Up

Before committing:

```powershell
# Verify no keys in the main file
git diff app\config\analytics_defaults.py

# Remove local config if needed
rm app\config\analytics_defaults_local.py

# Restore original __init__.py
mv app\config\__init__.py.backup app\config\__init__.py
```

## Full Documentation

See `docs/LOCAL_DEVELOPMENT_WITH_ANALYTICS.md` for:
- Multiple setup options
- Detailed troubleshooting
- Docker build approach
- Best practices

---

**That's it!** You should now see events in your PostHog dashboard. 🎉

