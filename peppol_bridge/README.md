# Peppol Bridge (TimeTracker)

`peppol-bridge` is a small, self-hostable HTTP service that implements TimeTracker’s **Generic Peppol Access Point adapter contract**.

TimeTracker generates **Peppol BIS Billing 3.0 UBL 2.1 XML** and sends it to this bridge (`PEPPOL_ACCESS_POINT_URL`). The bridge then forwards it to a selected provider API (preset) or a custom forward URL.

## Endpoints

- `GET /health` — basic health check
- `POST /test` — verify provider credentials/config
- `POST /send` — receive TimeTracker contract and forward the UBL

## Auth (bridge endpoint)

If `PEPPOL_BRIDGE_AUTH_TOKEN` is set, the bridge requires:

- `Authorization: Bearer <token>`

TimeTracker can send this token using `PEPPOL_ACCESS_POINT_TOKEN`.

## Provider presets

### e-invoice.be

Environment:

- `PEPPOL_BRIDGE_PROVIDER=einvoice`
- `EINVOICE_API_KEY=...`
- `EINVOICE_BASE_URL=https://api.e-invoice.be` (optional)

### Peppyrus

Environment:

- `PEPPOL_BRIDGE_PROVIDER=peppyrus`
- `PEPPYRUS_API_KEY=...`
- `PEPPYRUS_BASE_URL=https://api.peppyrus.be/v1` (optional; test: `https://api.test.peppyrus.be/v1`)

Peppyrus authenticates API requests with the `X-Api-Key` header (not `Authorization: Bearer`).

### generic_custom (passthrough)

Environment:

- `PEPPOL_BRIDGE_PROVIDER=generic_custom`
- `GENERIC_FORWARD_URL=https://...`
- `GENERIC_FORWARD_TOKEN=...` (optional bearer token)

## Running with Docker

Build:

```bash
docker build -f peppol_bridge/Dockerfile -t timetracker-peppol-bridge:latest .
```

Run:

```bash
docker run --rm -p 8088:8088 \
  -e PEPPOL_BRIDGE_PROVIDER=einvoice \
  -e EINVOICE_API_KEY=YOUR_KEY \
  -e PEPPOL_BRIDGE_AUTH_TOKEN=CHANGE_ME \
  timetracker-peppol-bridge:latest
```

