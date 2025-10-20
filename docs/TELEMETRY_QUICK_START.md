# Telemetry & Analytics Quick Start Guide

## For End Users

### First-Time Setup

When you first access TimeTracker, you'll see a welcome screen asking about telemetry:

1. **Read the Privacy Information** - Review what data is collected (and what isn't)
2. **Choose Your Preference:**
   - ✅ **Enable Telemetry** - Help improve TimeTracker by sharing anonymous usage data
   - ⬜ **Disable Telemetry** - No data will be sent (default)
3. **Click "Complete Setup & Continue"**

You can change this decision anytime in the admin settings.

### Viewing Telemetry Status (Admin Only)

1. Login as an administrator
2. Go to **Admin** → **Telemetry Dashboard** (or visit `/admin/telemetry`)
3. View:
   - Current telemetry status (enabled/disabled)
   - Installation ID and fingerprint
   - PostHog configuration status
   - Sentry configuration status
   - What data is being collected

### Changing Telemetry Preference (Admin Only)

1. Go to `/admin/telemetry`
2. Click **"Enable Telemetry"** or **"Disable Telemetry"** button
3. Your preference is saved immediately

## For Administrators

### Setting Up Analytics Services

#### PostHog (Product Analytics)

To enable PostHog tracking:

1. Sign up for PostHog at https://posthog.com (or self-host)
2. Get your API key from PostHog dashboard
3. Set environment variable:
   ```bash
   export POSTHOG_API_KEY="your-api-key-here"
   export POSTHOG_HOST="https://app.posthog.com"  # Default, change if self-hosting
   ```
4. Restart the application
5. Enable telemetry in admin dashboard (if not already enabled)

#### Sentry (Error Monitoring)

To enable Sentry error tracking:

1. Sign up for Sentry at https://sentry.io (or self-host)
2. Create a project and get your DSN
3. Set environment variable:
   ```bash
   export SENTRY_DSN="your-sentry-dsn-here"
   export SENTRY_TRACES_RATE="0.1"  # Sample 10% of requests
   ```
4. Restart the application

### Installation-Specific Configuration

TimeTracker automatically generates a unique salt and installation ID on first startup. These are stored in `data/installation.json` and persist across restarts.

**File location:** `data/installation.json`

**Example content:**
```json
{
  "telemetry_salt": "8f4a7b2e9c1d6f3a5e8b4c7d2a9f6e3b1c8d5a7f2e9b4c6d3a8f5e1b7c4d9a2f",
  "installation_id": "a3f5c8e2b9d4a1f7",
  "setup_complete": true,
  "telemetry_enabled": false,
  "setup_completed_at": "2025-10-20T12:34:56.789"
}
```

**Important:**
- ⚠️ Do not delete this file unless you want to reset the setup
- ⚠️ Back up this file with your database backups
- ⚠️ Keep the salt secure (though it doesn't contain PII)

### Viewing Tracked Events

If telemetry is enabled, all events are logged to `logs/app.jsonl`:

```bash
tail -f logs/app.jsonl | grep "event_type"
```

Example event:
```json
{
  "timestamp": "2025-10-20T12:34:56.789Z",
  "level": "info",
  "event_type": "timer.started",
  "user_id": 1,
  "entry_id": 42,
  "project_id": 7
}
```

### Docker Deployment

The Docker Compose configuration includes all analytics services:

```bash
# Start all services (including analytics)
docker-compose up -d

# View logs for analytics services
docker-compose logs -f prometheus grafana loki
```

**Services included:**
- **Prometheus** - Metrics collection (http://localhost:9090)
- **Grafana** - Visualization (http://localhost:3000)
- **Loki** - Log aggregation
- **Promtail** - Log shipping

## Privacy & Compliance

### GDPR Compliance

TimeTracker's telemetry system is designed with GDPR principles in mind:

- ✅ **Consent-Based:** Opt-in by default
- ✅ **Transparent:** Clear documentation of collected data
- ✅ **Right to Withdraw:** Can disable anytime
- ✅ **Data Minimization:** Only collects necessary event data
- ✅ **No PII:** Never collects personally identifiable information

### Data Retention

- **JSON Logs:** Rotate daily, keep 30 days (configurable)
- **PostHog:** Follow PostHog's retention policy
- **Sentry:** Follow Sentry's retention policy
- **Prometheus:** 15 days default (configurable in `prometheus/prometheus.yml`)

### Disabling All Telemetry

To completely disable all telemetry and analytics:

1. **In Application:** Disable in `/admin/telemetry`
2. **Remove API Keys:**
   ```bash
   unset POSTHOG_API_KEY
   unset SENTRY_DSN
   unset ENABLE_TELEMETRY
   ```
3. **Restart Application**

## Troubleshooting

### Setup Page Keeps Appearing

If the setup page keeps appearing after completion:

1. Check `data/installation.json` exists and has `"setup_complete": true`
2. Check file permissions (application must be able to write to `data/` directory)
3. Check logs for errors: `tail -f logs/app.jsonl`

### Events Not Appearing in PostHog

1. **Check API Key:** Verify `POSTHOG_API_KEY` is set
2. **Check Telemetry Status:** Go to `/admin/telemetry` and verify it's enabled
3. **Check Logs:** `tail -f logs/app.jsonl | grep PostHog`
4. **Check Network:** Ensure server can reach PostHog host

### Admin Dashboard Not Accessible

1. **Login as Admin:** Only administrators can access `/admin/telemetry`
2. **Check User Role:** Verify user has `is_admin=True` in database
3. **Check Logs:** Look for permission errors in logs

## Support & Documentation

- **Full Documentation:** See `docs/analytics.md`
- **All Tracked Events:** See `docs/all_tracked_events.md`
- **Privacy Policy:** See `docs/privacy.md`
- **GitHub Issues:** Report bugs or request features

## FAQ

**Q: Is telemetry required to use TimeTracker?**
A: No! Telemetry is completely optional and disabled by default.

**Q: Can you identify me from the telemetry data?**
A: No. We only collect anonymous event types and numeric IDs. No usernames, emails, or project names are ever collected.

**Q: How do I know what's being sent?**
A: Check the `/admin/telemetry` dashboard and review `docs/all_tracked_events.md` for a complete list.

**Q: Can I use my own PostHog/Sentry instance?**
A: Yes! Set `POSTHOG_HOST` and `SENTRY_DSN` to your self-hosted instances.

**Q: What happens to my data if I disable telemetry?**
A: Nothing is sent to external services. Events are still logged locally in `logs/app.jsonl` for debugging.

**Q: Can I re-run the setup?**
A: Yes, delete `data/installation.json` and restart the application.

