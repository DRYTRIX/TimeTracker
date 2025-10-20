# Analytics Quick Start Guide

This guide will help you quickly enable and configure analytics features in TimeTracker.

## 🎯 Choose Your Setup

### Option 1: No External Analytics (Default)
**What you get:**
- ✅ Local JSON logs (`logs/app.jsonl`)
- ✅ Prometheus metrics (`/metrics` endpoint)
- ✅ No data sent externally

**Setup:**
```bash
# No configuration needed - this is the default!
docker-compose up -d
```

---

### Option 2: Self-Hosted Monitoring
**What you get:**
- ✅ Local JSON logs
- ✅ Prometheus metrics collection
- ✅ Grafana dashboards
- ✅ Everything stays on your infrastructure

**Setup:**
```bash
# Deploy with monitoring profile
docker-compose --profile monitoring up -d

# Access dashboards
# Grafana: http://localhost:3000 (admin/admin)
# Prometheus: http://localhost:9090
```

---

### Option 3: Cloud Error Monitoring (Sentry)
**What you get:**
- ✅ Local JSON logs
- ✅ Prometheus metrics
- ✅ Automatic error reporting to Sentry
- ✅ Performance monitoring

**Setup:**
1. Create a free Sentry account: https://sentry.io
2. Create a new project and get your DSN
3. Add to `.env`:
```bash
SENTRY_DSN=https://your-key@sentry.io/your-project-id
SENTRY_TRACES_RATE=0.1  # 10% of requests for performance monitoring
```
4. Restart:
```bash
docker-compose restart
```

---

### Option 4: Product Analytics (PostHog)
**What you get:**
- ✅ Local JSON logs
- ✅ Prometheus metrics
- ✅ User behavior analytics
- ✅ Feature usage tracking
- ✅ Session recordings (optional)

**Setup:**
1. Create a free PostHog account: https://app.posthog.com
2. Create a project and get your API key
3. Add to `.env`:
```bash
POSTHOG_API_KEY=your-api-key
POSTHOG_HOST=https://app.posthog.com
```
4. Restart:
```bash
docker-compose restart
```

**Self-Hosted PostHog:**
You can also self-host PostHog: https://posthog.com/docs/self-host

---

### Option 5: Everything (Self-Hosted)
**What you get:**
- ✅ All monitoring and logging
- ✅ Everything on your infrastructure
- ✅ Full control over your data

**Setup:**
```bash
# Deploy with all profiles
docker-compose --profile monitoring --profile logging up -d

# Access services
# Application: https://localhost (via nginx)
# Grafana: http://localhost:3000
# Prometheus: http://localhost:9090
# Loki: http://localhost:3100
```

---

### Option 6: Full Cloud Stack
**What you get:**
- ✅ Cloud error monitoring (Sentry)
- ✅ Cloud product analytics (PostHog)
- ✅ Local logs and metrics

**Setup:**
Add to `.env`:
```bash
# Sentry
SENTRY_DSN=your-sentry-dsn
SENTRY_TRACES_RATE=0.1

# PostHog
POSTHOG_API_KEY=your-posthog-key
POSTHOG_HOST=https://app.posthog.com
```

Restart:
```bash
docker-compose restart
```

---

## 🔧 Advanced Configuration

### Enable Anonymous Telemetry
Help improve TimeTracker by sending anonymous usage statistics via PostHog:

```bash
# Add to .env
ENABLE_TELEMETRY=true
POSTHOG_API_KEY=your-posthog-api-key  # Required for telemetry
TELE_SALT=your-random-salt-string
APP_VERSION=1.0.0
```

**What's sent:**
- Anonymized installation fingerprint (SHA-256 hash)
- Application version
- Platform information (OS, Python version)

**What's NOT sent:**
- No usernames, emails, or any PII
- No project names or business data
- No IP addresses (not stored)

**Note:** Telemetry events are sent to PostHog using the same configuration as product analytics, keeping all your data in one place.

---

## 📊 Viewing Your Analytics

