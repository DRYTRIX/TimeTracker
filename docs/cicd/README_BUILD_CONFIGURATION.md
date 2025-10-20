# Build Configuration Guide

This document explains how TimeTracker handles analytics configuration for official builds vs self-hosted deployments.

## Quick Start

### For Self-Hosted Users (No Setup Required)

```bash
# Clone and run - analytics disabled by default
git clone https://github.com/YOUR_USERNAME/timetracker.git
cd timetracker
docker-compose up -d
```

No analytics keys needed! Telemetry is opt-in and disabled by default.

### For Official Build Users

```bash
# Pull and run official build
docker pull ghcr.io/YOUR_USERNAME/timetracker:latest
docker-compose up -d
```

On first access, choose whether to enable telemetry for community support.

## How It Works

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Configuration Priority (Highest to Lowest)                  │
├─────────────────────────────────────────────────────────────┤
│ 1. Environment Variables (User Override)                    │
│    └─> POSTHOG_API_KEY=...                                  │
│                                                              │
│ 2. Built-in Defaults (Official Builds Only)                 │
│    └─> From app/config/analytics_defaults.py                │
│        (Injected by GitHub Actions)                          │
│                                                              │
│ 3. Empty/Disabled (Self-Hosted)                            │
│    └─> Placeholders not replaced = No analytics             │
└─────────────────────────────────────────────────────────────┘
```

### File Structure

```
app/config/
└── analytics_defaults.py
    ├── POSTHOG_API_KEY_DEFAULT = "%%POSTHOG_API_KEY_PLACEHOLDER%%"
    ├── SENTRY_DSN_DEFAULT = "%%SENTRY_DSN_PLACEHOLDER%%"
    ├── APP_VERSION_DEFAULT = "%%APP_VERSION_PLACEHOLDER%%"
    └── get_analytics_config() → Returns merged config
```

## GitHub Actions Workflow

### Official Release Build

`.github/workflows/build-and-publish.yml`:

```yaml
- name: Inject analytics configuration
  env:
    POSTHOG_API_KEY: ${{ secrets.POSTHOG_API_KEY }}
    SENTRY_DSN: ${{ secrets.SENTRY_DSN }}
  run: |
    sed -i "s|%%POSTHOG_API_KEY_PLACEHOLDER%%|${POSTHOG_API_KEY}|g" \
      app/config/analytics_defaults.py
    sed -i "s|%%SENTRY_DSN_PLACEHOLDER%%|${SENTRY_DSN}|g" \
      app/config/analytics_defaults.py
```

### Development Build

`.github/workflows/build-dev.yml`:

- Placeholders remain intact
- No analytics keys injected
- Users must provide their own keys

## Setup Instructions

### Setting Up GitHub Secrets (For Official Builds)

1. Go to your GitHub repository
2. Navigate to Settings → Secrets and variables → Actions
3. Add the following secrets:

   ```
   POSTHOG_API_KEY
   ├─ Name: POSTHOG_API_KEY
   └─ Value: phc_xxxxxxxxxxxxxxxxxxxxx
   
   SENTRY_DSN
   ├─ Name: SENTRY_DSN
   └─ Value: https://xxxxx@sentry.io/xxxxx
   ```

4. Trigger a release:
   ```bash
   git tag v3.0.0
   git push origin v3.0.0
   ```

### Verifying the Build

After the GitHub Action completes:

```bash
# Pull the image
docker pull ghcr.io/YOUR_USERNAME/timetracker:latest

# Check if it's an official build
docker run --rm ghcr.io/YOUR_USERNAME/timetracker:latest \
  python3 -c "from app.config.analytics_defaults import is_official_build; \
  print('Official build' if is_official_build() else 'Self-hosted')"
```

## User Override Examples

### Override Everything

```bash
# .env file
POSTHOG_API_KEY=my-custom-key
POSTHOG_HOST=https://my-posthog.com
SENTRY_DSN=https://my-sentry-dsn
APP_VERSION=3.0.0-custom
```

### Disable Analytics in Official Build

```bash
# Leave POSTHOG_API_KEY empty
export POSTHOG_API_KEY=""
export SENTRY_DSN=""

