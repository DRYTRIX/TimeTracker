# Analytics and Monitoring

TimeTracker provides privacy-aware analytics and monitoring with Grafana Cloud OTLP as the telemetry sink.

## Overview

1. **Structured JSON Logging** - Application event logs in `logs/app.jsonl`
2. **Sentry Integration** - Error monitoring and tracing (optional)
3. **Prometheus Metrics** - Runtime metrics at `/metrics`
4. **Grafana OTLP Telemetry** - Installation + product analytics telemetry

## Telemetry Model

### Base telemetry (anonymous, default behavior)
- Installation-level telemetry (`base_telemetry.first_seen`, `base_telemetry.heartbeat`)
- Includes install UUID, app version, platform, OS, architecture, locale, timezone
- No direct PII fields

### Detailed analytics (explicit opt-in only)
- Product events such as `timer.started`, `project.created`, `auth.login`
- Sent only when admins enable detailed analytics in the app
- PII-filtered before export

## Configuration

```bash
# Grafana OTLP sink
GRAFANA_OTLP_ENDPOINT=https://otlp-gateway-.../otlp/v1/logs
GRAFANA_OTLP_TOKEN=your-token

# Detailed analytics consent switch (app-controlled per installation)
ENABLE_TELEMETRY=true

# Optional error monitoring
SENTRY_DSN=
SENTRY_TRACES_RATE=0.1
```

## Troubleshooting

- If no telemetry arrives, verify `GRAFANA_OTLP_ENDPOINT` and `GRAFANA_OTLP_TOKEN`
- If detailed events are missing, confirm detailed analytics is enabled in admin settings
- If only base events appear, consent is likely disabled (expected behavior)