### Local Logs
```bash
# View JSON logs
tail -f logs/app.jsonl

# Pretty print JSON logs
tail -f logs/app.jsonl | jq .

# Search for specific events
grep "timer.started" logs/app.jsonl | jq .
```

### Prometheus Metrics
```bash
# View raw metrics
curl http://localhost:8000/metrics

# Query specific metric
curl 'http://localhost:9090/api/v1/query?query=tt_requests_total'
```

### Grafana Dashboards
1. Open http://localhost:3000
2. Login (admin/admin)
3. Create a new dashboard
4. Add panels with Prometheus queries

**Example Queries:**
```promql
# Request rate
rate(tt_requests_total[5m])

# P95 latency
histogram_quantile(0.95, rate(tt_request_latency_seconds_bucket[5m]))

# Error rate
rate(tt_requests_total{http_status=~"5.."}[5m])
```

---

## 🚨 Troubleshooting

### Logs not appearing?
```bash
# Check log directory permissions
ls -la logs/

# Check container logs
docker-compose logs timetracker

# Verify JSON logging is enabled
grep "JSON logging initialized" logs/timetracker.log
```

### Metrics endpoint not working?
```bash
# Test metrics endpoint
curl http://localhost:8000/metrics

# Should return Prometheus format text
# If 404, check app startup logs
docker-compose logs timetracker | grep metrics
```

### Sentry not receiving errors?
```bash
# Check SENTRY_DSN is set
docker-compose exec timetracker env | grep SENTRY

# Check Sentry initialization
docker-compose logs timetracker | grep -i sentry

# Trigger a test error in Python console
docker-compose exec timetracker python
>>> from app import create_app
>>> app = create_app()
>>> # Should see "Sentry error monitoring initialized"
```

### PostHog not tracking events?
```bash
# Check API key is set
docker-compose exec timetracker env | grep POSTHOG

# Check PostHog initialization
docker-compose logs timetracker | grep -i posthog

# Verify network connectivity
docker-compose exec timetracker curl -I https://app.posthog.com
```

---

## 🔒 Privacy & Compliance

### For GDPR Compliance
1. Enable only the analytics you need
2. Document your data collection in your privacy policy
3. Provide users with opt-out mechanisms
4. Regularly review and delete old data

### For Maximum Privacy
1. Use self-hosted analytics only (Option 2)
2. Disable telemetry (default)
3. Use short log retention periods
4. Encrypt logs at rest

### For Complete Control
1. Self-host everything (Prometheus, Grafana, Loki)
2. Don't enable Sentry or PostHog
3. Don't enable telemetry
4. All data stays on your infrastructure

---

## 📚 Further Reading

- **Complete Documentation:** [docs/analytics.md](docs/analytics.md)
- **Event Schema:** [docs/events.md](docs/events.md)
- **Privacy Policy:** [docs/privacy.md](docs/privacy.md)
- **Implementation Summary:** [ANALYTICS_IMPLEMENTATION_SUMMARY.md](ANALYTICS_IMPLEMENTATION_SUMMARY.md)

---

## ✅ Quick Validation

After setup, verify everything works:

```bash
# 1. Check metrics endpoint
curl http://localhost:8000/metrics

# 2. Check JSON logs are being written
ls -lh logs/app.jsonl

# 3. Trigger an event (login)
# Then check logs:
grep "auth.login" logs/app.jsonl | tail -1 | jq .

# 4. If using Grafana, check Prometheus datasource
# Open: http://localhost:3000/connections/datasources

# 5. View application logs
docker-compose logs -f timetracker
```

---

## 🎉 You're All Set!

Your analytics are now configured. TimeTracker will:
- 📝 Log all events in structured JSON format
- 📊 Expose metrics for Prometheus scraping
- 🔍 Send errors to Sentry (if enabled)
- 📈 Track product usage in PostHog (if enabled)
- 🔒 Respect user privacy at all times

**Need help?** Check the [documentation](docs/analytics.md) or [open an issue](https://github.com/drytrix/TimeTracker/issues).

---

**Last Updated:** 2025-10-20  
**Version:** 1.0

