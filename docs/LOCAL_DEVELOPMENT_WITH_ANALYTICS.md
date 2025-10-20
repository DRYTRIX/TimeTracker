# Local Development with Analytics

## Running TimeTracker Locally with PostHog

Since analytics keys are embedded during the build process and cannot be overridden via environment variables, here's how to test PostHog locally during development.

## Option 1: Temporary Local Configuration (Recommended)

### Step 1: Get Your Development Keys

1. **Create a PostHog account** (or use existing):
   - Go to https://posthog.com (or your self-hosted instance)
   - Create a new project called "TimeTracker Dev"
   - Copy your **Project API Key** (starts with `phc_`)

2. **Create a Sentry account** (optional):
   - Go to https://sentry.io
   - Create a new project
   - Copy your **DSN**

### Step 2: Temporarily Edit Local File

Create a local configuration file that won't be committed:

```bash
# Create a local config override (gitignored)
cp app/config/analytics_defaults.py app/config/analytics_defaults_local.py
```

Edit `app/config/analytics_defaults_local.py`:

```python
# Local development keys (DO NOT COMMIT)
POSTHOG_API_KEY_DEFAULT = "phc_your_dev_key_here"
POSTHOG_HOST_DEFAULT = "https://app.posthog.com"

SENTRY_DSN_DEFAULT = "https://your_dev_dsn@sentry.io/project"
SENTRY_TRACES_RATE_DEFAULT = "1.0"  # 100% sampling for dev
```

### Step 3: Update Import (Temporarily)

In `app/config/__init__.py`, temporarily change:

```python
# Temporarily use local config for development
try:
    from app.config.analytics_defaults_local import get_analytics_config, has_analytics_configured
except ImportError:
    from app.config.analytics_defaults import get_analytics_config, has_analytics_configured
```

### Step 4: Add to .gitignore

Ensure your local config is ignored:

```bash
echo "app/config/analytics_defaults_local.py" >> .gitignore
```

### Step 5: Run the Application

```bash
docker-compose up -d
```

Or without Docker:

```bash
# Activate virtual environment
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Run Flask
python app.py
```

### Step 6: Enable Telemetry

1. Access http://localhost:5000
2. Complete setup and **enable telemetry**
3. Or go to Admin → Telemetry Dashboard → Enable

### Step 7: Test Events

Perform actions and check PostHog:
- Login/logout
- Start/stop timer
- Create project
- Create task

Events should appear in your PostHog dashboard within seconds!

## Option 2: Direct File Edit (Quick & Dirty)

For quick testing, directly edit `app/config/analytics_defaults.py`:

```python
# Temporarily replace placeholders (DON'T COMMIT THIS)
POSTHOG_API_KEY_DEFAULT = "phc_your_dev_key_here"  # was: "%%POSTHOG_API_KEY_PLACEHOLDER%%"
```

**⚠️ IMPORTANT:** Revert this before committing!

```bash
# Before committing, revert your changes
git checkout app/config/analytics_defaults.py
```

## Option 3: Use Docker Build with Secrets

Build a local image with your dev keys:

```bash
# Create a local build script
cat > build-dev-local.sh <<'EOF'
#!/bin/bash

# Your dev keys
export POSTHOG_API_KEY="phc_your_dev_key"
export SENTRY_DSN="https://your_dev_dsn@sentry.io/xxx"

# Inject keys into local copy
sed -i "s|%%POSTHOG_API_KEY_PLACEHOLDER%%|${POSTHOG_API_KEY}|g" app/config/analytics_defaults.py
sed -i "s|%%SENTRY_DSN_PLACEHOLDER%%|${SENTRY_DSN}|g" app/config/analytics_defaults.py

# Build image
docker build -t timetracker:dev .

# Revert changes
git checkout app/config/analytics_defaults.py

echo "✅ Built timetracker:dev with your dev keys"
EOF

chmod +x build-dev-local.sh
./build-dev-local.sh
```

Then run:

```bash
docker run -p 5000:5000 timetracker:dev
```

## Option 4: Development Branch Build