# Or just disable telemetry in the UI
# Admin → Telemetry → Disable
```

### Use Official Keys in Self-Hosted

```bash
# If you have access to official keys
export POSTHOG_API_KEY="official-key-here"
docker-compose up -d
```

## Development Workflow

### Local Development

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/timetracker.git
cd timetracker

# No keys needed for local dev
docker-compose up -d

# Access at http://localhost:5000
```

### Testing Analytics Locally

```bash
# Create your own PostHog/Sentry accounts
# Add keys to .env
echo "POSTHOG_API_KEY=your-dev-key" >> .env
echo "SENTRY_DSN=your-dev-dsn" >> .env

# Restart
docker-compose restart app

# Enable telemetry in admin dashboard
# Test events by using the app
```

## Security Considerations

### ✅ Safe Practices

- Analytics keys are injected at build time (not in source code)
- Keys are stored as GitHub Secrets (encrypted)
- Self-hosted users can use their own keys or none at all
- Telemetry is opt-in by default
- No PII is ever collected

### ⚠️ Important Notes

- **Never commit actual keys** to `analytics_defaults.py`
- **Keep GitHub Secrets secure** (limit access)
- **Audit workflows** before running them
- **Review tracked events** in `docs/all_tracked_events.md`

## Testing

### Test Official Build Process

```bash
# Create a test release
git tag v3.0.0-test
git push origin v3.0.0-test

# Monitor GitHub Actions
# Check the logs for:
# ✅ Analytics configuration injected
# ✅ All placeholders replaced successfully
# ✅ Docker image built and pushed
```

### Test Self-Hosted Build

```bash
# Build locally
docker build -t timetracker:test .

# Verify placeholders are intact
docker run --rm timetracker:test cat app/config/analytics_defaults.py | \
  grep "%%POSTHOG_API_KEY_PLACEHOLDER%%"

# Should show the placeholder (not replaced)
```

## Troubleshooting

### Placeholders Not Replaced

**Problem:** Official build still shows placeholders

**Solution:**
```bash
# Check GitHub Secrets are set
# Re-run the workflow
# Verify sed commands in workflow logs
```

### Analytics Not Working in Official Build

**Problem:** PostHog events not appearing

**Solution:**
```bash
# 1. Check telemetry is enabled in admin dashboard
# 2. Verify PostHog API key is valid
# 3. Check logs: docker-compose logs app | grep PostHog
# 4. Test connection: curl https://app.posthog.com/batch/
```

### Self-Hosted Build Has Embedded Keys

**Problem:** Self-hosted build accidentally has keys

**Solution:**
```bash
# Verify you're using the right workflow
# Dev/feature builds should use build-dev.yml
# Only release tags trigger build-and-publish.yml
```

## FAQ

**Q: Where are the analytics keys stored?**
A: In GitHub Secrets (encrypted) for official builds. Never in source code.

**Q: Can users extract the keys from official Docker images?**
A: Technically yes, but they're only useful with that specific PostHog/Sentry project. Self-hosted users should use their own keys.

**Q: What if I want to fork and build my own official releases?**
A: Set up your own PostHog/Sentry projects, add keys to your fork's GitHub Secrets, and run the workflow.

**Q: How do I rotate keys?**
A: Update GitHub Secrets and trigger a new release build.

**Q: Can I see what's sent to analytics?**
A: Yes! Check `logs/app.jsonl` for all events, and `docs/all_tracked_events.md` for the schema.

## Resources

- **Analytics Defaults:** `app/config/analytics_defaults.py`
- **Build Workflow:** `.github/workflows/build-and-publish.yml`
- **Dev Workflow:** `.github/workflows/build-dev.yml`
- **Telemetry Code:** `app/utils/telemetry.py`
- **All Events:** `docs/all_tracked_events.md`
- **Official vs Self-Hosted:** `docs/OFFICIAL_BUILDS.md`

---

**Need Help?** Open an issue on GitHub or check the documentation in `docs/`.

