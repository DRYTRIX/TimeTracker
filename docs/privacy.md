# Privacy Policy - Analytics & Telemetry

This document describes how TimeTracker collects, uses, and protects data through its analytics and telemetry features.

## Overview

TimeTracker is designed with privacy as a core principle. All analytics features are either:
1. **Local-only** (structured logging)
2. **Self-hosted** (Prometheus metrics)
3. **Optional and opt-in** (Grafana OTLP detailed analytics, Sentry)

## Data Collection

### What We Collect

#### 1. Structured Logs (Always Enabled)
Logs are stored **locally on your server only** in `logs/app.jsonl`.

**Data collected:**
- Request timestamps and durations
- HTTP methods and response codes
- Endpoint paths
- User IDs (internal database references)
- Error messages and stack traces
- Request IDs for tracing

**Not collected:**
- Passwords or authentication tokens
- Email addresses
- Personal notes or time entry descriptions
- IP addresses (unless explicitly configured in your logging setup)

**Storage:** Local filesystem only  
**Retention:** Based on your logrotate configuration  
**Access:** Only system administrators with access to the server

#### 2. Prometheus Metrics (Always Enabled, Self-Hosted)
Metrics are exposed at `/metrics` endpoint for scraping by your Prometheus server.

**Data collected:**
- Request counts by endpoint and status code
- Request latency histograms
- Active timer counts
- Database connection pool metrics

**Not collected:**
- User-identifying information
- Personal data
- Business data

**Storage:** Your Prometheus server  
**Retention:** Based on your Prometheus configuration  
**Access:** Only users with access to your Prometheus/Grafana instance

#### 3. Error Monitoring (Sentry) - Optional
**Default:** Disabled  
**Enable by setting:** `SENTRY_DSN`

When enabled, sends error reports to Sentry.

**Data collected:**
- Error messages and stack traces
- Request context (URL, method, headers)
- User ID (internal reference)
- Application version
- Server environment information

**Not collected:**
- Passwords or tokens
- Request/response bodies (by default)
- Email addresses (unless in error message)

**Storage:** Sentry servers (or your self-hosted Sentry instance)  
**Retention:** Based on your Sentry plan (typically 90 days)  
**Access:** Team members with Sentry access

#### 4. Base Telemetry (Minimal) - Anonymous Installation Telemetry
**Purpose:** Install footprint and distribution (version, platform, active installs).

**Data collected (no PII):**
- Install ID (random UUID), app version, platform, OS version, architecture
- Locale, timezone, deployment type, first/last seen, heartbeat timestamp

**Not collected:** Raw IP (stored), email, usernames, feature usage, paths, business data

**Storage:** Grafana OTLP sink (if configured)  
**Retention:** Recommend 12 months  
**Access:** Product/ops for install analytics

#### 5. Detailed Analytics (Grafana OTLP) - Optional & Opt-In
**Default:** Disabled (user must opt in via Admin → Privacy & Analytics)  
**Requires:** OTLP endpoint/token configured and user enabling "detailed analytics"

When opted in, tracks product usage and feature adoption.

**Data collected:**
- Event names (e.g. "timer.started", "project.created"), internal user ID, install_id
- Feature usage metadata, session context, page views (pathnames)

**Not collected:** Email, usernames, time entry content, client/project names, stored IP

**Storage:** Grafana Cloud OTLP backend (or self-hosted OTLP receiver)  
**Retention:** Per your Grafana retention policy  
**Access:** Team members with Grafana access

**Consent:** You can turn detailed analytics off anytime in Admin → Settings or Admin → Telemetry. Base telemetry (minimal) continues; no product events are sent when opted out.

## Anonymization & Hashing

### Installation Fingerprint

The telemetry fingerprint is generated as:
```
SHA256(server_hostname + TELE_SALT)
```

- Cannot be reversed to identify the server
- Unique per installation
- Changes if `TELE_SALT` changes
- No correlation to user data

### User IDs

All analytics use internal database IDs (integers), never:
- Email addresses
- Usernames
- Real names
- External identifiers

## Data Sharing

### Third-Party Services

When you enable optional services, data is sent to:

| Service | Data Sent | Purpose | Control |
|---------|-----------|---------|---------|
| Sentry | Errors, request context | Error monitoring | Set `SENTRY_DSN` |
| Grafana OTLP | Base telemetry + product events | Product analytics | Set `GRAFANA_OTLP_ENDPOINT` and `GRAFANA_OTLP_TOKEN` |

### Self-Hosting

You can self-host all optional services:
- **Sentry**: https://develop.sentry.dev/self-hosted/
- **Grafana/OTLP receiver**: Use Grafana Cloud or self-host an OTLP-compatible receiver
- **Prometheus**: Already self-hosted by default

## Your Rights (GDPR Compliance)

TimeTracker is designed to be GDPR-compliant. You have the right to:

### 1. Access Your Data
- **Logs**: Access files in `logs/` directory
- **Metrics**: Query your Prometheus instance
- **Sentry**: Export data from Sentry UI
- **Grafana telemetry**: Export/query from Grafana stack

