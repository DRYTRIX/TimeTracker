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
- Support UI funnel events (`support.modal_opened`, `support.donation_clicked`, etc.) are emitted the same way when opt-in is enabled; see [all_tracked_events.md](all_tracked_events.md).

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

# Support / checkout links (optional; defaults in app/config.py)
SUPPORT_PURCHASE_URL=https://timetracker.drytrix.com/support.html
SUPPORT_PORTAL_BASE=https://timetracker.drytrix.com
# Optional one line shown in the support modal when set
SUPPORT_SOCIAL_PROOF_TEXT=
# Optional per-tier donate URLs (default to SUPPORT_PURCHASE_URL when unset)
SUPPORT_DONATE_EUR5_URL=
SUPPORT_DONATE_EUR10_URL=
SUPPORT_DONATE_EUR25_URL=
# Long-session soft prompt threshold in minutes (default 120)
SUPPORT_LONG_SESSION_MINUTES=120
```

Per-user **report generation counts** for the support modal are stored in `users.support_stats_reports_generated` (see migration `149_add_user_support_stats_reports_generated`).

## Troubleshooting

- If no telemetry arrives, verify `GRAFANA_OTLP_ENDPOINT` and `GRAFANA_OTLP_TOKEN`
- If detailed events are missing, confirm detailed analytics is enabled in admin settings
- If only base events appear, consent is likely disabled (expected behavior)
