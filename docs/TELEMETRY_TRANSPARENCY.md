# Telemetry Transparency Notice

TimeTracker uses a two-layer model:

- **Anonymous base telemetry (default behavior):** installation registration + heartbeat
- **Detailed analytics (opt-in):** richer usage/error/performance context

## What is always sent

Base telemetry includes installation-level, non-PII metadata:
- install UUID
- app version
- platform/OS/architecture
- locale/timezone
- first_seen + heartbeat timestamps

## What is only sent when opted in

Detailed telemetry events such as feature usage and error context, with direct PII fields filtered out.

## What is never sent

- emails
- usernames
- project/client names and content
- time entry notes/content
- raw password/token fields

## Sink

Telemetry is sent to Grafana Cloud OTLP when configured:
- `GRAFANA_OTLP_ENDPOINT`
- `GRAFANA_OTLP_TOKEN`

## Control

Admins can enable/disable detailed analytics in the app at any time.  
Disabling detailed analytics does **not** stop base anonymous telemetry.