Push to a development branch and let GitHub Actions build with dev keys:

1. Add development secrets to GitHub:
   ```
   POSTHOG_API_KEY_DEV
   SENTRY_DSN_DEV
   ```

2. Push to `develop` branch - workflow builds with keys

3. Pull and run:
   ```bash
   docker pull ghcr.io/YOUR_USERNAME/timetracker:develop
   docker run -p 5000:5000 ghcr.io/YOUR_USERNAME/timetracker:develop
   ```

## Verifying It Works

### Check PostHog Dashboard

1. Go to PostHog dashboard
2. Navigate to "Events" or "Live Events"
3. Perform actions in TimeTracker
4. Events should appear immediately:
   - `auth.login`
   - `timer.started`
   - `project.created`
   - etc.

### Check Application Logs

```bash
# Docker
docker-compose logs app | grep PostHog

# Local
tail -f logs/app.jsonl | grep PostHog
```

Should see:
```
PostHog product analytics initialized (host: https://app.posthog.com)
```

### Check Local Event Logs

```bash
# All events logged locally regardless of PostHog
tail -f logs/app.jsonl | grep event_type
```

## Testing Telemetry Toggle

### Enable Telemetry
1. Login as admin
2. Go to http://localhost:5000/admin/telemetry
3. Click "Enable Telemetry"
4. Perform actions
5. Check PostHog for events

### Disable Telemetry
1. Go to http://localhost:5000/admin/telemetry
2. Click "Disable Telemetry"
3. Perform actions
4. No events should appear in PostHog (but still logged locally)

## Best Practices

### For Daily Development

Use **Option 1** (local config file):
- ✅ Keys stay out of git
- ✅ Easy to toggle
- ✅ Revert friendly

### For Testing Official Build Process

Use **Option 3** (Docker build):
- ✅ Simulates production
- ✅ Tests full flow
- ✅ Clean separation

### For Quick Testing

Use **Option 2** (direct edit):
- ✅ Fast
- ⚠️ Easy to accidentally commit
- ⚠️ Need to remember to revert

## Common Issues

### Events Not Appearing in PostHog

**Check 1:** Is telemetry enabled?
```bash
cat data/installation.json | grep telemetry_enabled
# Should show: "telemetry_enabled": true
```

**Check 2:** Is PostHog initialized?
```bash
docker-compose logs app | grep "PostHog product analytics initialized"
```

**Check 3:** Is the API key valid?
- Go to PostHog project settings
- Verify API key is correct
- Check it's not revoked

**Check 4:** Network connectivity
```bash
# From inside Docker container
docker-compose exec app curl -I https://app.posthog.com
# Should return 200 OK
```

### "Module not found" Errors

Make sure you're in the right directory and dependencies are installed:

```bash
# Check location
pwd  # Should be in TimeTracker root

# Install dependencies
pip install -r requirements.txt
```

### Keys Visible in Git

If you accidentally committed keys:

```bash
# Remove from git history (if not pushed)
git reset --soft HEAD~1
git checkout app/config/analytics_defaults.py

# If already pushed, rotate the keys immediately!
# Then force push (careful!)
git push --force
```

## Clean Up

### Before Committing

```bash
# Make sure no dev keys are in the file
git diff app/config/analytics_defaults.py

# Should only show %%PLACEHOLDER%% values
# If you see actual keys, revert:
git checkout app/config/analytics_defaults.py
```

### Remove Local Config

```bash
rm app/config/analytics_defaults_local.py
```

## Summary

**Recommended workflow:**

1. Create `analytics_defaults_local.py` with your dev keys
2. Add to `.gitignore`
3. Modify `__init__.py` to import local version
4. Run application normally
5. Enable telemetry in admin dashboard
6. Test events in PostHog

**Remember:**
- ✅ Never commit real API keys
- ✅ Use separate PostHog project for development
- ✅ Test both enabled and disabled states
- ✅ Revert local changes before committing

---

Need help? Check:
- PostHog docs: https://posthog.com/docs
- TimeTracker telemetry docs: `docs/all_tracked_events.md`

