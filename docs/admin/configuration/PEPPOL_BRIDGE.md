# Peppol Bridge (Self-hosted adapter)

TimeTracker can send invoices via Peppol using the **Generic transport**. Generic transport requires an HTTP adapter endpoint (`PEPPOL_ACCESS_POINT_URL`) that accepts TimeTracker’s JSON contract and forwards the UBL XML to a Peppol Access Point provider.

This repository includes a ready-to-run adapter: **`peppol-bridge`**.

## Quick start (Docker Compose)

1) Add the bridge service to your compose file:

```yaml
  peppol-bridge:
    build:
      context: .
      dockerfile: peppol_bridge/Dockerfile
    container_name: timetracker-peppol-bridge
    environment:
      - PEPPOL_BRIDGE_AUTH_TOKEN=${PEPPOL_BRIDGE_AUTH_TOKEN:?Set PEPPOL_BRIDGE_AUTH_TOKEN}
      - PEPPOL_BRIDGE_TIMEOUT_S=30
      - PEPPOL_BRIDGE_PROVIDER=einvoice
      - EINVOICE_BASE_URL=${EINVOICE_BASE_URL:-https://api.e-invoice.be}
      - EINVOICE_API_KEY=${EINVOICE_API_KEY:?Set EINVOICE_API_KEY}
    ports: []
    restart: unless-stopped
```

2) In TimeTracker, open the wizard:

- **Admin → System Settings → Peppol → Setup wizard**

Use:

- Bridge base URL (from container): `http://peppol-bridge:8088`
- Bridge auth token: the same `PEPPOL_BRIDGE_AUTH_TOKEN` you set in compose

The wizard stores:

- `PEPPOL_ENABLED` override in DB (enabled)
- `PEPPOL_TRANSPORT_MODE=generic`
- `PEPPOL_ACCESS_POINT_URL=http://peppol-bridge:8088/send`
- `PEPPOL_ACCESS_POINT_TOKEN=<bridge auth token>`

## Provider presets

### e-invoice.be

Environment variables:

- `PEPPOL_BRIDGE_PROVIDER=einvoice`
- `EINVOICE_API_KEY=...`
- `EINVOICE_BASE_URL=https://api.e-invoice.be` (optional; staging: `https://api-dev.e-invoice.be`)

### Peppyrus

Environment variables:

- `PEPPOL_BRIDGE_PROVIDER=peppyrus`
- `PEPPYRUS_API_KEY=...`
- `PEPPYRUS_BASE_URL=https://api.peppyrus.be/v1` (optional; test: `https://api.test.peppyrus.be/v1`)

### generic_custom (passthrough)

Environment variables:

- `PEPPOL_BRIDGE_PROVIDER=generic_custom`
- `GENERIC_FORWARD_URL=https://...` (URL that accepts TimeTracker’s adapter contract)
- `GENERIC_FORWARD_TOKEN=...` (optional bearer token for the forward URL)

## Health and testing

The bridge exposes:

- `GET /health`
- `POST /test` (validates provider credentials)
- `POST /send` (TimeTracker adapter contract)

If `PEPPOL_BRIDGE_AUTH_TOKEN` is set, `/test` and `/send` require:

- `Authorization: Bearer <token>`

