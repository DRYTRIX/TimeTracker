# Telemetry & Analytics Cheat Sheet

## Quick Commands

### View Telemetry Status
```bash
# Check installation config
cat data/installation.json

# View recent events
tail -f logs/app.jsonl | grep event_type

# Check if telemetry is enabled
grep -o '"telemetry_enabled":[^,]*' data/installation.json
```

### Reset Setup
```bash
# Delete installation config (will show setup page again)
rm data/installation.json

# Restart application
docker-compose restart app
```

### Configure Services
```bash
# PostHog
export POSTHOG_API_KEY="your-api-key"
export POSTHOG_HOST="https://app.posthog.com"

# Sentry
export SENTRY_DSN="your-sentry-dsn"
export SENTRY_TRACES_RATE="0.1"
```

## Key URLs

| URL | Description | Access |
|-----|-------------|--------|
| `/setup` | Initial setup page | Public |
| `/admin/telemetry` | Telemetry dashboard | Admin only |
| `/admin/telemetry/toggle` | Toggle telemetry | Admin only (POST) |
| `/metrics` | Prometheus metrics | Public |

## Key Files

| File | Purpose |
|------|---------|
| `data/installation.json` | Installation config (salt, ID, preferences) |
| `logs/app.jsonl` | JSON-formatted application logs |
| `app/utils/installation.py` | Installation config management |
| `app/routes/setup.py` | Setup route handler |
| `docs/all_tracked_events.md` | Complete list of events |

## Event Tracking Functions

```python
# Log event (JSON logging)
log_event("event.name", user_id=1, key="value")

# Track event (PostHog)
track_event(user_id, "event.name", {"key": "value"})
```

## Event Categories

| Category | Events | Example |
|----------|--------|---------|
| Auth | 3 | `auth.login`, `auth.logout` |
| Timer | 2 | `timer.started`, `timer.stopped` |
| Projects | 4 | `project.created`, `project.updated` |
| Tasks | 4 | `task.created`, `task.status_changed` |
| Clients | 4 | `client.created`, `client.archived` |
| Invoices | 5 | `invoice.created`, `invoice.sent` |
| Reports | 3 | `report.viewed`, `export.csv` |
| Comments | 3 | `comment.created`, `comment.updated` |
| Admin | 6 | `admin.user_created`, `admin.telemetry_toggled` |
| Setup | 1 | `setup.completed` |

**Total: 30+ events**

## Installation Config Structure

```json
{
  "telemetry_salt": "64-char-hex-string",
  "installation_id": "16-char-id",
  "setup_complete": true,
  "telemetry_enabled": false,
  "setup_completed_at": "2025-10-20T..."
}
```

## Privacy Checklist

### ✅ What We Track
- Event types (`timer.started`)
- Numeric IDs (1, 2, 3...)
- Timestamps
- Anonymous fingerprints

### ❌ What We DON'T Track
- Email addresses
- Usernames
- Project names
- Client data
- Time entry notes
- IP addresses
- Any PII

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Setup keeps appearing | Check `data/installation.json` exists and is writable |
| Events not in PostHog | Verify `POSTHOG_API_KEY` is set and telemetry is enabled |
| Cannot access dashboard | Ensure logged in as admin user |
| Salt keeps changing | Don't delete `data/installation.json` |

## Docker Services

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f app

# Restart app
docker-compose restart app

# Access analytics services
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000
```

## Testing Commands

```bash
# Run all tests
pytest

# Run telemetry tests
pytest tests/test_telemetry.py tests/test_installation_config.py

# Run with coverage
pytest --cov=app --cov-report=html

# Check linting
flake8 app/utils/installation.py app/routes/setup.py
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTHOG_API_KEY` | (empty) | PostHog API key for product analytics |
| `POSTHOG_HOST` | `https://app.posthog.com` | PostHog host URL |
| `SENTRY_DSN` | (empty) | Sentry DSN for error monitoring |
| `SENTRY_TRACES_RATE` | `0.0` | Sentry traces sample rate (0.0-1.0) |
| `ENABLE_TELEMETRY` | `false` | Override telemetry (user pref takes precedence) |
| `TELE_URL` | (empty) | Custom telemetry endpoint |

## Common Tasks

### Enable Telemetry
1. Login as admin
2. Go to `/admin/telemetry`
3. Click "Enable Telemetry"

### Disable Telemetry
1. Login as admin
2. Go to `/admin/telemetry`
3. Click "Disable Telemetry"

### View What's Being Tracked
```bash
# Live stream of events
tail -f logs/app.jsonl | jq 'select(.event_type != null)'

# Count events by type
cat logs/app.jsonl | jq -r '.event_type' | sort | uniq -c | sort -rn
```

### Export Events
```bash
# All events from today
cat logs/app.jsonl | jq 'select(.event_type != null)' > events_today.json

# Specific event type
cat logs/app.jsonl | jq 'select(.event_type == "timer.started")' > timer_events.json
```

## Security Notes

⚠️ **Important:**
- Telemetry salt is unique per installation
- Installation ID cannot reverse-engineer to identify server
- No PII is ever collected or transmitted
- All tracking is opt-in by default
- Users can disable at any time

## Quick Reference

**Check telemetry status:**
```bash
curl http://localhost:5000/admin/telemetry
```

**Toggle telemetry (requires admin login):**
```bash
curl -X POST http://localhost:5000/admin/telemetry/toggle \
  -H "Cookie: session=YOUR_SESSION_COOKIE"
```

**View Prometheus metrics:**
```bash
curl http://localhost:5000/metrics
```

---

**For more details, see:**
- `IMPLEMENTATION_COMPLETE.md` - Full implementation details
- `docs/all_tracked_events.md` - Complete event list
- `docs/TELEMETRY_QUICK_START.md` - User guide

