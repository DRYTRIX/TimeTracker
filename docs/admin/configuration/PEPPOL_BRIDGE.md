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

Peppyrus authenticates API requests with the `X-Api-Key` header (not `Authorization: Bearer`).

### getpeppr

Environment variables:

- `PEPPOL_BRIDGE_PROVIDER=getpeppr`
- `GETPEPPR_API_KEY=...` (`sk_sandbox_…` sends on the Peppol test network, `sk_live_…` in production; the key decides the environment)
- `GETPEPPR_BASE_URL=https://api.getpeppr.dev/v1` (optional)

getpeppr authenticates with `Authorization: Bearer <key>`. Create an account and a sandbox key at [console.getpeppr.dev](https://console.getpeppr.dev).

How the bridge uses it:

- `POST /test` calls `GET /v1/identity` (read-only) and returns the key's environment and its Peppol identity, so you can check which company and network you are about to send from.
- `POST /send` calls `POST /v1/invoices/import` with the UBL exactly as TimeTracker generated it and the recipient's `scheme:id` as routing. getpeppr takes the sender from the API key's company and refuses a UBL whose supplier is another company; the document type comes from the UBL. The sender and document/process identifiers in TimeTracker's contract are therefore not forwarded.
- Every send carries an `Idempotency-Key` built from the invoice's UBL, its recipient and the UTC date. Embedded attachments (the invoice PDF) are left out of the key, because TimeTracker regenerates the PDF on every attempt and sends without it when generation fails or embedding is turned off. Sending the same invoice again the same day never delivers a second copy: getpeppr returns the original document when the request is byte-identical, and otherwise refuses it (`422 idempotency_key_reuse`), which TimeTracker shows as a failed send even though the first attempt went out. Check the document in the getpeppr console before sending it again. A corrected invoice is a new key. getpeppr also refuses the same invoice number to the same recipient within 15 minutes (`409 duplicate_document`). A resend on a later UTC day goes out, and getpeppr flags it with `duplicateOf`.
- `GET /message/<id>/status` reads `GET /v1/invoices/<id>` and maps getpeppr's status to the bridge folder: `submitted` → `outbox`; `delivered` and the buyer's responses (`acknowledged`, `in_process`, `under_query`, `conditionally_accepted`, `accepted`, `rejected`, `paid`, `partially_paid`) → `sent`; `failed` → `failed`; `no_action` (recipient not found on the network) → `failed`; `cleared` and any other status → no folder (still pending). A failed folder carries a `fatal_rules` entry (`getpeppr:failed` or `getpeppr:no_recipient`). getpeppr's own status is returned beside it in `status`. A buyer's `rejected` is a business answer after delivery, not a failed transmission, so it reads `sent` with `status: "rejected"`.

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
