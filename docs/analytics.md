# Analytics and Monitoring

TimeTracker includes comprehensive analytics and monitoring capabilities to help understand application usage, performance, and errors.

## Overview

The analytics system consists of several components:

1. **Structured JSON Logging** - Application-wide event logging in JSON format
2. **Sentry Integration** - Error monitoring and performance tracking
3. **Prometheus Metrics** - Performance metrics and monitoring
4. **PostHog Analytics** - Product analytics and user behavior tracking
5. **Telemetry** - Opt-in installation and version tracking

## Features

### Structured Logging

All application events are logged in structured JSON format to `logs/app.jsonl`. Each log entry includes:

- Timestamp
- Log level
- Event name
- Request ID (for tracing requests)
- Additional context (user ID, project ID, etc.)

Example log entry:
```json
{
  "asctime": "2025-10-20T10:30:45.123Z",
  "levelname": "INFO",
  "name": "timetracker",
  "message": "project.created",
  "request_id": "abc123-def456",
  "user_id": 42,
  "project_id": 15
}
```

### Error Monitoring (Sentry)

When enabled, Sentry captures:
- Uncaught exceptions
- Performance traces
- Request context
- User context

### Performance Metrics (Prometheus)

Exposed at `/metrics` endpoint:
- Total request count by method, endpoint, and status code
- Request latency histogram by endpoint
- Custom business metrics

### Product Analytics (PostHog)

Tracks user behavior and feature usage with advanced features:
- **Event Tracking**: Timer operations, project management, reports, exports
- **Person Properties**: User role, auth method, login history
- **Feature Flags**: Gradual rollouts, A/B testing, kill switches
- **Group Analytics**: Segment by platform, version, deployment method
- **Cohort Analysis**: Target specific user segments
- **Rich Context**: Browser, device, URL, environment on every event

See [POSTHOG_ADVANCED_FEATURES.md](../POSTHOG_ADVANCED_FEATURES.md) for complete guide.

### Telemetry

Optional, opt-in telemetry helps us understand:
- Number of active installations (anonymized)
- Version distribution
- Update patterns

**Privacy**: Telemetry is disabled by default and contains no personally identifiable information (PII).

**Implementation**: Telemetry data is sent via PostHog using anonymous fingerprints, keeping all installation data in one place.

## Configuration

All analytics features are controlled via environment variables. See `env.example` for configuration options.

### Enabling Analytics

```bash
# Enable Sentry
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
SENTRY_TRACES_RATE=0.1  # 10% sampling for performance traces

# Enable PostHog
POSTHOG_API_KEY=your-posthog-api-key
POSTHOG_HOST=https://app.posthog.com

# Enable Telemetry (opt-in, uses PostHog)
ENABLE_TELEMETRY=true
TELE_SALT=your-unique-salt
APP_VERSION=1.0.0
```

## Disabling Analytics

By default, most analytics features are disabled. To ensure they remain disabled:

```bash
# Disable all optional analytics
SENTRY_DSN=
POSTHOG_API_KEY=
ENABLE_TELEMETRY=false
```

Structured logging to files is always enabled as it's essential for troubleshooting.

## Log Management

Logs are written to `logs/app.jsonl` and should be rotated using:
- Docker volume mounts + host logrotate
- Grafana Loki + Promtail
- Elasticsearch + Filebeat
- Or similar log aggregation solutions

## Dashboards

Recommended dashboards:

### Sentry
- Error rate alerts
- New issue notifications
- Performance regression alerts

### Grafana + Prometheus
- Request rate and latency (P50, P95, P99)
- Error rates by endpoint
- Active timers gauge
- Database connection pool metrics

### PostHog
- User engagement funnels
- Feature adoption rates
- Session recordings (if enabled)

## Data Retention

- **Logs**: Retained locally based on your logrotate configuration
- **Sentry**: Based on your Sentry plan (typically 90 days)
- **Prometheus**: Based on your Prometheus configuration (typically 15-30 days)
- **PostHog**: Based on your PostHog plan
- **Telemetry**: 12 months

## Privacy & Compliance

See [privacy.md](privacy.md) for detailed information about data collection, retention, and GDPR compliance.

## Event Schema

See [events.md](events.md) for a complete list of tracked events and their properties.

## Maintenance

### Adding New Events

1. Define the event in `docs/events.md`
2. Instrument the code using `log_event()` or `track_event()`
3. Update this documentation
4. Test in development environment
5. Monitor in production dashboards

### Event Naming Convention

- Use dot notation: `resource.action`
- Examples: `project.created`, `timer.started`, `export.csv`
- Be consistent with existing event names

### Who Can Add Events

Changes to analytics require approval from:
- Product owner (for PostHog events)
- DevOps/SRE (for infrastructure metrics)
- Privacy officer (for any data collection changes)

## Troubleshooting

### Logs Not Appearing

1. Check `logs/` directory permissions
2. Verify LOG_LEVEL is set correctly
3. Check disk space

### Sentry Not Receiving Errors

1. Verify SENTRY_DSN is set correctly
2. Check network connectivity
3. Verify Sentry project is active
4. Check Sentry rate limits

### Prometheus Metrics Not Available

1. Verify `/metrics` endpoint is accessible
2. Check Prometheus scrape configuration
3. Verify network connectivity

### PostHog Events Not Appearing

1. Verify POSTHOG_API_KEY is set correctly
2. Check PostHog project settings
3. Verify network connectivity
4. Check PostHog rate limits

## Support

For analytics-related issues:
1. Check this documentation
2. Review logs in `logs/app.jsonl`
3. Check service-specific dashboards (Sentry, Grafana, PostHog)
4. Contact support with relevant log excerpts