### 2. Rectify Your Data
Contact your TimeTracker administrator to correct inaccurate data.

### 3. Erase Your Data
To delete your data:

#### Local Logs
```bash
# Delete logs
rm -f logs/app.jsonl*
```

#### Prometheus
Data automatically expires based on retention settings.

#### Sentry
Use Sentry's data deletion features or contact support.

#### Grafana telemetry
Use your Grafana data retention/deletion policy and tooling.

#### Telemetry
Set `ENABLE_TELEMETRY=false` to stop sending data. To delete existing telemetry data, contact the telemetry service operator with your fingerprint hash.

### 4. Export Your Data
All data can be exported:
- **Logs**: Copy files from `logs/` directory
- **Metrics**: Query and export from Prometheus
- **Sentry**: Use Sentry export features
- **Grafana telemetry**: Use Grafana export/query features

### 5. Opt-Out
To opt out of all optional analytics:

```bash
# .env file
SENTRY_DSN=
GRAFANA_OTLP_ENDPOINT=
GRAFANA_OTLP_TOKEN=
ENABLE_TELEMETRY=false
```

## Data Security

### In Transit
- Logs: Local filesystem only (no transit)
- Metrics: Scraped via HTTP/HTTPS (configure TLS in Prometheus)
- Sentry: HTTPS only
- Grafana OTLP: HTTPS only
- Telemetry: HTTPS only

### At Rest
- **Logs**: Protected by filesystem permissions (use encryption at rest if required)
- **Metrics**: Protected by Prometheus access controls
- **Sentry**: Protected by Sentry (encrypted at rest)
- **Grafana telemetry**: Protected by your Grafana backend

### Access Controls
- Logs: Require server filesystem access
- Metrics: Require Prometheus/Grafana access
- Sentry: Require Sentry account with appropriate permissions
- Grafana telemetry: Require Grafana account with appropriate permissions

## Data Minimization

TimeTracker follows data minimization principles:

1. **Only collect what's necessary** for functionality or debugging
2. **No PII in events** unless absolutely required
3. **Aggregate when possible** instead of individual records
4. **Short retention** periods for detailed logs
5. **Local-first** storage when possible

## Consent & Transparency

### Explicit Consent Required
- Installation telemetry (`ENABLE_TELEMETRY`)
- Product analytics sink (`GRAFANA_OTLP_ENDPOINT` + `GRAFANA_OTLP_TOKEN`)
- Error monitoring (`SENTRY_DSN`)

### Implicit Consent
- Local logs (essential for operation)
- Prometheus metrics (essential for monitoring)

### Transparency
- This documentation is always available
- Configuration is explicit in environment variables
- No hidden data collection

## Children's Privacy

TimeTracker is not intended for use by children under 16. We do not knowingly collect data from children.

## International Data Transfers

If you enable optional services hosted outside your region:
- **Sentry**: Data may be transferred to US/EU Sentry servers
- **Grafana telemetry**: Data location depends on your Grafana region/stack

Use self-hosted instances to keep data in your region.

## Changes to This Policy

This privacy policy may be updated. Changes will be:
1. Documented in git commit history
2. Announced in release notes
3. Reflected in this document

Last updated: 2025-10-20

## Contact

For privacy-related questions:
1. Check this documentation
2. Contact your TimeTracker administrator
3. For SaaS deployments, contact the service provider

## Compliance Summary

| Regulation | Status | Notes |
|------------|--------|-------|
| GDPR | Compliant | Supports all data subject rights |
| CCPA | Compliant | Opt-out available for all optional features |
| HIPAA | Not applicable | TimeTracker is not a healthcare application |
| SOC 2 | Depends on deployment | Use encrypted logs, secure credentials |

## Frequently Asked Questions

### Can I disable all analytics?
You can disable optional analytics (Sentry and detailed telemetry). Local logs and Prometheus metrics are essential for operation but stay on your infrastructure.

### Where is my data stored?
- **Logs**: Your server's filesystem
- **Metrics**: Your Prometheus server
- **Optional services**: Depends on your configuration (self-hosted or cloud)

### Can someone else see my data?
Only if you:
1. Enable optional cloud services (Sentry, Grafana OTLP)
2. Grant them access to your infrastructure

Self-hosted deployments are completely private.

### How do I delete all analytics data?
```bash
# Stop application
docker-compose down

# Delete logs
rm -rf logs/*.jsonl*

# Remove optional service configurations
# Edit .env and remove:
# - SENTRY_DSN
# - GRAFANA_OTLP_ENDPOINT
# - GRAFANA_OTLP_TOKEN
# - ENABLE_TELEMETRY

# Restart application
docker-compose up -d
```

### Is my business data collected?
No. Analytics collect:
- Usage patterns (which features are used)
- Technical metrics (performance, errors)
- User IDs (internal references only)

Not collected:
- Project names or descriptions
- Time entry descriptions
- Client information
- Invoice details
- Task descriptions

---

**Version**: 1.0  
**Effective Date**: 2025-10-20  
**Document Owner**: Privacy & Security Team

